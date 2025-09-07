from wiredwolf.controller.lobbies import LobbyBrowser
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.server import GameServer


class GameController:

    _lobby_browser: LobbyBrowser
    _lobby: Lobby
    _server: GameServer

    def __init__(self):
        self._lobby_browser = LobbyBrowser()

    def create_lobby(self, name: str, password: str | None = None):
        self._lobby = Lobby(name=name, password=password)
        self._server = GameServer(self._lobby)
        self._lobby_browser.publish_lobby(
            self._lobby.name, self._server.connection_socket)
        return self._lobby

    def join_lobby(self, lobby_name: str, lobby_password: str | None):
        self._lobby_browser.connect_to_lobby_by_name(lobby_name, lobby_password)

    @property
    def lobby_browser(self):
        return self._lobby_browser

    @property
    def lobby(self):
        return self._lobby
