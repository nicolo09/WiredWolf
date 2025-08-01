from wiredwolf.controller.lobbies import LobbyBrowser
from wiredwolf.controller.lobbies import Lobby


class GameController:

    __lobby_browser = None
    __lobby = None

    def __init__(self):
        self.__lobby_browser = LobbyBrowser()

    def create_lobby(self, name=None, password=None):
        self.__lobby = Lobby(name=name, password=password)
        return self.__lobby

    @property
    def lobby_browser(self):
        return self.__lobby_browser

    @property
    def lobby(self):
        return self.__lobby
