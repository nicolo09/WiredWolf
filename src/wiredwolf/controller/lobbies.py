import abc
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import dataclasses
import uuid
from wiredwolf.controller.connections import (
    AsyncTCPClientConnectionHandler,
    AsyncTCPMessageHandler,
)
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    MessageHandlerFactory,
)

from wiredwolf.controller.commons import CONNECTION_TIMEOUT, MAX_PLAYERS, Peer
from wiredwolf.controller.commons import PasswordRequest
from wiredwolf.controller.services import CallbackServiceListener, ServiceManager


SERVICE_TYPE: str = "_wiredwolflobby._tcp.local."


@dataclass
class LobbyInfo:
    """
    Represents the information of a lobby that can be sent to a client to be displayed in the lobby browser.
    """
    name: str
    has_password: bool
    uuid: str
    peers_number: int = 1
    max_peers: int = MAX_PLAYERS


@dataclass
class Lobby:
    owner: Peer
    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))  #TODO: Possible UUID collision will have to be handled in server code
    password: str | None = None
    peers: set[Peer] = dataclasses.field(init=False, default_factory=set[Peer])

    def __post_init__(self):
        """Initializes the lobby by adding the owner to the peers list."""
        self.peers.add(self.owner)

    def lobby_info(self) -> LobbyInfo:
        """Returns a LobbyInfo object representing the information of this lobby."""
        return LobbyInfo(
            name=self.name,
            has_password=self.is_password_protected(),
            uuid=self.uuid,
            peers_number=len(self.peers),
            max_peers=MAX_PLAYERS,
        )

    def check_password(self, passwd: str) -> bool:
        """Checks if the provided password matches the lobby's password."""
        return self.password == passwd

    def is_password_protected(self) -> bool:
        """Returns whether the lobby is password-protected."""
        return self.password is not None


class LobbyNotFoundError(Exception):
    """Exception raised when a lobby is not found."""


class LobbyBrowser(abc.ABC):
    """
    Abstract base class for lobby browsers.
    """

    @abc.abstractmethod
    def start_lobby_browser(
        self,
        on_lobby_found: Callable[[LobbyInfo], None],
        on_lobby_lost: Callable[[str], None],
        on_lobby_updated: Callable[[LobbyInfo], None]
    ) -> None:
        """Starts the lobby browser to discover available lobbies.
        When appropriate the lobby browser should be stopped by calling stop_lobby_browser().

        args:
            on_lobby_found (Callable[[LobbyInfo], None]): Callback invoked when a new lobby is found.
            on_lobby_lost (Callable[[str], None]): Callback invoked when a lobby is lost.
            on_lobby_updated (Callable[[LobbyInfo], None]): Callback invoked when a lobby is updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stop_lobby_browser(self) -> None:
        """Stops the lobby browser from discovering lobbies."""
        raise NotImplementedError

    @abc.abstractmethod
    def publish_lobby(self, lobby_info: LobbyInfo, receiver_port: int) -> None:
        """Publishes a lobby to be discovered by other players."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        raise NotImplementedError

    @abc.abstractmethod
    async def connect_to_lobby_by_name(
        self, my_self: Peer, lobby_name: str, lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        """
        Connects to a lobby with the given name and password.

        Args:
            lobby_name (str): The name of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[ClientConnectionHandler, Lobby]: The connected client handler and the joined lobby.
        """
        raise NotImplementedError


class TcpMdnsLobbyBrowser(LobbyBrowser):
    """
    Handles the discovery and creations/publishment of game lobbies through mDNS.
    """

    # TODO Handle same lobby name collisions

    def __init__(self):
        self._service_manager: ServiceManager = ServiceManager(SERVICE_TYPE)
        self._browser = None
        self._published_lobby_service_info = None

    def start_lobby_browser(
        self,
        on_lobby_found: Callable[[LobbyInfo], None],
        on_lobby_lost: Callable[[str], None],
        on_lobby_updated: Callable[[LobbyInfo], None],
    ) -> None:
        """Starts the lobby browser to discover available lobbies.
        When appropriate the lobby browser should be stopped by calling stop_lobby_browser().

        args:
            on_lobby_found (Callable[[LobbyInfo], None]): Callback invoked when a new lobby is found.
            on_lobby_lost (Callable[[str], None]): Callback invoked when a lobby is lost.
            on_lobby_updated (Callable[[LobbyInfo], None]): Callback invoked when a lobby is updated.
        """
        if not self._browser:
            listener = CallbackServiceListener(
                on_service_added=lambda name, props: on_lobby_found(self._get_lobby_info_from_service_properties(props)),
                on_service_removed=on_lobby_lost,
                on_service_updated=lambda name, props: on_lobby_updated(self._get_lobby_info_from_service_properties(props)),
            )
            self._browser = self._service_manager.get_service_browser(listener)
        else:
            raise RuntimeError("Lobby browser is already running.")

    def _get_lobby_info_from_service_properties(self, properties: dict[str, str]) -> LobbyInfo:
        """Helper method to convert service properties to a LobbyInfo object."""
        return LobbyInfo(
            name=properties.get("name", "Unknown Lobby"),
            has_password=properties.get("has_password", "false").lower() == "true",
            uuid=properties.get("uuid", ""),
            peers_number=int(properties.get("peers_number", "1")),
            max_peers=int(properties.get("max_peers", str(MAX_PLAYERS))),
        )

    def _get_service_properties_from_lobby_info(self, lobby_info: LobbyInfo) -> dict[str, str]:
        """Helper method to convert LobbyInfo to service properties."""
        return {
            "name": lobby_info.name,
            "has_password": str(lobby_info.has_password).lower(),
            "uuid": lobby_info.uuid,
            "peers_number": str(lobby_info.peers_number),
            "max_peers": str(lobby_info.max_peers),
        }

    def stop_lobby_browser(self) -> None:
        """Stops the lobby browser from discovering lobbies."""
        if self._browser:
            self._browser.cancel()
            self._browser = None
        else:
            raise RuntimeError("Lobby browser is not running.")

    def publish_lobby(self, lobby_info: LobbyInfo, receiver_port: int) -> None: #TODO Move receiver_port to constructor
        """Publishes a lobby to the network so that it can be discovered by other players."""
        if not self._published_lobby_service_info:
            self._published_lobby_service_info = self._service_manager.register_service(
                name=lobby_info.name, receiverPort=receiver_port, properties=self._get_service_properties_from_lobby_info(lobby_info)
            )
        else:
            raise RuntimeError("There is already a lobby being published.")

    def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        if self._published_lobby_service_info:
            self._service_manager.unregister_service(self._published_lobby_service_info)
            self._published_lobby_service_info = None
        else:
            raise RuntimeError("No lobby is currently being published.")

    async def _connect(
        self, endpoint: tuple[str, int], my_self: Peer, lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        try:
            async with asyncio.timeout(CONNECTION_TIMEOUT):
                msg_handler: AsyncTCPMessageHandler = AsyncTCPMessageHandler(
                    MessageHandlerFactory.getDefaultSerializer()
                )
                reader, writer = await asyncio.open_connection(endpoint[0], endpoint[1])
                # Sending my peer info to the server
                await msg_handler.send_obj(writer, my_self)
                # Expecting PasswordRequest or lobby
                recv_msg = await msg_handler.receive_obj(reader)
                if isinstance(recv_msg, PasswordRequest):
                    # Server requested a password...
                    if lobby_password:
                        # ...send the password
                        recv_msg.password = lobby_password
                        await msg_handler.send_obj(writer, recv_msg)
                        lobby = await msg_handler.receive_obj(reader)
                        if isinstance(lobby, Exception):
                            # The server returned an error
                            writer.close()
                            raise lobby
                        else:
                            # The server returned a lobby, successfully joined
                            return AsyncTCPClientConnectionHandler(
                                my_self, reader, writer
                            ), lobby
                    else:
                        # ...but no password was provided
                        writer.close()
                        raise ValueError("Lobby requires a password.")
                elif isinstance(recv_msg, Lobby):
                    if lobby_password:
                        # Password was provided but not needed
                        writer.close()
                        raise ValueError("Lobby does not require a password.")
                    # Successfully joined the lobby
                    return AsyncTCPClientConnectionHandler(
                        my_self, reader, writer
                    ), recv_msg
                else:
                    writer.close()
                    raise RuntimeError("Unexpected message received.")
        except asyncio.TimeoutError:
            raise TimeoutError("Connection to lobby timed out.")

    async def connect_to_lobby_directly(
        self, my_self: Peer, address: tuple[str, int], lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        """
        Connects directly to a lobby at the given address with the provided password.

        Args:
            address (tuple[str, int]): The (IP, port) address of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[ClientConnectionHandler, Lobby]: The connected client handler and the joined lobby.
        """

        return await self._connect(address, my_self, lobby_password)

    async def connect_to_lobby_by_name(
        self, my_self: Peer, lobby_name: str, lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        """
        Connects to a lobby with the given name and password.

        Args:
            lobby_name (str): The name of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[ClientConnectionHandler, Lobby]: The connected client handler and the joined lobby.
        """
        try:
            ip, port = await self._service_manager.get_service_endpoint(lobby_name)
        except TimeoutError:
            raise LobbyNotFoundError(f"Could not find lobby '{lobby_name}'.")

        return await self._connect((ip, port), my_self, lobby_password)

    # TODO: This should also handle reconnection to previously joined lobbies in case of crash/network issues

class LobbyBrowserFactory:
    @staticmethod
    def get_lobby_browser() -> LobbyBrowser:
        """Creates and returns a new LobbyBrowser instance.

        Returns:
            LobbyBrowser: The created lobby browser.
        """
        return TcpMdnsLobbyBrowser()