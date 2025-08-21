from wiredwolf.controller.connections import MessageHandler, PickleSerializer
from collections.abc import Callable
from enum import Enum
import logging
import socket
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from wiredwolf.controller.commons import Peer


SERVICE_TYPE: str = "_wiredwolflobby._tcp.local."


class LobbyState(Enum):
    """Represents the various states a lobby can be in."""

    WAITING_FOR_PLAYERS = "waiting_for_players"
    STARTING = "starting"
    PLAYING = "playing"
    CHANGING_MASTER = "changing_master"
    WAITING_PLAYER_RECONNECT = "waiting_player_reconnect"


class Lobby:
    """Represents a game lobby."""

    _peers: dict[Peer, socket.socket] = {}
    _state: LobbyState = LobbyState.WAITING_FOR_PLAYERS
    _name: str = ""
    _password: str | None = None
    _message_handler: MessageHandler

    def __init__(self, name: str, password: str | None = None):
        self._peers = {}
        self._state = LobbyState.WAITING_FOR_PLAYERS
        self._name = name
        self._password = password
        self._message_handler = MessageHandler(PickleSerializer())

    def add_peer(self, peer: Peer, socket: socket.socket):
        self._peers[peer] = socket

    def remove_peer(self, peer: Peer):
        self._peers.pop(peer, None)

    def is_password_protected(self) -> bool:
        """Returns whether the lobby is password-protected."""
        return self._password is not None

    @property
    def message_handler(self) -> MessageHandler:
        """Returns the message handler for the lobby."""
        return self._message_handler

    @property
    def peers(self) -> dict[Peer, socket.socket]:
        """Returns the list of peers in the lobby."""
        return self._peers

    @property
    def state(self) -> LobbyState:
        """Returns the current state of the lobby."""
        return self._state

    @property
    def name(self) -> str:
        """Returns the name of the lobby."""
        return self._name

    def check_password(self, password: str) -> bool:
        """Checks if the provided password matches the lobby's password."""
        return self._password == password  # TODO: Hash? Maybe not, since it's not saved persistently

    @state.setter
    def state(self, state: LobbyState):
        self._state = state

    def send_chat_message(self, message: str):
        # TODO: Implement chat message sending logic
        pass

    def choose_player(self, player: Peer):
        # TODO: Implement player selection logic
        pass

    def vote_guilty(self):
        # TODO: Implement voting logic
        pass

    def vote_innocent(self):
        # TODO: Implement voting logic
        pass


class LobbyBrowser:
    """
    Handles the discovery and creations/publishment of game lobbies through mDNS.
    """

    def __init__(self):
        self.__service_manager = ServiceManager(SERVICE_TYPE)
        self.__browser = None
        self.__published_lobby_service_info = None

    def start_lobby_browser(self, on_lobby_found: Callable[[str], None], on_lobby_lost: Callable[[str], None], on_lobby_updated: Callable[[str], None]) -> None:
        """Starts the lobby browser to discover available lobbies. When appropriate the lobby browser should be stopped by calling stop_lobby_browser()."""
        if not self.__browser:
            listener = CallbackServiceListener(
                on_service_added=on_lobby_found,
                on_service_removed=on_lobby_lost,
                on_service_updated=on_lobby_updated
            )
            self.__browser = self.__service_manager.get_service_browser(
                listener)
        else:
            raise RuntimeError("Lobby browser is already running.")

    def stop_lobby_browser(self) -> None:
        """Stops the lobby browser from discovering lobbies."""
        if self.__browser:
            self.__browser.cancel()
            self.__browser = None
        else:
            raise RuntimeError("Lobby browser is not running.")

    def publish_lobby(self, lobby_name: str, connection_socket: socket.socket) -> None:
        """Publishes a lobby to the network so that it can be discovered by other players."""
        if not self.__published_lobby_service_info:
            self.__published_lobby_service_info = self.__service_manager.register_service(
                name=lobby_name, receiverSocket=connection_socket)
        else:
            raise RuntimeError("There is already a lobby being published.")

    def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        if self.__published_lobby_service_info:
            self.__service_manager.unregister_service(
                self.__published_lobby_service_info)
            self.__published_lobby_service_info = None
        else:
            raise RuntimeError("No lobby is currently being published.")


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
        self.__on_service_updated(name)  # TODO: Implement service update logic


class ServiceManager():

    __logger = logging.getLogger(__name__)

    __port: int

    def __init__(self, service_type: str):
        self.__zeroconf = Zeroconf()
        self.__service_type = service_type

    def register_service(self, name: str, receiverSocket: socket.socket) -> ServiceInfo:
        self.__port = receiverSocket.getsockname()[1]
        self.__logger.info(
            f"Registering service {name} on port {self.__port}...")
        serviceInfo = ServiceInfo(
            type_=self.__service_type,
            name=name + "." + self.__service_type,
            addresses=[socket.inet_aton("127.0.0.1")],
            port=self.__port,
            properties={}
        )
        self.__zeroconf.register_service(serviceInfo)
        self.__logger.info(f"Service {name} registered successfully.")
        return serviceInfo

    def unregister_service(self, info: ServiceInfo) -> None:
        self.__logger.info(f"Unregistering service {info.name}...")
        self.__zeroconf.unregister_service(info)
        self.__logger.info(f"Service {info.name} unregistered successfully.")

    def get_service_listener(self, service_type: str, on_service_added: Callable[[str], None], on_service_removed: Callable[[str], None], on_service_updated: Callable[[str], None]) -> CallbackServiceListener:
        self.__logger.info(
            "Starting service listener for type" + service_type + "...")
        return CallbackServiceListener(
            on_service_added=on_service_added,
            on_service_removed=on_service_removed,
            on_service_updated=on_service_updated
        )

    def get_service_browser(self, listener: ServiceListener) -> ServiceBrowser:
        return ServiceBrowser(self.__zeroconf, self.__service_type, listener)
