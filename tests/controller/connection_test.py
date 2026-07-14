from asyncio import StreamReader, StreamWriter, timeout
import asyncio
from socket import socketpair
from typing import Any, AsyncGenerator
from unittest import mock
import pytest
import pytest_asyncio
from tests.controller.conftest import TEST_TIMEOUT
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
import wiredwolf.controller.connections.connections as connections
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.messages import BaseMessage, ChatMessage, HeartbeatMessage, LobbyUpdatedMessage, NotAcknowledgeMessage
from wiredwolf.controller.server import GameServer, GameServerFactory
from wiredwolf.controller.server_plugins import ChatPlugin, GameLifecyclePlugin

TEST_BIND_ADDRESS = ("127.0.0.1", DEFAULT_SERVER_PORT)

async def check_is_instance(obj: Any, cls: type):
    assert isinstance(obj, cls)


@pytest_asyncio.fixture
async def server_conn_handler() -> AsyncGenerator[
    tuple[connections.AsyncTCPServerConnectionHandler, mock.Mock], None
]:

    mocked = mock.AsyncMock()
    serverConnHandler = connections.AsyncTCPServerConnectionHandler(
        bind_address=TEST_BIND_ADDRESS,
        on_new_peer=lambda peer: mocked.on_new_peer(peer),
        on_peer_disconnected=lambda peer: mocked.on_peer_disconnected(peer),
        on_new_message=lambda msg: mocked.on_new_message(msg),
    )
    yield serverConnHandler, mocked
    await serverConnHandler.close()


@pytest_asyncio.fixture
async def client_conn_handler():

    client_socket, server_socket = socketpair()
    client_reader, client_writer = await asyncio.open_connection(sock=client_socket)
    server_reader, server_writer = await asyncio.open_connection(sock=server_socket)
    peer = Peer("TestPeer")

    handler = connections.ConnectionHandlerFactory.get_client_connection_handler(
        my_self=peer,
        reader=client_reader,
        writer=client_writer,
    )

    yield handler
    try:
        await handler.close()
    except connections.ConnectionClosedError:
        pass

@pytest_asyncio.fixture
async def server():
    myself = Peer("Server")
    lobby = Lobby(myself, "TestLobby")
    server, _ = await GameServerFactory.get_game_server(lobby)
    yield server
    await server.close()


def test_peer_equality():
    peer1 = Peer("Alice")
    peer2 = Peer("Bob")
    assert peer1 != peer2, "Peers with different names should not be equal"
    peer3 = Peer("Alice")
    assert peer1 != peer3, (
        "Peers with the same name but different UUIDs should not be equal"
    )


def test_too_long_data_raises():
    handler = connections.AsyncTCPMessageHandler(connections.PickleSerializer())
    with pytest.raises(ValueError):
        handler.add_length_prefix(b"x" * (int("9" * handler.PREFIX_LEN) + 1))


def test_base_connection_handler():
    handler = connections.AsyncTCPMessageHandler(connections.PickleSerializer())
    assert handler.add_length_prefix(b"test") == b"0004test"

@pytest.mark.asyncio
async def test_send_and_receive():
    handler = connections.AsyncTCPMessageHandler(connections.PickleSerializer())

    async def client():
        creader, cwriter = await asyncio.open_connection("127.0.0.1", 8888)
        received = await handler.receive(creader)
        assert received == b"test"
        await handler.send(cwriter, b"test")
        cwriter.close()
        await cwriter.wait_closed()

    async def server():
        async def client_conn_cb(sreader: StreamReader, swriter: StreamWriter):
            await handler.send(swriter, b"test")
            received = await handler.receive(sreader)
            assert received == b"test"
            swriter.close()
            await swriter.wait_closed()

        await asyncio.start_server(lambda r, w: client_conn_cb(r, w), "127.0.0.1", 8888)

    try:
        async with timeout(TEST_TIMEOUT):
            await server()
            await client()
    except asyncio.TimeoutError:
        pytest.fail("Client and server did not complete communication within the timeout period")


@pytest.mark.asyncio
async def test_wrong_sender_discard_message(
    browser: TcpMdnsLobbyBrowser, server: GameServer
):
    exception_received_event = asyncio.Event()
    myself = Peer("Client1")
    lobby = Lobby(myself, "TestLobby")

    def on_client_receives_message(message: BaseMessage) -> None:
        if isinstance(message, LobbyUpdatedMessage):
            assert message.lobby == lobby
        elif isinstance(message, NotAcknowledgeMessage):
            exception_received_event.set()
        else:
            pytest.fail("Client should receive a NotAcknowledgeMessage")

    server.add_plugin(ChatPlugin())
    server.add_plugin(GameLifecyclePlugin())
    await server.start_listening()
    client_handler, lobby = await browser.connect_to_lobby_directly(
        myself, TEST_BIND_ADDRESS, None
    )
    client_handler.set_on_message(on_client_receives_message)
    await client_handler.start_receiving()
    fake_sender = Peer("FakeSender")
    msg = ChatMessage(sender=fake_sender, message="Hello", game_phase=None)
    await client_handler.send_obj(msg)
    try:
        async with timeout(TEST_TIMEOUT):
            await exception_received_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("Exception message not received in time")
    try:
        await client_handler.close()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_double_call_to_start_receiving(
    client_conn_handler: connections.AsyncTCPClientConnectionHandler,
):
    with pytest.raises(RuntimeError):
        await client_conn_handler.start_receiving()
        await client_conn_handler.start_receiving()

@pytest.mark.asyncio
async def test_server_connection_handler_callbacks(
    server_conn_handler: tuple[connections.AsyncTCPServerConnectionHandler, mock.Mock]
):
    handler, mocked = server_conn_handler
    myself = Peer("Client1")
    await handler.start_listening()
    reader, writer = await asyncio.open_connection(*TEST_BIND_ADDRESS)
    handler = connections.ConnectionHandlerFactory.get_client_connection_handler(
        my_self=myself,
        reader=reader,
        writer=writer,
    )
    handler.set_on_message(lambda msg: mocked.on_new_client_message(msg))
    await handler.start_receiving()
    await handler.send_obj(myself)
    try:
        async with timeout(5):
            while not mocked.on_new_peer.called:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("on_new_peer callback was not called in time")
    assert mocked.on_new_peer.call_count == 1, "on_new_peer should be called once"
    peer_arg = mocked.on_new_peer.call_args.args[0]
    assert peer_arg == myself, "on_new_peer should be called with the correct Peer instance"
    msg = ChatMessage(sender=myself, message="Hello", game_phase=None)
    await handler.send_obj(msg)
    try:
        async with timeout(5):
            while not mocked.on_new_message.called:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("on_new_message callback was not called in time")
    assert mocked.on_new_message.call_count == 1, "on_new_message should be called once"
    msg_arg = mocked.on_new_message.call_args.args[0]
    assert msg_arg == msg, "on_new_message should be called with the correct message"
    try:
        await handler.close()
    except connections.ConnectionClosedError:
        pass

@pytest.mark.asyncio
async def test_heartbeat():
    """Test that check that an heartbeat is recived by the client"""
    heartbeat_event = asyncio.Event()
    async def callback(p: Peer):
        assert isinstance(p, Peer)
    async def callback2(m: BaseMessage):
        #Server callback, don't care
        assert isinstance(m, BaseMessage)

    def callback_on_message(m: BaseMessage):
        #Client callback, check if we received a heartbeat message
        if isinstance(m, HeartbeatMessage):
            heartbeat_event.set()
    sockets = socketpair()
    server_reader, server_writer = await asyncio.open_connection(sock=sockets[0])
    client_reader, client_writer = await asyncio.open_connection(sock=sockets[1])
    server_peer = Peer("Server")
    client_peer = Peer("Client")
    server=connections.AsyncTCPServerConnectionHandler(("0.0.0.0", 0), callback , callback, callback2, callback, (server_peer, server_reader, server_writer))
    client=connections.AsyncTCPClientConnectionHandler(client_peer, client_reader, client_writer)
    client.set_on_message(callback_on_message) #What happens when you recive a message, is calling the function
    await server.start_listening()
    await client.start_receiving()
    try:
        async with timeout(connections.CONNECTION_TIMEOUT_HEARTBEAT):
            await heartbeat_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("Heartbeat message not received in time")

@pytest.mark.asyncio
async def test_heartbeat_client_gets_disconnection():
    """Test that check that the client can get when the heartbeat is disrupted"""
    heartbeat_event = asyncio.Event()
    closed_event = asyncio.Event()
    async def callback(p: Peer):
        assert isinstance(p, Peer)
    async def callback2(m: BaseMessage):
        #Server callback, don't care
        assert isinstance(m, BaseMessage)

    def callback_on_message(m: BaseMessage):
        #Client callback, check if we received a heartbeat message
        if isinstance(m, HeartbeatMessage):
            heartbeat_event.set()
        elif isinstance(m, connections.ConnectionClosedMessage):
            closed_event.set()
    sockets = socketpair()
    server_reader, server_writer = await asyncio.open_connection(sock=sockets[0])
    client_reader, client_writer = await asyncio.open_connection(sock=sockets[1])
    server_peer = Peer("Server")
    client_peer = Peer("Client")
    server=connections.AsyncTCPServerConnectionHandler(("0.0.0.0", 0), callback , callback, callback2, callback, (server_peer, server_reader, server_writer))
    client=connections.AsyncTCPClientConnectionHandler(client_peer, client_reader, client_writer)
    client.set_on_message(callback_on_message) #What happens when you recive a message, is calling the function
    await server.start_listening()
    await client.start_receiving()
    try:
        async with timeout(connections.CONNECTION_TIMEOUT_HEARTBEAT):
            await heartbeat_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("Heartbeat message not received in time")

    if server._heartbeat_task is not None:
        server._heartbeat_task.cancel() #Stop the heartbeat, to simulate a disconnection

    try:
        async with timeout(connections.CONNECTION_TIMEOUT_HEARTBEAT*2):
            await closed_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("ConnectionClosedMessage not received in time")


@pytest.mark.asyncio
async def test_heartbeat_server_reacts_to_disconnection():
    """Test that check that the server recives the client disconnection and calls the callback"""
    heartbeat_event = asyncio.Event()
    heartbeat_failed_event = asyncio.Event()
    async def callback(p: Peer):
        assert isinstance(p, Peer)
    async def callback2(m: BaseMessage):
        #Server callback, don't care
        assert isinstance(m, BaseMessage)

    def callback_on_message(m: BaseMessage):
        #Client callback, check if we received a heartbeat message
        if isinstance(m, HeartbeatMessage):
            heartbeat_event.set()

    async def callback_on_heartbeat_failed(p: Peer):
        heartbeat_failed_event.set()

    sockets = socketpair()
    server_reader, server_writer = await asyncio.open_connection(sock=sockets[0])
    client_reader, client_writer = await asyncio.open_connection(sock=sockets[1])
    server_peer = Peer("Server")
    client_peer = Peer("Client")
    server=connections.AsyncTCPServerConnectionHandler(("0.0.0.0", 0), callback , callback, callback2, callback_on_heartbeat_failed, (server_peer, server_reader, server_writer))
    client=connections.AsyncTCPClientConnectionHandler(client_peer, client_reader, client_writer)
    client.set_on_message(callback_on_message) #What happens when you recive a message, is calling the function
    await server.start_listening()
    await client.start_receiving()
    try:
        async with timeout(connections.CONNECTION_TIMEOUT_HEARTBEAT):
            await heartbeat_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("Heartbeat message not received in time")
    
    sockets[0].close() #Close the server socket, to simulate a disconnection
    try:
        async with timeout(connections.CONNECTION_TIMEOUT_HEARTBEAT*2):
            await heartbeat_failed_event.wait()
    except asyncio.TimeoutError:
        pytest.fail("Heartbeat failed event not received in time")

