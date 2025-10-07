import socket
import unittest

from wiredwolf.controller.commons import Peer
import wiredwolf.controller.connections as connections
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser


class BaseConnectionTest(unittest.TestCase):
    def test_too_long_data_raises(self):
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        with self.assertRaises(ValueError):
            handler.add_length_prefix(b"x" * (int("9"*handler.PREFIX_LEN)+1))

    def test_base_connection_handler(self):
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        self.assertEqual(handler.add_length_prefix(b"test"), b'0004test')

    def test_send_and_receive(self):
        server_socket, client_socket = socket.socketpair()
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        handler.send(server_socket, b"test")
        received = handler.receive(client_socket)
        self.assertEqual(received, b"test")


class ServerConnectionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.serverConnHandler = connections.TCPServerConnectionHandler(
            lambda peer: self.assertIsInstance(peer, connections.Peer), ("127.0.0.1", 0))
        self.serverName = self.serverConnHandler.get_receiver_socket().getsockname()

    def tearDown(self) -> None:
        self.serverConnHandler.stop_new_connections()

    def test_server_creation(self):
        self.assertIsNotNone(self.serverName)
