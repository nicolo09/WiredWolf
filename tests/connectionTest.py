import socket
import unittest

import wiredwolf.controller.connections as connections


class ServerConnectionTest(unittest.TestCase):
    
    def setUp(self) -> None:
        self.serverConnHandler = connections.ServerConnectionHandler(lambda peer: self.assertIsInstance(peer, connections.Peer), ("127.0.0.1", 0))
        self.serverName = self.serverConnHandler.get_receiver_socket().getsockname()
        
    def tearDown(self) -> None:
        self.serverConnHandler.stop_new_connections()
    
    def test_server_creation(self):
        self.assertIsNotNone(self.serverName)        

    def test_connect_to_server(self):
        clientSocket = socket.create_connection(self.serverName)
        self.assertIsNotNone(clientSocket)
        self.assertTrue(clientSocket.getsockname() != self.serverName)

    def test_client_connect_to_server(self):
        clientConnHandler = connections.ClientConnectionHandler(connections.Peer("client", "localhost"))
        clientConnHandler.connect_to_server(self.serverName)