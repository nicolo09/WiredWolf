import socket
import unittest

from wiredwolf.controller.commons import PasswordRequest, Peer
from wiredwolf.controller.connections import MessageHandlerFactory
from wiredwolf.controller.connections import TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


class ServerTest(unittest.TestCase):
    def test_join_server(self):
        PASSWORD = "password123"
        handler = MessageHandlerFactory.getDefault()
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        server: GameServer = GameServer(lobby)
        assert isinstance(server.connection_handler,
                          TCPServerConnectionHandler)
        client_sock = socket.create_connection(
            ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]))
        handler.send_obj(client_sock, Peer("test_user"))
        pass_req: PasswordRequest = handler.receive_obj(client_sock)
        pass_req.password = PASSWORD
        handler.send_obj(client_sock, pass_req)
        self.assertEqual(handler.receive_obj(client_sock), lobby)
        client_sock.close()
        server.stop_new_connections()

    def test_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        lobby_browser = TcpMdnsLobbyBrowser()
        server: GameServer = GameServer(lobby)
        my_self = Peer("test_user")
        assert isinstance(server.connection_handler,
                          TCPServerConnectionHandler)
        _, recv_lobby = lobby_browser.connect_to_lobby_directly(
            my_self, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]), PASSWORD)
        self.assertEqual(recv_lobby, lobby)
        server.stop_new_connections()

    def test_multiple_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        lobby_browser = TcpMdnsLobbyBrowser()
        server: GameServer = GameServer(lobby)
        my_self = Peer("test_user")
        other_peer = Peer("other_user")
        assert isinstance(server.connection_handler,
                          TCPServerConnectionHandler)
        _, recv_lobby = lobby_browser.connect_to_lobby_directly(
            my_self, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1])
            , PASSWORD)
        self.assertEqual(recv_lobby, lobby)
        _, recv_lobby2 = lobby_browser.connect_to_lobby_directly(
            other_peer,
            ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1])
            , PASSWORD)
        self.assertIn(other_peer, recv_lobby2.peers)
        self.assertIn(my_self, recv_lobby2.peers)
        server.stop_new_connections()
