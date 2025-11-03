from asyncio import StreamReader, StreamWriter, timeout
import asyncio
from typing import Any
import pytest
import pytest_asyncio
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
import wiredwolf.controller.connections as connections
from wiredwolf.controller.messages import BaseMessage


def test_too_long_data_raises():
    handler = connections.AsyncTCPMessageHandler(connections.PickleSerializer())
    with pytest.raises(ValueError):
        handler.add_length_prefix(b"x" * (int("9" * handler.PREFIX_LEN) + 1))


def test_base_connection_handler():
    handler = connections.AsyncTCPMessageHandler(connections.PickleSerializer())
    assert handler.add_length_prefix(b"test") == b"0004test"


def test_send_and_receive():
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

    async def timeout_fun():
        async with timeout(5):
            await server()
            await client()

    asyncio.run(timeout_fun())


@pytest_asyncio.fixture
async def server_conn_handler():
    async def check_is_instance(obj: Any, cls: type):
        assert isinstance(obj, cls)

    serverConnHandler = connections.AsyncTCPServerConnectionHandler(
        lambda peer: check_is_instance(peer, Peer),
        lambda msg: check_is_instance(msg, BaseMessage),
    )
    await serverConnHandler.start_listening(("127.0.0.1", DEFAULT_SERVER_PORT))
    yield serverConnHandler
    await serverConnHandler.close()


def test_server_creation(
    server_conn_handler: connections.AsyncTCPServerConnectionHandler,
):
    assert server_conn_handler is not None
