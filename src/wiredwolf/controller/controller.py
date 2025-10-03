from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import TCPServerConnectionHandler
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.server import GameServer


class GameController:

    _lobby_browser: TcpMdnsLobbyBrowser
    _lobby: Lobby
    _server: GameServer
    _mySelf: Peer

    def __init__(self):
        self._lobby_browser = TcpMdnsLobbyBrowser()
        self._mySelf = Peer("Player") # TODO: Default name, should be set by user

    def create_lobby(self, name: str, password: str | None = None):
        self._lobby = Lobby(name=name, password=password)
        self._server = GameServer(self._lobby)
        if (isinstance(self._server.connection_handler, TCPServerConnectionHandler)):
            self._server.connection_handler.get_receiver_socket()
            self._lobby_browser.publish_lobby(
                self._lobby.name, self._server.connection_handler.get_receiver_socket())
            return self._lobby
        else:
            raise RuntimeError("Server connection handler is not TCP.")

    def join_lobby(self, lobby_name: str, lobby_password: str | None):
        self._lobby_browser.connect_to_lobby_by_name(self._mySelf, lobby_name, lobby_password)

    @property
    def lobby_browser(self):
        return self._lobby_browser

    @property
    def lobby(self):
        return self._lobby
