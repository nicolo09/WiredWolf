import socket
import unittest

from wiredwolf.controller.commons import Peer
import wiredwolf.controller.connections as connections


class BaseConnectionTest(unittest.TestCase):
    def test_base_connection_handler(self):
        handler = connections.ConnectionHandler()
        self.assertEqual(handler.add_length_prefix(b"test"), b'0004test')

    def test_send_and_receive(self):
        server_socket, client_socket = socket.socketpair()
        handler = connections.ConnectionHandler()
        handler._send(server_socket, b"test")  # type: ignore
        received = handler._receive(client_socket)  # type: ignore
        self.assertEqual(received, b"test")


class ServerConnectionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.serverConnHandler = connections.ServerConnectionHandler(
            lambda peer: self.assertIsInstance(peer, connections.Peer), ("127.0.0.1", 0))
        self.serverName = self.serverConnHandler.get_receiver_socket().getsockname()

    def tearDown(self) -> None:
        self.serverConnHandler.stop_new_connections()

    def test_server_creation(self):
        self.assertIsNotNone(self.serverName)

    def test_client_connect_to_server(self):
        def assertPeer(peer: Peer) -> None:
            self.assertIsInstance(peer, connections.Peer)
            self.assertEqual(peer.name, peer_name)

        peer_name = "client"
        myServer = connections.ServerConnectionHandler(
            assertPeer, ("127.0.0.1", 0))
        myServerName = myServer.get_receiver_socket().getsockname()
        clientConnHandler = connections.ClientConnectionHandler(
            connections.Peer(peer_name, "127.0.0.1"))
        clientSocket = clientConnHandler.connect_to_server(myServerName)
        self.assertIsNotNone(clientSocket)
        myServer.stop_new_connections()
