import unittest
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


class LobbyTest(unittest.TestCase):

    def test_peer_connect(self):
        # Start the lobby browser
        lobby_browser = TcpMdnsLobbyBrowser()
        lobbies: list[Lobby] = []
        lobby_browser.start_lobby_browser(on_lobby_found=lobbies.append, on_lobby_lost=lobbies.remove, on_lobby_updated=lambda x: None) # type: ignore

        # Create and publish a new lobby
        lobby = Lobby("Test Lobby", "password123")
        server = GameServer(lobby)
        assert isinstance(server.connection_handler, TCPServerConnectionHandler)
        lobby_browser.publish_lobby(lobby.name, server.connection_handler.get_receiver_socket())

        # Wait for the lobby to be discovered
        while not lobbies:
            pass

        lobby_browser.stop_publishing_lobby()
        server.stop_new_connections()
        server.close()

    def test_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        server: GameServer = GameServer(lobby)
        browser = TcpMdnsLobbyBrowser()
        myself = Peer("Test Peer")
        assert isinstance(server.connection_handler, TCPServerConnectionHandler)
        browser.connect_to_lobby_directly(myself, ("127.0.0.1", server.connection_handler.get_receiver_socket().getsockname()[1]), PASSWORD)
        server.stop_new_connections()
        server.close()