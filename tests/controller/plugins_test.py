import asyncio
from venv import logger
import pytest
import pytest_asyncio
from tests.controller.utils import TestFactory
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import GameServer


@pytest_asyncio.fixture
async def gameServerAndClients():
    gameServer: GameServer
    clients: list[ClientConnectionHandler]
    owner = Peer("owner_peer")
    gameServer, clients = await TestFactory.create_tcp_server_with_connected_clients(
        2, Lobby(owner, "Test Lobby")
    )
    yield gameServer, clients
    await gameServer.close()
    for client in clients:
        await client.close()

@pytest.mark.asyncio
async def test_chat_plugin(
    gameServerAndClients: tuple[GameServer, list[ClientConnectionHandler]],
):
    _, clients = gameServerAndClients
    MESSAGE: str = "Hello from client 0"
    message_received = asyncio.Event()

    logger.info("Starting test_chat_plugin")

    def on_message(msg: BaseMessage):
        logger.info("Client 1 received message: %s", msg)
        assert isinstance(msg, ChatMessage)
        assert msg.message == MESSAGE
        message_received.set()

    clients[1].set_on_message(on_message)
    await clients[0].send_obj(ChatMessage(sender=clients[0].my_self, message=MESSAGE))
    await message_received.wait()
    assert message_received.is_set(), "Chat message was not received by client 1"

#TODO: Test for wrong sender in ChatMessage