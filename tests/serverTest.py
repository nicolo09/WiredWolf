import socket
import unittest

from wiredwolf.controller.commons import PasswordRequest, Peer
from wiredwolf.controller.connections import MessageHandlerFactory, TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


class ServerTest(unittest.TestCase):
    def test_join_server(self):
        PASSWORD = "password123"
        handler = MessageHandlerFactory.getDefault()
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        server: GameServer = GameServer(lobby)
        assert isinstance(server.connection_handler, TCPServerConnectionHandler)
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
        lobbyBrowser = TcpMdnsLobbyBrowser()
        server: GameServer = GameServer(lobby)
        mySelf = Peer("test_user")
        assert isinstance(server.connection_handler, TCPServerConnectionHandler)
        sock, recvLobby = lobbyBrowser.connect_to_lobby_directly(mySelf, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]), PASSWORD)
        self.assertEqual(recvLobby, lobby)
        sock.close()
        server.stop_new_connections()
        
    def test_multiple_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        lobbyBrowser = TcpMdnsLobbyBrowser()
        server: GameServer = GameServer(lobby)
        mySelf = Peer("test_user")
        otherPeer = Peer("other_user")
        assert isinstance(server.connection_handler, TCPServerConnectionHandler)
        mySock, recvLobby = lobbyBrowser.connect_to_lobby_directly(mySelf, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]), PASSWORD)
        self.assertEqual(recvLobby, lobby)
        otherSock, recvLobby2 = lobbyBrowser.connect_to_lobby_directly(otherPeer, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]), PASSWORD)
        self.assertIn(otherPeer, recvLobby2.peers)
        self.assertIn(mySelf, recvLobby2.peers)
        mySock.close()
        otherSock.close()
        server.stop_new_connections()
