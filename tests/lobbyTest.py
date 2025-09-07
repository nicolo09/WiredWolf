import unittest
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser
from wiredwolf.controller.server import GameServer


class LobbyTest(unittest.TestCase):

    def test_peer_connect(self):
        # Start the lobby browser
        lobby_browser = LobbyBrowser()
        lobbies: list[Lobby] = []
        lobby_browser.start_lobby_browser(on_lobby_found=lambda x: lobbies.append(x), on_lobby_lost=lambda x: lobbies.remove(x), on_lobby_updated=lambda x: None) # type: ignore

        # Create and publish a new lobby
        lobby = Lobby("Test Lobby", "password123")
        server = GameServer(lobby)
        lobby_browser.publish_lobby(lobby.name, server.connection_socket)

        # Wait for the lobby to be discovered
        while not lobbies:
            pass

        lobby_browser.stop_publishing_lobby()
        server.stop_new_connections()

    def test_client_connect_to_server(self):
        PASSWORD = "password123"
        lobby: Lobby = Lobby("Test Lobby", PASSWORD)
        server: GameServer = GameServer(lobby)
        browser = LobbyBrowser()
        browser.connect_to_lobby_directly(("127.0.0.1", server.connection_socket.getsockname()[1]), PASSWORD)
        server.stop_new_connections()