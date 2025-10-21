import threading
from time import sleep
import unittest

from tests.controller.utils import TestFactory
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import GameServer
from wiredwolf.controller.server_plugins import ChatPlugin


class PluginTest(unittest.TestCase):
    """This class tests plugins attached to a GameServer.
    To obtain a GameServer and its connected clients it uses a TestFactory which by default gives a TCP server and clients.
    If the connection protocol is changed the factory and this test should be adapted in order to run this tests with all protocols available.
    """

    gameServer: GameServer
    clients: list[ClientConnectionHandler]

    def setUp(self) -> None:
        self.gameServer, self.clients = TestFactory.create_tcp_server_with_connected_clients(2, Lobby("Test Lobby"))
        

    def tearDown(self) -> None:
        super().tearDown()
        self.gameServer.close()

    def test_chat_plugin(self):
        MESSAGE: str = "Hello from client 0"
        message_received: threading.Event = threading.Event()

        def on_message(msg: BaseMessage):
            if isinstance(msg, ChatMessage):
                self.assertEqual(msg.message, MESSAGE)
                message_received.set()

        chat_plugin = ChatPlugin()
        self.gameServer.add_plugin(chat_plugin)
        self.clients[1].set_on_message(on_message)
        peer: Peer = Peer("client_0")
        self.clients[0].send_obj(
            ChatMessage(sender=peer, message=MESSAGE)
        )
        waited = 0.0
        while not message_received.is_set() and waited < 3:
            sleep(0.1)
            waited += 0.1
        self.assertTrue(message_received.is_set(), "Chat message was not received by client 1")
