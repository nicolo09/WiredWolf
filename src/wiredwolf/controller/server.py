import asyncio
import logging
from asyncio import Task
from socket import socketpair
from wiredwolf.controller.commons import (
    PHASE_DURATION_SECONDS,
    DEFAULT_SERVER_PORT,
    FIRST_DAY_PHASE_DURATION_SECONDS,
    MAX_PLAYERS,
    MIN_PLAYERS,
    PLAYERS_TO_ADD_ESCORT,
    PLAYERS_TO_ADD_MEDIUM,
    PasswordRequest,
    Peer,
)
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    ConnectionHandlerFactory,
    ServerConnectionHandler,
)
from wiredwolf.controller.messages import (
    BaseMessage,
    GameStartedMessage,
    LobbyUpdatedMessage,
    PhaseAdvanceMessage,
)
from wiredwolf.controller.lobbies import Lobby
import abc

from wiredwolf.model.game_phases import GamePhase, GamePhaseOutcome
from wiredwolf.model.player import BasicRole, Role, create_players
from wiredwolf.model.game import Game
from wiredwolf.model.game_builder import GameInfoBuilder


class ServerPlugin(abc.ABC):
    """Abstract base class for server pieces that adds common functionalities.
    A plugin should not be added to multiple servers.
    """

    _logger = logging.getLogger(__name__)

    def __init__(self, handled_messages: list[type]) -> None:
        super().__init__()
        self._handled_messages = handled_messages
        self._server = None

    @property
    def server(self) -> "GameServer | None":
        return self._server

    @server.setter
    def server(self, server: "GameServer") -> None:
        self._server = server

    @property
    def handled_messages(self) -> list[type]:
        return self._handled_messages

    async def handle_message(self, message: BaseMessage) -> bool:
        """Handles received messages, subclasses should implement this method but call super().handle_message().

        Args:
            message (BaseMessage): The message to handle.

        Raises:
            ValueError: If the message type is not handled by this plugin.

        Returns:
            bool: True if the message should not be passed to other handlers, False otherwise.
        """
        if type(message) not in self._handled_messages:
            raise ValueError(
                f"Message of type {type(message)} not handled by this plugin."
            )
        if not self._server:
            raise RuntimeError("Plugin is not attached to any server.")
        else:
            return await self.handle_message_sub(message, self._server)
        # To be implemented by subclasses

    @abc.abstractmethod
    async def handle_message_sub(
        self, message: BaseMessage, server: "GameServer"
    ) -> bool:
        pass


class GameServer:
    """Represents a wiredwolf server that manages a game lobby and player connections."""

    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        lobby: Lobby,
        owner_connection: tuple[Peer, asyncio.StreamReader, asyncio.StreamWriter],
    ):
        self._lobby: Lobby = lobby
        self._game: Game | None = None  # Placeholder for game instance
        self._server_conn_handler: ServerConnectionHandler = (
            ConnectionHandlerFactory.get_server_connection_handler(
                on_new_peer=self._on_new_peer,
                on_peer_disconnected=self._on_peer_disconnected,
                on_new_message=self.process_incoming_message,
                owner_connection=owner_connection,
            )
        )
        self._plugins: list[ServerPlugin] = []
        self._game_actual_phase_task: Task[GamePhaseOutcome] | None = None

    async def start_listening(self):
        await self._server_conn_handler.start_listening(
            ("127.0.0.1", DEFAULT_SERVER_PORT)
        )

    @property
    def connection_handler(self) -> ServerConnectionHandler:
        """
        Returns the connection handler for this server.
        """
        return self._server_conn_handler

    @property
    def lobby(self) -> Lobby:
        """Gets the lobby managed by this server.
        Returns:
            Lobby: The lobby managed by this server.
        """
        return self._lobby

    @property
    def game(self) -> Game | None:
        """Gets the game instance managed by this server.
        Returns:
            Game | None: The game instance managed by this server, or None if the game has not started yet.
        """
        return self._game

    async def _on_new_peer(self, peer: Peer):
        self.__logger.info("New peer attempting connection: %s", peer)
        try:
            if self._lobby.is_password_protected():
                # If the lobby is password-protected, ask for the password
                password_request = PasswordRequest()
                await self._server_conn_handler.send_obj(peer, password_request)
                password_response: PasswordRequest = (
                    await self._server_conn_handler.receive_obj(peer)
                )
                if password_response.id != password_request.id:
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Invalid password request.")
                    )
                    return
                if password_response.password and self._lobby.check_password(
                    password_response.password
                ):
                    await self._add_peer_and_notify_updates(peer)
                    # TODO: Check if this is needed await self._server_conn_handler.send_obj(peer, self._lobby)
                else:
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Incorrect password.")
                    )
            else:
                # If no password is set, add the peer directly
                await self._add_peer_and_notify_updates(peer)
                # TODO: Check if this is needed await self._server_conn_handler.send_obj(peer, self._lobby)
        except Exception as e:
            self.__logger.error("Error handling new peer %s: %s", peer, e)

    async def _on_peer_disconnected(self, peer: Peer):
        self.__logger.info("Peer disconnected: %s", peer)
        if peer in self._lobby.peers:
            self._lobby.peers.remove(peer)
            await self._notify_updated_lobby()
        else:
            self.__logger.warning("Received disconnection for unknown peer: %s", peer)

    async def _notify_updated_lobby(self):
        for p in self._lobby.peers:
            await self._server_conn_handler.send_obj(
                p, LobbyUpdatedMessage(self._lobby)
            )
        self.__logger.info("Lobby updated. Current peers: %s", self._lobby.peers)

    async def _add_peer_and_notify_updates(self, peer: Peer):
        # Update lobby
        self._lobby.peers.add(peer)
        # Notify other peers of the updated lobby sending the updated lobby object
        await self._notify_updated_lobby()

    async def send_to_all(self, message: BaseMessage):
        """Sends a message to all connected peers in the lobby."""
        # TODO: Change to have them sent concurrently
        for peer in self._lobby.peers:
            try:
                await self._server_conn_handler.send_obj(peer, message)
            except Exception as e:
                self.__logger.error("Error sending message to %s: %s", peer, e)

    def add_plugin(self, plugin: ServerPlugin):
        """Adds a new message handling plugin to this server

        Args:
            plugin (ServerPlugin): The plugin to add.
        """
        self._plugins.append(plugin)
        plugin.server = self

    async def start_game(self) -> None:
        self.__logger.info("Starting game in lobby: %s", self._lobby)
        # Create game instance based on lobby peers and roles
        if len(self._lobby.peers) < MIN_PLAYERS:
            raise ValueError("Not enough players to start the game.")
        if len(self._lobby.peers) > MAX_PLAYERS:
            raise ValueError("Too many players to start the game.")
        roles: set[Role] = {BasicRole.CLAIRVOYANT}
        if len(self._lobby.peers) >= PLAYERS_TO_ADD_MEDIUM:
            # Add Medium for 9+ players
            roles.add(BasicRole.MEDIUM)
        if len(self._lobby.peers) >= PLAYERS_TO_ADD_ESCORT:
            # Add Escort and an extra werewolf for 16+ players
            roles.add(BasicRole.ESCORT)
        game_info = GameInfoBuilder.new().with_roles(roles).build()
        players = create_players(
            {peer.uuid: peer.name for peer in self._lobby.peers},
            game_info.get_all_handled_roles(),
        )
        self._game = Game(players, game_info)
        assert self._game.phase is GamePhase.DAY_DISCUSSION
        self.__logger.info("Game started with players: %s", players)
        await self.send_to_all(GameStartedMessage(self._game.get_game_status()))
        self._game_actual_phase_task = asyncio.create_task(
            self.wait_and_advance_game(FIRST_DAY_PHASE_DURATION_SECONDS)
        )
        self._game_actual_phase_task.add_done_callback(
            lambda outcome: self.on_game_phase_advanced(outcome)
        )

    def on_game_phase_advanced(self, outcome: Task[GamePhaseOutcome]):
        # If the game is not over, set up the next phase timer
        if outcome.result().new_phase is GamePhase.VILLAGERS_VICTORY:
            self.__logger.info("Game over. Villagers have won.")
            return
        elif outcome.result().new_phase is GamePhase.WEREWOLVES_VICTORY:
            self.__logger.info("Game over. Werewolves have won.")
            return
        else:
            self.__logger.info(
                "Setting up timer for next phase: %s seconds.",
                PHASE_DURATION_SECONDS,
            )
            self._game_actual_phase_task = asyncio.create_task(
                self.wait_and_advance_game(PHASE_DURATION_SECONDS)
            )
        self._game_actual_phase_task.add_done_callback(
            lambda outcome: self.on_game_phase_advanced(outcome)
        )

    async def wait_and_advance_game(self, time_seconds: int) -> GamePhaseOutcome:
        """Waits for the specified time and then advances the game phase.

        Args:
            time_seconds (int): The time to wait in seconds.
        """
        if not self._game:
            raise RuntimeError("Game has not been started yet.")
        self.__logger.info(
            "Waiting for %d seconds before advancing the game phase.",
            time_seconds,
        )
        await asyncio.sleep(time_seconds)
        outcome = self._game.advance_phase()
        self.__logger.info("Game phase advanced. Outcome: %s", outcome)
        await self.send_to_all(PhaseAdvanceMessage(outcome))
        return outcome

    def stop_new_connections(self):
        """Stop accepting new peer connections"""
        self._server_conn_handler.stop_new_connections()

    async def close(self):
        """Closes the server and all associated connections."""
        self.stop_new_connections()
        await self._server_conn_handler.close()

    async def process_incoming_message(self, message: BaseMessage):
        """Handles a message coming from a peer.

        Args:
            message (BaseMessage): The message to handle.
        """
        handled = False
        for plugin in self._plugins:
            if type(message) in plugin.handled_messages:
                handled = True
                should_stop: bool = await plugin.handle_message(message)
                self.__logger.info(
                    "Message of type %s handled by plugin %s", type(message), plugin
                )
                if should_stop:
                    return
        if not handled:
            self.__logger.error(
                "No plugin found to handle message of type %s", type(message)
            )
            raise ValueError(
                f"No plugin found to handle message of type {type(message)}"
            )


class GameServerFactory:
    @staticmethod
    async def get_game_server(
        lobby: Lobby,
    ) -> tuple[GameServer, ClientConnectionHandler]:
        """Creates and returns a new GameServer instance and the owner ClientConnectionHandler.

        Args:
            lobby (Lobby): The lobby to be managed by the server.
        Returns:
            tuple[GameServer, ClientConnectionHandler]: The created GameServer and the owner's ClientConnectionHandler.
        """
        from wiredwolf.controller.server_plugins import get_plugins_list
        client_socket, server_socket = socketpair()
        client_reader, client_writer = await asyncio.open_connection(sock=client_socket)
        server_reader, server_writer = await asyncio.open_connection(sock=server_socket)
        server = GameServer(
            lobby, owner_connection=(lobby.owner, server_reader, server_writer)
        )
        for plugin in await get_plugins_list():
            server.add_plugin(plugin)
        client_conn_handler = ConnectionHandlerFactory.get_client_connection_handler(
            lobby.owner, client_reader, client_writer
        )
        return server, client_conn_handler
