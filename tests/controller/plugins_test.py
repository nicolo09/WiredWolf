import threading
from venv import logger

import pytest

from tests.controller.utils import TestFactory
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import GameServer
from wiredwolf.controller.server_plugins import ChatPlugin


@pytest.fixture
def gameServerAndClients():
    gameServer: GameServer
    clients: list[ClientConnectionHandler]
    gameServer, clients = TestFactory.create_tcp_server_with_connected_clients(
        2, Lobby("Test Lobby")
    )
    yield gameServer, clients
    gameServer.close()
    for client in clients:
        client.close()


def test_chat_plugin(
    gameServerAndClients: tuple[GameServer, list[ClientConnectionHandler]],
):
    gameServer, clients = gameServerAndClients
    MESSAGE: str = "Hello from client 0"
    message_received: threading.Event = threading.Event()

    logger.info("Starting test_chat_plugin")

    def on_message(msg: BaseMessage):
        logger.info("Client 1 received message: %s", msg)
        assert isinstance(msg, ChatMessage)
        assert msg.message == MESSAGE
        message_received.set()

    clients[1].set_on_message(on_message)
    chat_plugin = ChatPlugin()
    gameServer.add_plugin(chat_plugin)
    peer: Peer = Peer("client_0")
    clients[0].send_obj(ChatMessage(sender=peer, message=MESSAGE))
    message_received.wait(timeout=5)
    assert message_received.is_set(), "Chat message was not received by client 1"
