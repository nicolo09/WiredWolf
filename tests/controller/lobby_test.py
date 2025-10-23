import unittest

import pytest
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer

@pytest.fixture()
def lobby():
    lobby = Lobby("Test Lobby", "password123")
    yield lobby

@pytest.fixture()
def server(lobby: Lobby):
    server = GameServer(lobby)
    yield server
    server.stop_new_connections()
    server.close()

@pytest.fixture()
def browser():
    browser = TcpMdnsLobbyBrowser()
    yield browser


class LobbyTest(unittest.TestCase):
    PASSWORD: str = "password123"
    lobby: Lobby
    server: GameServer
    browser: TcpMdnsLobbyBrowser

    def setUp(self) -> None:
        self.lobby = Lobby("Test Lobby", self.PASSWORD)
        self.server = GameServer(self.lobby)
        self.browser = TcpMdnsLobbyBrowser()

    def tearDown(self) -> None:
        self.server.stop_new_connections()
        self.server.close()

    def test_client_connect_to_server(self):
        myself = Peer("Test Peer")
        assert isinstance(self.server.connection_handler, TCPServerConnectionHandler)
        handler, recv_lobby = self.browser.connect_to_lobby_directly(
            myself,
            (
                "localhost",
                self.server.connection_handler.get_receiver_socket().getsockname()[1],
            ),
            self.PASSWORD,
        )
        self.assertEqual(recv_lobby, self.lobby)
        handler.close()

    def test_peer_connect(self):
        # Start the lobby browser
        self.browser = TcpMdnsLobbyBrowser()
        lobbies: list[Lobby] = []
        self.browser.start_lobby_browser(on_lobby_found=lobbies.append, on_lobby_lost=lobbies.remove, on_lobby_updated=lambda x: None,)  # type: ignore

        assert isinstance(self.server.connection_handler, TCPServerConnectionHandler)
        self.browser.publish_lobby(
            self.lobby.name, self.server.connection_handler.get_receiver_socket()
        )
        # Wait for the lobby to be discovered
        while not lobbies:
            pass
        self.browser.stop_publishing_lobby()
        self.browser.stop_lobby_browser()
        self.server.stop_new_connections()
        self.server.close()
