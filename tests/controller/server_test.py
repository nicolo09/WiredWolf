import asyncio
import socket
import unittest

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, PasswordRequest, Peer
from wiredwolf.controller.connections import MessageHandlerFactory, AsyncTCPMessageHandler
from wiredwolf.controller.connections import AsyncTCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


class ServerTest(unittest.TestCase):
    PASSWORD: str = "password123"
    server: GameServer
    handler: AsyncTCPMessageHandler
    lobby: Lobby

    def setUp(self) -> None:
        super().setUp()
        self.handler = MessageHandlerFactory.getDefault()
        self.lobby = Lobby("Test Lobby", self.PASSWORD)
        self.server: GameServer = GameServer(self.lobby)

    def tearDown(self) -> None:
        super().tearDown()
        self.server.stop_new_connections()
        self.server.close()
"""
    def test_join_server(self):
        assert isinstance(self.server.connection_handler, AsyncTCPServerConnectionHandler)
        client_sock = socket.create_connection(
            (
                "127.0.0.1",
                DEFAULT_SERVER_PORT,
            )
        )
        asyncio.run(self.handler.send_obj(client_sock, Peer("test_user")))
        pass_req: PasswordRequest = self.handler.receive_obj(client_sock)
        pass_req.password = self.PASSWORD
        self.handler.send_obj(client_sock, pass_req)
        self.assertEqual(self.handler.receive_obj(client_sock), self.lobby)
        client_sock.close()

    def test_client_connect_to_server(self):
        lobby_browser = TcpMdnsLobbyBrowser()
        my_self = Peer("test_user")
        assert isinstance(self.server.connection_handler, TCPServerConnectionHandler)
        _, recv_lobby = lobby_browser.connect_to_lobby_directly(
            my_self,
            (
                "127.0.0.1",
                self.server.connection_handler.get_receiver_socket().getsockname()[1],
            ),
            self.PASSWORD,
        )
        self.assertEqual(recv_lobby, self.lobby)

    def test_multiple_client_connect_to_server(self):
        lobby_browser = TcpMdnsLobbyBrowser()
        my_self = Peer("test_user")
        other_peer = Peer("other_user")
        assert isinstance(self.server.connection_handler, TCPServerConnectionHandler)
        _, recv_lobby = lobby_browser.connect_to_lobby_directly(
            my_self,
            (
                "127.0.0.1",
                self.server.connection_handler.get_receiver_socket().getsockname()[1],
            ),
            self.PASSWORD,
        )
        self.assertEqual(recv_lobby, self.lobby)
        _, recv_lobby2 = lobby_browser.connect_to_lobby_directly(
            other_peer,
            (
                "127.0.0.1",
                self.server.connection_handler.get_receiver_socket().getsockname()[1],
            ),
            self.PASSWORD,
        )
        self.assertIn(other_peer, recv_lobby2.peers)
        self.assertIn(my_self, recv_lobby2.peers)
"""