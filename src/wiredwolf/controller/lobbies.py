from collections.abc import Callable
from enum import Enum
import logging
from socket import socket, inet_aton
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf


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

    def discover_lobbies(self) -> None:
        # TODO: This method would contain logic to discover available lobbies (probably to be made async)
        pass

    def publish_lobby(self, lobby) -> None:
        # TODO: This method would contain logic to publish a new lobby
        pass


class CallbackServiceListener(ServiceListener):

    def __init__(self, on_service_added: Callable[[str], None], on_service_removed: Callable[[str], None], on_service_updated: Callable[[str], None]) -> None:
        super().__init__()
        self.__on_service_added = on_service_added
        self.__on_service_removed = on_service_removed
        self.__on_service_updated = on_service_updated

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_added(name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_removed(name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_updated(name)


class ServiceManager():

    logger = logging.getLogger("wiredwolf.lobby_service")

    __port: int

    def __init__(self, service_type: str):
        self.__zeroconf = Zeroconf()
        self.__service_type = service_type

    def register_service(self, name, receiverSocket: socket) -> ServiceInfo:
        self.__port = receiverSocket.getsockname()[1]
        self.logger.info(
            f"Registering service {name} on port {self.__port}...")
        serviceInfo = ServiceInfo(
            type_=self.__service_type,
            name=name + "." + self.__service_type,
            addresses=[inet_aton("127.0.0.1")],
            port=self.__port,
            properties={}
        )
        self.__zeroconf.register_service(serviceInfo)
        self.logger.info(f"Service {name} registered successfully.")
        return serviceInfo

    def unregister_service(self, info: ServiceInfo) -> None:
        self.logger.info(f"Unregistering service {info.name}...")
        self.__zeroconf.unregister_service(info)
        self.logger.info(f"Service {info.name} unregistered successfully.")

    def get_service_listener(self, service_type, on_service_added, on_service_removed, on_service_updated) -> CallbackServiceListener:
        self.logger.info(
            "Starting service listener for type" + service_type + "...")
        return CallbackServiceListener(
            on_service_added=on_service_added,
            on_service_removed=on_service_removed,
            on_service_updated=on_service_updated
        )
        
    def get_service_browser(self, listener: ServiceListener) -> ServiceBrowser:
        return ServiceBrowser(self.__zeroconf, self.__service_type, listener)


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
