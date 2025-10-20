from http import client
import unittest

from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import ClientConnectionHandler, TCPClientConnectionHandler, TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.server import GameServer
from wiredwolf.controller.server_plugins import ChatPlugin
import socket

class PluginTest(unittest.TestCase):
    
    gameServer: GameServer
    client: ClientConnectionHandler

    def setUp(self) -> None:
        super().setUp()
        lobby: Lobby = Lobby("Test Lobby")
        myself: Peer = Peer("Test Peer")
        self.gameServer = GameServer(lobby) #TODO: Factory to get connection handlers
        if (type(self.gameServer.connection_handler) is TCPServerConnectionHandler):
            self.client: ClientConnectionHandler = TCPClientConnectionHandler(myself, self.gameServer.connection_handler.get_receiver_socket().getsockname())
        else:
            raise Exception("Unsupported connection handler for testing")
        
    def tearDown(self) -> None:
        super().tearDown()
        self.gameServer.close()

    def test_chat_plugin(self):
        chat_plugin = ChatPlugin()
        self.gameServer.add_plugin(chat_plugin)
        