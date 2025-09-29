import socket
import unittest

from wiredwolf.controller.commons import PasswordRequest, Peer
from wiredwolf.controller.connections import MessageHandlerFactory
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser
from wiredwolf.controller.server import GameServer


class ServerTest(unittest.TestCase):
    def test_join_server(self):
        PASSWORD = "password123"
        handler = MessageHandlerFactory.getDefault()
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        server: GameServer = GameServer(lobby)
        client_sock = socket.create_connection(
            ("127.0.0.1", server.connection_socket.getsockname()[1]))
        handler.send_obj(client_sock, Peer("test_user", "127.0.0.1"))
        pass_req: PasswordRequest = handler.receive_obj(client_sock)
        pass_req.password = PASSWORD
        handler.send_obj(client_sock, pass_req)
        self.assertEqual(handler.receive_obj(client_sock), lobby)
        client_sock.close()
        server.stop_new_connections()
        
    def test_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        lobbyBrowser = LobbyBrowser()
        server: GameServer = GameServer(lobby)
        mySelf = Peer("test_user", "127.0.0.1")
        sock, recvLobby = lobbyBrowser.connect_to_lobby_directly(mySelf, ("127.0.0.1", server.connection_socket.getsockname()[1]), PASSWORD)
        self.assertEqual(recvLobby, lobby)
        sock.close()
        server.stop_new_connections()
