from dataclasses import dataclass
import logging
import socket
import uuid
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import MessageHandler, ServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby


class GameServer:
    __logger = logging.getLogger(__name__)
    _server: ServerConnectionHandler
    _lobby: Lobby
    _players: dict[Peer, socket.socket]

    def __init__(self, lobby: Lobby):  # TODO: Add owner peer and socket
        self._lobby = lobby
        self._server = ServerConnectionHandler(
            lambda peer, socket: self._on_new_peer(peer, socket))
        self._players = {}

    @property
    def _message_handler(self) -> MessageHandler:
        """Returns the message handler for the lobby."""
        return self._lobby.message_handler

    @property
    def connection_socket(self) -> socket.socket:
        """
        Returns the socket used by this server to receive new connections in the lobby.
        """
        return self._server.get_receiver_socket()

    def _on_new_peer(self, peer: Peer, socket: socket.socket):
        self.__logger.info(f"New peer attempting connection: {peer}")
        if self._lobby.is_password_protected():
            socket.settimeout(10)  # TODO: Magic number
            # If the lobby is password-protected, ask for the password
            req = PasswordRequest()
            self._message_handler.send_obj(socket, req)
            resp: PasswordRequest = self._message_handler.receive_obj(socket)
            if resp.id != req.id:
                self._message_handler.send_obj(
                    socket, ValueError("Invalid password request."))
                return
            if resp.password and self._lobby.check_password(resp.password):
                # TODO add peer to lobby and notify everyone
                self._message_handler.send_obj(socket, self._lobby)
            else:
                self._message_handler.send_obj(
                    socket, ValueError("Incorrect password."))
        else:
            # If no password is set, add the peer directly
            # TODO add peer to lobby and notify everyone
            self._message_handler.send_obj(socket, self._lobby)

    def start_game(self):
        # TODO: Implement game start logic
        pass

    def end_game(self):
        # TODO: Implement game end logic
        pass

    def stop_new_connections(self):
        self._server.stop_new_connections()


@dataclass
class PasswordRequest:
    """Represents a password request message."""
    password: str | None = None
    id: str = str(uuid.uuid4())
