import logging
from wiredwolf.controller.commons import PasswordRequest, Peer
from wiredwolf.controller.connections import (
    ServerConnectionHandler,
    TCPClientConnectionHandler,
    TCPServerConnectionHandler,
)
from wiredwolf.controller.messages import BaseMessage
from wiredwolf.controller.lobbies import Lobby
import abc


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

    @abc.abstractmethod
    def handle_message(self, message: BaseMessage) -> bool:
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
        # To be implemented by subclasses


class GameServer:
    """Represents a wiredwolf server that manages a game lobby and player connections."""

    __logger = logging.getLogger(__name__)

    def __init__(self, lobby: Lobby):  # TODO: Add owner peer and socket
        self._lobby: Lobby = lobby
        self._server_conn_handler: TCPServerConnectionHandler = (
            TCPServerConnectionHandler(self._on_new_peer, self.process_incoming_message)
        )
        self._players: dict[Peer, TCPClientConnectionHandler] = {}
        self._plugins: list[ServerPlugin] = []

    @property
    def connection_handler(self) -> ServerConnectionHandler:
        """
        Returns the connection handler for this server.
        """
        return self._server_conn_handler

    def _on_new_peer(self, peer: Peer):
        self.__logger.info("New peer attempting connection: %s", peer)
        try:
            if self._lobby.is_password_protected():
                # If the lobby is password-protected, ask for the password
                req = PasswordRequest()
                self._server_conn_handler.send_obj(peer, req)
                resp: PasswordRequest = self._server_conn_handler.receive_obj(peer)
                if resp.id != req.id:
                    self._server_conn_handler.send_obj(
                        peer, ValueError("Invalid password request.")
                    )
                    return
                if resp.password and self._lobby.check_password(resp.password):
                    self._add_peer_and_notify_updates(peer)
                    self._server_conn_handler.send_obj(peer, self._lobby)
                else:
                    self._server_conn_handler.send_obj(
                        peer, ValueError("Incorrect password.")
                    )
            else:
                # If no password is set, add the peer directly
                self._add_peer_and_notify_updates(peer)
                self._server_conn_handler.send_obj(peer, self._lobby)
        except Exception as e:
            self.__logger.error("Error handling new peer %s: %s", peer, e)

    def _add_peer_and_notify_updates(self, peer: Peer):
        # Update lobby
        self._lobby.add_peer(peer)
        # Notify other peers of the updated lobby sending the updated lobby object
        for p in self._lobby.peers:
            if p != peer:
                self._server_conn_handler.send_obj(p, self._lobby)
        self.__logger.info(
            "Peer %s joined the lobby. Current peers: %s", peer, self._lobby.peers
        )

    def send_to_all(self, message: BaseMessage):
        """Sends a message to all connected peers in the lobby."""
        for peer in self._lobby.peers:
            try:
                self._server_conn_handler.send_obj(peer, message)
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
        # TODO: Implement game start logic
        self.__logger.info("Starting game in lobby: %s", self._lobby)
        raise NotImplementedError("Game start logic not implemented yet.")

    def end_game(self) -> None:
        # TODO: Implement game end logic
        self.__logger.info("Ending game in lobby: %s", self._lobby)
        raise NotImplementedError("Game end logic not implemented yet.")

    def stop_new_connections(self):
        """Stop accepting new peer connections"""
        self._server_conn_handler.stop_new_connections()

    def close(self):
        """Closes the server and all associated connections."""
        self.stop_new_connections()
        self._server_conn_handler.close()

    def process_incoming_message(self, message: BaseMessage):
        """Handles a message coming from a peer.

        Args:
            message (BaseMessage): The message to handle.
        """
        for plugin in self._plugins:
            if type(message) in plugin.handled_messages:
                should_stop: bool = plugin.handle_message(message)
                self.__logger.info(
                    "Message of type %s handled by plugin %s", type(message), plugin
                )
                if should_stop:
                    return
        # self.__logger.warning("No plugin found to handle message of type %s", type(message))
