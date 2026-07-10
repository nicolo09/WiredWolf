import abc
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import dataclasses
import logging

from zeroconf import ServiceInfo
from wiredwolf.controller.connections import (
    AsyncTCPClientConnectionHandler,
    AsyncTCPMessageHandler,
    ClientConnectionHandler,
    MessageHandlerFactory,
)

from wiredwolf.controller.commons import (
    CONNECTION_TIMEOUT,
    MAX_PLAYERS,
    MIN_PLAYERS,
    Peer,
    lobby_id_generator,
)
from wiredwolf.controller.commons import PasswordRequest
from wiredwolf.controller.messages import LobbyUpdatedMessage
from wiredwolf.controller.services import CallbackCachedServiceListener, ServiceManager


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
    uuid: str = field(
        default_factory=lambda: lobby_id_generator()
    )  # TODO: Possible UUID collision will have to be handled in services code
    password: str | None = None
    peers: set[Peer] = dataclasses.field(init=False, default_factory=set[Peer])
    max_peers: int = MAX_PLAYERS

    def __post_init__(self):
        """Initializes the lobby by adding the owner to the peers list."""
        self.max_peers = max(self.max_peers, MIN_PLAYERS)
        self.peers.add(self.owner)

    def lobby_info(self) -> LobbyInfo:
        """Returns a LobbyInfo object representing the information of this lobby."""
        return LobbyInfo(
            name=self.name,
            has_password=self.is_password_protected(),
            uuid=self.uuid,
            peers_number=len(self.peers),
            max_peers=self.max_peers,
        )

    def check_password(self, passwd: str) -> bool:
        """
        Checks if the provided password matches the lobby's password.
        
        Returns:
            bool: True if the password matches, False otherwise.
        """
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
        on_lobby_lost: Callable[[LobbyInfo], None],
        on_lobby_updated: Callable[[LobbyInfo], None],
    ) -> None:
        """Starts the lobby browser to discover available lobbies.
        When appropriate the lobby browser should be stopped by calling stop_lobby_browser().

        args:
            on_lobby_found (Callable[[LobbyInfo], None]): Callback invoked when a new lobby is found.
            on_lobby_lost (Callable[[LobbyInfo], None]): Callback invoked when a lobby is lost.
            on_lobby_updated (Callable[[LobbyInfo], None]): Callback invoked when a lobby is updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stop_lobby_browser(self) -> None:
        """Stops the lobby browser from discovering lobbies."""
        raise NotImplementedError

    @abc.abstractmethod
    async def publish_lobby(self, lobby_info: LobbyInfo, receiver_port: int) -> None:
        """Publishes a lobby to be discovered by other players."""
        raise NotImplementedError

    @abc.abstractmethod
    async def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        raise NotImplementedError

    @property
    def is_publishing_lobby(self) -> bool:
        """Returns whether a lobby is currently being published."""
        raise NotImplementedError

    @abc.abstractmethod
    async def connect_to_lobby_by_id(
        self, my_self: Peer, lobby_id: str, lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        """
        Connects to a lobby with the given ID and password.

        Args:
            lobby_id (str): The ID of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[ClientConnectionHandler, Lobby]: The connected client handler and the joined lobby.
        """
        raise NotImplementedError


class TcpMdnsLobbyBrowser(LobbyBrowser):
    """
    Handles the discovery and creations/publishment of game lobbies through mDNS.
    """

    __logger = logging.getLogger(__name__)

    # TODO Handle same lobby name collisions

    def __init__(self):
        self._service_manager: ServiceManager = ServiceManager(SERVICE_TYPE)
        self._browser = None
        self._published_lobby_service_info: list[ServiceInfo] | None = None
        # We keep track of found lobbies to be able to remove them when they are lost
        self._found_lobbies: dict[str, LobbyInfo] = {}  # Maps lobby UUIDs to their info

    @property
    def is_publishing_lobby(self) -> bool:
        """Returns whether a lobby is currently being published."""
        return self._published_lobby_service_info is not None

    def start_lobby_browser(
        self,
        on_lobby_found: Callable[[LobbyInfo], None],
        on_lobby_lost: Callable[[LobbyInfo], None],
        on_lobby_updated: Callable[[LobbyInfo], None],
    ) -> None:
        """Starts the lobby browser to discover available lobbies.
        When appropriate the lobby browser should be stopped by calling stop_lobby_browser().

        args:
            on_lobby_found (Callable[[LobbyInfo], None]): Callback invoked when a new lobby is found.
            on_lobby_lost (Callable[[LobbyInfo], None]): Callback invoked when a lobby is lost.
            on_lobby_updated (Callable[[LobbyInfo], None]): Callback invoked when a lobby is updated.
        """

        def on_lobby_found_cb(name: str, props: dict[str, str]) -> None:
            """Callback invoked when a new lobby is found. This is used to add the lobby to the discovered lobbies list."""
            try:
                self._found_lobbies[name] = self._get_lobby_info_from_service_properties(
                    props
                )
                on_lobby_found(self._found_lobbies[name])
            except ValueError as e:
                self.__logger.warning("Error adding lobby %s: %s", name, e)

        def on_lobby_lost_cb(name: str) -> None:
            """Callback invoked when a lobby is lost. This is used to remove the lobby from the discovered lobbies list."""
            if name in self._found_lobbies:
                on_lobby_lost(self._found_lobbies.pop(name))

        def on_lobby_updated_cb(name: str, props: dict[str, str]) -> None:
            """Callback invoked when a lobby is updated. This is used to update the lobby information in the discovered lobbies list."""
            if name in self._found_lobbies:
                try:
                    self._found_lobbies[name] = (
                        self._get_lobby_info_from_service_properties(props)
                    )
                    on_lobby_updated(self._found_lobbies[name])
                except ValueError as e:
                    self.__logger.warning("Error updating lobby %s: %s", name, e)

        if not self._browser:
            listener = CallbackCachedServiceListener(
                on_service_added=on_lobby_found_cb,
                on_service_removed=on_lobby_lost_cb,
                on_service_updated=on_lobby_updated_cb,
            )
            self._browser = self._service_manager.get_service_browser(listener)
        else:
            raise RuntimeError("Lobby browser is already running.")

    def _get_lobby_info_from_service_properties(
        self, properties: dict[str, str]
    ) -> LobbyInfo:
        """Helper method to convert service properties to a LobbyInfo object."""
        if "name" not in properties or "uuid" not in properties:
            raise ValueError("Service properties do not include 'name' and 'uuid'.")
        return LobbyInfo(
            name=properties.get("name", "Unknown Lobby"),
            has_password=properties.get("has_password", "false").lower() == "true",
            uuid=properties.get("uuid", ""),
            peers_number=int(properties.get("peers_number", "1")),
            max_peers=int(properties.get("max_peers", str(MAX_PLAYERS))),
        )

    def _get_service_properties_from_lobby_info(
        self, lobby_info: LobbyInfo
    ) -> dict[str, str]:
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

    async def publish_lobby(
        self, lobby_info: LobbyInfo, receiver_port: int
    ) -> None:  # TODO Move receiver_port to constructor
        """Publishes a lobby to the network so that it can be discovered by other players."""
        if not self._published_lobby_service_info:
            self._published_lobby_service_info = await self._service_manager.register_service(
                name=lobby_info.uuid,  # Using lobby UUID as service name to avoid name collisions
                receiverPort=receiver_port,
                properties=self._get_service_properties_from_lobby_info(lobby_info),
            )
        else:
            raise RuntimeError("There is already a lobby being published.")

    async def stop_publishing_lobby(self) -> None:
        """Stops publishing the lobby."""
        if self._published_lobby_service_info:
            await self._service_manager.unregister_service(self._published_lobby_service_info)
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
                while True:
                    # Expecting PasswordRequest or LobbyUpdatedMessage (in case no password is required) in response
                    recv_msg = await msg_handler.receive_obj(reader)
                    if isinstance(recv_msg, PasswordRequest):
                        if lobby_password:
                            # Server requested a password and one was provided, send it
                            recv_msg.password = lobby_password
                            await msg_handler.send_obj(writer, recv_msg)
                        else:
                            # Server requested a password but none was provided
                            writer.close()
                            raise ValueError("Lobby requires a password.")
                    elif isinstance(recv_msg, LobbyUpdatedMessage):
                        return AsyncTCPClientConnectionHandler(my_self, reader, writer), recv_msg.lobby
                    elif isinstance(recv_msg, Exception): 
                        # The server returned an error
                        writer.close()
                        self.__logger.error("Error received from server: %s", recv_msg)
                        raise recv_msg
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

    async def connect_to_lobby_by_id(
        self, my_self: Peer, lobby_id: str, lobby_password: str | None
    ) -> tuple[ClientConnectionHandler, Lobby]:
        """
        Connects to a lobby with the given ID and password.

        Args:
            lobby_id (str): The ID of the lobby to connect to.
            lobby_password (str | None): The password for the lobby, or None if not required.

        Returns:
            tuple[ClientConnectionHandler, Lobby]: The connected client handler and the joined lobby.
        """
        try:
            endpoints = await self._service_manager.get_service_endpoints(lobby_id)
        except TimeoutError:
            raise LobbyNotFoundError(f"Could not find lobby '{lobby_id}'.")

        for ip, port in endpoints:
            try:
                return await self._connect((ip, port), my_self, lobby_password)
            except (ConnectionError, TimeoutError):
                self.__logger.warning(f"Failed to connect to lobby {lobby_id} at {ip}:{port}, trying next endpoint if available...")
                continue
        self.__logger.error(f"All connection attempts to lobby {lobby_id} failed.")
        raise LobbyNotFoundError(f"Could not connect to lobby '{lobby_id}'.")

    # TODO: This should also handle reconnection to previously joined lobbies in case of crash/network issues


class LobbyBrowserFactory:
    @staticmethod
    def get_lobby_browser() -> LobbyBrowser:
        """Creates and returns a new LobbyBrowser instance.

        Returns:
            LobbyBrowser: The created lobby browser.
        """
        return TcpMdnsLobbyBrowser()
