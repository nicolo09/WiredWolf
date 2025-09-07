from wiredwolf.controller import TIMEOUT
from wiredwolf.controller.connections import MessageHandler, MessageHandlerFactory, PickleSerializer
from collections.abc import Callable
from enum import Enum
import socket

from wiredwolf.controller.commons import Peer
from wiredwolf.controller.commons import PasswordRequest
from wiredwolf.controller.services import CallbackServiceListener, ServiceManager


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

    _peers: list[Peer] = []
    _state: LobbyState = LobbyState.WAITING_FOR_PLAYERS
    _name: str = ""
    _password: str | None = None
    _message_handler: MessageHandler

    def __init__(self, name: str, password: str | None = None):
        """Initializes a Lobby instance.

        Args:
            name (str): The name of the lobby.
            password (str | None, optional): The password for the lobby, if any. Defaults to None (not password protected).
        """
        self._peers = []
        self._state = LobbyState.WAITING_FOR_PLAYERS
        self._name = name
        self._password = password
        self._message_handler = MessageHandler(PickleSerializer())

    def add_peer(self, peer: Peer, socket: socket.socket):
        self._peers.append(peer)

    def remove_peer(self, peer: Peer):
        self._peers.remove(peer)

    def is_password_protected(self) -> bool:
        """Returns whether the lobby is password-protected."""
        return self._password is not None

    @property
    def message_handler(self) -> MessageHandler:
        """Returns the message handler for the lobby."""
        return self._message_handler

    @property
    def peers(self) -> list[Peer]:
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
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Lobby):
            return NotImplemented
        return (self._name == value._name and
                self._password == value._password and
                self._peers == value._peers and
                self._state == value._state)


class LobbyBrowser:
    """
    Handles the discovery and creations/publishment of game lobbies through mDNS.
    """
    # TODO Handle same lobby name collisions

    _service_manager: ServiceManager

    def __init__(self):
        self._service_manager = ServiceManager(SERVICE_TYPE)
        self._browser = None
        self._published_lobby_service_info = None

    def start_lobby_browser(self, on_lobby_found: Callable[[str], None], on_lobby_lost: Callable[[str], None], on_lobby_updated: Callable[[str], None]) -> None:
        """Starts the lobby browser to discover available lobbies. When appropriate the lobby browser should be stopped by calling stop_lobby_browser()."""
        if not self._browser:
            listener = CallbackServiceListener(
                on_service_added=on_lobby_found,
                on_service_removed=on_lobby_lost,
                on_service_updated=on_lobby_updated
            )
            self._browser = self._service_manager.get_service_browser(
                listener)
        else:
            raise RuntimeError("Lobby browser is already running.")

    def stop_lobby_browser(self) -> None:
        """Stops the lobby browser from discovering lobbies."""
        if self._browser:
            self._browser.cancel()
            self._browser = None
        else:
            raise RuntimeError("Lobby browser is not running.")

    def publish_lobby(self, lobby_name: str, connection_socket: socket.socket) -> None:
        """Publishes a lobby to the network so that it can be discovered by other players."""
        if not self._published_lobby_service_info:
            self._published_lobby_service_info = self._service_manager.register_service(
                name=lobby_name, receiverSocket=connection_socket)
        else:
            raise RuntimeError("There is already a lobby being published.")

    def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        if self._published_lobby_service_info:
            self._service_manager.unregister_service(
                self._published_lobby_service_info)
            self._published_lobby_service_info = None
        else:
            raise RuntimeError("No lobby is currently being published.")

    def _connect(self, sock: socket.socket, lobby_password: str | None) -> tuple[socket.socket, Lobby]:
        msgHandler = MessageHandlerFactory.getDefault() #TODO: Allow custom message handlers by constructor parameter
        # Expecting PasswordRequest or lobby
        recvMsg = msgHandler.receive_obj(sock)
        if isinstance(recvMsg, PasswordRequest):
            # Server requested a password...
            if lobby_password:
                # ...send the password
                recvMsg.password = lobby_password
                msgHandler.send_obj(sock, recvMsg)
                lobby = msgHandler.receive_obj(sock)
                if isinstance(lobby, Exception):
                    # The server returned an error
                    sock.close()
                    raise lobby
                else:
                    # The server returned a lobby, successfully joined
                    return sock, lobby
            else:
                # ...but no password was provided
                sock.close()
                raise ValueError("Lobby requires a password.")
        elif isinstance(recvMsg, Lobby):
            if lobby_password:
                # Password was provided but not needed
                sock.close()
                raise ValueError("Lobby does not require a password.")
            # Successfully joined the lobby
            return sock, recvMsg
        else:
            sock.close()
            raise RuntimeError("Unexpected message received.")

    def connect_to_lobby_directly(self, address: tuple[str, int], lobby_password: str | None) -> tuple[socket.socket, Lobby]:
        """
        Connects directly to a lobby at the given address with the provided password.

        Args:
            address (tuple[str, int]): The (IP, port) address of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[socket.socket, Lobby]: The connected socket and the joined lobby.
        """

        sock = socket.create_connection(address, timeout=TIMEOUT)
        return self._connect(sock, lobby_password)

    def connect_to_lobby_by_name(self, lobby_name: str, lobby_password: str | None) -> tuple[socket.socket, Lobby]:
        """
        Connects to a lobby with the given name and password.

        Args:
            lobby_name (str): The name of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[socket.socket, Lobby]: The connected socket and the joined lobby.
        """

        sock = self._service_manager.connect_to_service(lobby_name)
        return self._connect(sock, lobby_password)
