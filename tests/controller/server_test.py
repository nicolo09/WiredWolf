import pytest
import pytest_asyncio
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


PASSWORD: str = "password123"


@pytest_asyncio.fixture
async def server_and_owner():
    owner = Peer("Owner Peer")
    lobby = Lobby(owner, "Test Lobby", PASSWORD)
    server = GameServer(lobby)
    await server.start_listening()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def browser():
    lobby_browser = TcpMdnsLobbyBrowser()
    yield lobby_browser


@pytest.mark.asyncio
async def test_join_server(server: GameServer, browser: TcpMdnsLobbyBrowser) -> None:
    handler, lobby = await browser.connect_to_lobby_directly(
        Peer("test_user"), ("127.0.0.1", DEFAULT_SERVER_PORT), PASSWORD
    )
    assert lobby == server.lobby
    await handler.close()


@pytest.mark.asyncio
async def test_multiple_client_connect_to_server(
    server: GameServer, browser: TcpMdnsLobbyBrowser
):
    peer1 = Peer("test_user")
    peer2 = Peer("another_user")
    client_handler1, recv_lobby1 = await browser.connect_to_lobby_directly(
        peer1,
        (
            "127.0.0.1",
            DEFAULT_SERVER_PORT,
        ),
        PASSWORD,
    )
    assert recv_lobby1 == server.lobby
    assert len(recv_lobby1.peers) == 2
    client_handler2, recv_lobby2 = await browser.connect_to_lobby_directly(
        peer2,
        (
            "127.0.0.1",
            DEFAULT_SERVER_PORT,
        ),
        PASSWORD,
    )
    assert recv_lobby2 == server.lobby
    assert len(recv_lobby2.peers) == 3
    assert peer1 in server.lobby.peers
    assert peer2 in server.lobby.peers
    await client_handler1.close()
    await client_handler2.close()
