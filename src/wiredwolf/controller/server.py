import asyncio
import logging
from asyncio import Task
from socket import socketpair
from wiredwolf.controller import commons
from wiredwolf.controller.connections.connections import (
    ClientConnectionHandler,
    ConnectionHandlerFactory,
    ServerConnectionHandler,
)
from wiredwolf.controller.messages import (
    AcknowledgeMessage,
    BaseMessage,
    GameStartedMessage,
    LobbyUpdatedMessage,
    NotAcknowledgeMessage,
    PhaseAdvanceMessage,
)
from wiredwolf.controller.lobbies import Lobby
import abc

from wiredwolf.model.game_phases import GamePhase, GamePhaseOutcome
from wiredwolf.model.player import BasicRole, Role, create_players
from wiredwolf.model.game import Game
from wiredwolf.model.game_builder import GameInfoBuilder

class DuplicateIdException(Exception):
    """Exception raised when a peer tries to connect with an ID that already exists in the lobby."""
    
    def __init__(self, new_id: str | None = None, message="Duplicate ID detected."):
        super().__init__(message)
        self.new_id: str | None = new_id

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

    async def handle_message(self, message: BaseMessage) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        """Handles received messages, subclasses should implement this method but call super().handle_message().

        Args:
            message (BaseMessage): The message to handle.

        Raises:
            ValueError: If the message type is not handled by this plugin.

        Returns:
            tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]: A tuple containing the response message and a boolean indicating whether the message should not be passed to other handlers.
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
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        pass


class GameServer:
    """Represents a wiredwolf server that manages a game lobby and player connections."""

    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        lobby: Lobby,
        owner_connection: tuple[commons.Peer, asyncio.StreamReader, asyncio.StreamWriter],
        game: Game | None = None,
    ):
        """Creates a new GameServer

        Args:
            lobby (Lobby): The lobby this server will serve the game to
            owner_connection (tuple[commons.Peer, asyncio.StreamReader, asyncio.StreamWriter]): The direct connection of the owner of the lobby to the server
            game (Game | None, optional): A Game instance to resume a game. Defaults to None, which means a new game will be created when starting the game.
        """
        self._lobby: Lobby = lobby
        self._game: Game | None = game
        self._server_conn_handler: ServerConnectionHandler = (
            ConnectionHandlerFactory.get_server_connection_handler(
                bind_address=(commons.DEFAULT_SERVER_HOST, commons.DEFAULT_SERVER_PORT),
                on_new_peer=self._on_new_peer,
                on_peer_disconnected=self._on_peer_disconnected,
                on_peer_recovery=self._on_peer_recovery,
                on_new_message=self.process_incoming_message,
                owner_connection=owner_connection,
            )
        )
        self._plugins: list[ServerPlugin] = []
        self._game_actual_phase_task: Task[GamePhaseOutcome] | None = None

    async def start_listening(self):
        await self._server_conn_handler.start_listening()

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

    async def _on_new_peer(self, peer: commons.Peer):
        self.__logger.info("New peer attempting connection: %s", peer)
        try:
            if self._lobby.is_password_protected():
                # If the lobby is password-protected, ask for the password
                password_request = commons.PasswordRequest()
                await self._server_conn_handler.send_obj(peer, password_request)
                password_response: commons.PasswordRequest = (
                    await self._server_conn_handler.receive_obj(peer)
                )
                if password_response.id != password_request.id:
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Invalid password request.")
                    )
                    return
                if not password_response.password or not self._lobby.check_password(
                    password_response.password
                ):
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Incorrect password.")
                    )
                    return
                
            if self._check_peer_uuid_collision(peer.uuid):
                self.__logger.warning(
                    "Peer %s attempted to connect with a duplicate UUID %s. Generating a new UUID.", peer.name, peer.uuid
                )
                new_id_generated = False
                while not new_id_generated:
                    new_uuid = commons.peer_id_generator()
                    if not self._check_peer_uuid_collision(new_uuid):
                        self.__logger.info(
                            "Generated new UUID %s for peer %s", new_uuid, peer.name
                        )
                        await self._server_conn_handler.send_obj(peer, DuplicateIdException(new_id=new_uuid))
                        new_id_generated = True
                return
                
            await self._add_peer_and_notify_updates(peer)
        except Exception as e:
            self.__logger.error("Error handling new peer %s: %s", peer, e)

    async def _on_peer_recovery(self, peer: commons.Peer):
        await self._server_conn_handler.send_obj(peer, (self._lobby, self._game.get_game_status() if self._game else None))
        self.__logger.info("Peer recovered: %s", peer)

    async def _on_peer_disconnected(self, peer: commons.Peer):
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

    async def _add_peer_and_notify_updates(self, peer: commons.Peer):
        if len(self._lobby.peers) >= self._lobby.max_peers:
            self.__logger.warning("Lobby is full. Cannot add peer: %s", peer)
            await self._server_conn_handler.send_obj(
                peer, ValueError("Lobby is full. Cannot join.")
            )
            return
        if self._game_actual_phase_task is not None: # If the game is not running, the task is None
            self.__logger.warning("Game already started. Cannot add peer: %s", peer)
            await self._server_conn_handler.send_obj(
                peer, ValueError("Game already started. Cannot join.")
            )
            return
        # Update lobby
        self._lobby.peers.add(peer)
        # Notify other peers of the updated lobby sending the updated lobby object
        await self._notify_updated_lobby()
        
    def _check_peer_uuid_collision(self, id: str) -> bool:
        """Checks if a peer's UUID collides with any existing peer in the lobby.

        Args:
            id (str): The UUID to check for collision.

        Returns:
            bool: True if there is a collision, False otherwise.
        """
        return any(p.uuid == id for p in self._lobby.peers)

    async def send_to_peer(self, peer: commons.Peer, message: BaseMessage):
        """Sends a message to a specific peer.

        Args:
            peer (Peer): The peer to send the message to.
            message (BaseMessage): The message to send.
        """
        try:
            await self._server_conn_handler.send_obj(peer, message)
        except Exception as e:
            self.__logger.error("Error sending message to %s: %s", peer, e)

    async def send_to_uuid(self, peer_uuid: str, message: BaseMessage):
        """Sends a message to a specific peer identified by their UUID.

        Args:
            peer_uuid (str): The UUID of the peer to send the message to.
            message (BaseMessage): The message to send.
        """
        peer = next((p for p in self._lobby.peers if p.uuid == peer_uuid), None)
        if peer:
            await self.send_to_peer(peer, message)
        else:
            self.__logger.warning("No peer found with UUID: %s", peer_uuid)

    async def send_to_all(self, message: BaseMessage):
        """Sends a message to all connected peers in the lobby."""
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
        if self._game is None:
            # Create game instance based on lobby peers and roles
            if len(self._lobby.peers) < commons.MIN_PLAYERS:
                raise ValueError("Not enough players to start the game.")
            if len(self._lobby.peers) > commons.MAX_PLAYERS:
                raise ValueError("Too many players to start the game.")
            roles: set[Role] = {BasicRole.CLAIRVOYANT}
            if len(self._lobby.peers) >= commons.PLAYERS_TO_ADD_MEDIUM:
                # Add Medium for 9+ players
                roles.add(BasicRole.MEDIUM)
            if len(self._lobby.peers) >= commons.PLAYERS_TO_ADD_ESCORT:
                # Add Escort and an extra werewolf for 16+ players
                roles.add(BasicRole.ESCORT)
            game_info = GameInfoBuilder.new().with_roles(roles).build()
            players = create_players(
                {peer.uuid: peer.name for peer in self._lobby.peers},
                game_info.get_all_handled_roles(),
            )
            self._game = Game(players, game_info)
            self.__logger.info("Game started with players: %s", players)
            await self.send_to_all(GameStartedMessage(self._game.get_game_status()))
            self._game_actual_phase_task = asyncio.create_task(
                self.wait_and_advance_game(commons.FIRST_DAY_PHASE_DURATION_SECONDS)
            )
            self._game_actual_phase_task.add_done_callback(
                lambda outcome: self.on_game_phase_advanced(outcome)
            )
        else:
            self.__logger.info("Game resumed with players: %s", self._game.players)
            await self.send_to_all(GameStartedMessage(self._game.get_game_status()))
            self._game_actual_phase_task = asyncio.create_task(
                self.wait_and_advance_game(commons.PHASE_DURATION_SECONDS)
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
            duration = (
                commons.BALLOT_RESULT_PHASE_DURATION_SECONDS 
                if outcome.result().new_phase is GamePhase.BALLOT_RESULT 
                else commons.PHASE_DURATION_SECONDS
            )
            self.__logger.info(
                "Setting up timer for next phase: %s seconds.",
                duration,
            )
            self._game_actual_phase_task = asyncio.create_task(
                self.wait_and_advance_game(duration)
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
        await self.send_to_all(PhaseAdvanceMessage(outcome, self._game.get_game_status()))
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
        should_stop = False
        response = None
        for plugin in self._plugins:
            if type(message) in plugin.handled_messages and not should_stop:
                handled = True
                response, should_stop = await plugin.handle_message(message)
                self.__logger.info(
                    "Message of type %s handled by plugin %s", type(message), plugin
                )
        if not handled:
            self.__logger.error(
                "No plugin found to handle message of type %s", type(message)
            )
            raise ValueError(
                f"No plugin found to handle message of type {type(message)}"
            )
        elif response is not None:
            self.__logger.info("Message of type %s processed with response: %s", type(message), response)
            if message.sender is not None:
                await self.connection_handler.send_obj(message.sender, response)
            else:
                self.__logger.warning("Message has no sender to respond to.")

class GameServerFactory:
    @staticmethod
    async def get_game_server(
        lobby: Lobby, game: Game | None = None
    ) -> tuple[GameServer, ClientConnectionHandler]:
        """Creates and returns a new GameServer instance and the owner ClientConnectionHandler.

        Args:
            lobby (Lobby): The lobby to be managed by the server.
            game (Game | None): A Game instance to resume a game. Defaults to None, which means a new game will be created when starting the game.
        Returns:
            tuple[GameServer, ClientConnectionHandler]: The created GameServer and the owner's ClientConnectionHandler.
        """
        from wiredwolf.controller.server_plugins import get_plugins_list
        client_socket, server_socket = socketpair()
        client_reader, client_writer = await asyncio.open_connection(sock=client_socket)
        server_reader, server_writer = await asyncio.open_connection(sock=server_socket)
        server = GameServer(
            lobby, owner_connection=(lobby.owner, server_reader, server_writer), game=game
        )
        for plugin in await get_plugins_list():
            server.add_plugin(plugin)
        client_conn_handler = ConnectionHandlerFactory.get_client_connection_handler(
            lobby.owner, client_reader, client_writer, ("localhost", commons.DEFAULT_SERVER_PORT)
        )
        return server, client_conn_handler
