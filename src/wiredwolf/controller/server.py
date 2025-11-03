import logging
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, PasswordRequest, Peer
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    ConnectionHandlerFactory,
    ServerConnectionHandler
)
from wiredwolf.controller.messages import BaseMessage
from wiredwolf.controller.lobbies import Lobby
import abc
import random

from wiredwolf.model.player import Player, Role
from wiredwolf.model.game import Game
from wiredwolf.model.role_extensions import BasicGameInfoBuilder


class ServerPlugin(abc.ABC):
    """Abstract base class for server pieces that adds common functionalities.
    A plugin should not be added to multiple servers.
    """

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
    async def handle_message_sub(self, message: BaseMessage, server: "GameServer") -> bool:
        pass


class GameServer:
    """Represents a wiredwolf server that manages a game lobby and player connections."""

    __logger = logging.getLogger(__name__)

    def __init__(self, lobby: Lobby):  # TODO: Add owner peer and socket on init
        self._lobby: Lobby = lobby
        self._game: Game | None = None  # Placeholder for game instance
        self._server_conn_handler: ServerConnectionHandler = (
            ConnectionHandlerFactory.get_default_server_handler(
                self._on_new_peer, self.process_incoming_message
            )
        )
        self._players: dict[Peer, ClientConnectionHandler] = {}
        self._plugins: list[ServerPlugin] = []

    async def start_listening(self):
        await self._server_conn_handler.start_listening(("127.0.0.1", DEFAULT_SERVER_PORT))

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

    async def _on_new_peer(self, peer: Peer):
        self.__logger.info("New peer attempting connection: %s", peer)
        try:
            if self._lobby.is_password_protected():
                # If the lobby is password-protected, ask for the password
                req = PasswordRequest()
                await self._server_conn_handler.send_obj(peer, req)
                resp: PasswordRequest = await self._server_conn_handler.receive_obj(peer)
                if resp.id != req.id:
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Invalid password request.")
                    )
                    return
                if resp.password and self._lobby.check_password(resp.password):
                    await self._add_peer_and_notify_updates(peer)
                    await self._server_conn_handler.send_obj(peer, self._lobby)
                else:
                    await self._server_conn_handler.send_obj(
                        peer, ValueError("Incorrect password.")
                    )
            else:
                # If no password is set, add the peer directly
                await self._add_peer_and_notify_updates(peer)
                await self._server_conn_handler.send_obj(peer, self._lobby)
        except Exception as e:
            self.__logger.error("Error handling new peer %s: %s", peer, e)

    async def _add_peer_and_notify_updates(self, peer: Peer):
        # Update lobby
        self._lobby.add_peer(peer)
        # Notify other peers of the updated lobby sending the updated lobby object
        for p in self._lobby.peers:
            await self._server_conn_handler.send_obj(p, self._lobby)
        self.__logger.info(
            "Peer %s joined the lobby. Current peers: %s", peer, self._lobby.peers
        )

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

    def start_game(self) -> None:
        self.__logger.info("Starting game in lobby: %s", self._lobby)
        # Create game instance based on lobby peers and roles
        if len(self._lobby.peers) < 8:
            raise ValueError("Not enough players to start the game.")
        game_info_builder = BasicGameInfoBuilder.default().with_clairvoyant()
        roles = [Role.WEREWOLF] # Start with this werewolf plus the one added by game_info_builder
        if len(self._lobby.peers) >= 8:
            game_info_builder = game_info_builder.with_clairvoyant() # Add Clairvoyant for 8+ players
        if len(self._lobby.peers) >= 9:
            game_info_builder = game_info_builder.with_medium() # Add Medium for 9+ players
        if len(self._lobby.peers) >= 16:
            game_info_builder = game_info_builder.with_escort() # Add Escort and an extra werewolf for 16+ players
            roles.append(Role.WEREWOLF)
        game_info = game_info_builder.build()
        roles = roles + game_info.get_handled_roles() # Combine game roles with added roles
        roles = ((len(roles) - len(self._lobby.peers)) * [Role.VILLAGER]) + roles  # Fill remaining slots with Villagers
        random.shuffle(roles) # Shuffle roles to randomize assignment
        players = [Player(peer.uuid, roles[i]) for i, peer in enumerate(self._lobby.peers)]
        self._game = Game(players, game_info)
        # TODO: Implement game start logic

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
        for plugin in self._plugins:
            if type(message) in plugin.handled_messages:
                should_stop: bool = await plugin.handle_message(message)
                self.__logger.info(
                    "Message of type %s handled by plugin %s", type(message), plugin
                )
                if should_stop:
                    return
        # self.__logger.warning("No plugin found to handle message of type %s", type(message))
