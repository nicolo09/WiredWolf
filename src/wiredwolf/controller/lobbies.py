from enum import Enum


class Peer:

    __name = None
    __address = None

    def __init__(self, name, address):
        self.__name = name
        self.__address = address

    @property
    def address(self):
        return self.__address

    @property
    def name(self):
        return self.__name


class LobbyState(Enum):
    WAITING_FOR_PLAYERS = "waiting_for_players"
    STARTING = "starting"
    PLAYING = "playing"
    CHANGING_MASTER = "changing_master"
    WAITING_PLAYER_RECONNECT = "waiting_player_reconnect"


class LobbyBrowser:
    def __init__(self):
        pass

    def discover_lobbies(self):
        # TODO: This method would contain logic to discover available lobbies (probably to be made async)
        pass

    def publish_lobby(self, lobby):
        # TODO: This method would contain logic to publish a new lobby
        pass


class Lobby:

    __peers = []
    __state = None
    __name = None
    __password = None

    def __init__(self, name=None, password=None):
        self.__peers = []
        self.__state = LobbyState.WAITING_FOR_PLAYERS
        self.__name = name
        self.__password = password

    def add_peer(self, peer):
        self.__peers.append(peer)

    def remove_peer(self, peer):
        self.__peers.remove(peer)

    @property
    def peers(self):
        return self.__peers

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state):
        self.__state = state

    def send_chat_message(self, message):
        # TODO: Implement chat message sending logic
        pass

    def choose_player(self, player):
        # TODO: Implement player selection logic
        pass

    def vote_guilty(self):
        # TODO: Implement voting logic
        pass

    def vote_innocent(self):
        # TODO: Implement voting logic
        pass
