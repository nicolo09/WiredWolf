import logging
import socket
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import MessageHandler, ServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby


class GameServer:
    __logger = logging.getLogger(__name__)
    _server: ServerConnectionHandler | None = None
    _lobby: Lobby

    def __init__(self, lobby: Lobby):  # TODO: Add owner peer and socket
        self._lobby = lobby
        self._server = ServerConnectionHandler(
            lambda peer, socket: self._on_new_peer(peer, socket))

    @property
    def _message_handler(self) -> MessageHandler:
        """Returns the message handler for the lobby."""
        return self._lobby.message_handler

    @property
    def connection_socket(self) -> socket.socket:
        """Returns the socket used by this lobby's server to receive new connections in the lobby.

        Raises:
            RuntimeError: If this peer is not the lobby's server.
        """
        if not self._server:
            raise RuntimeError("This peer is not the lobby's server.")
        return self._server.get_receiver_socket()

    def _on_new_peer(self, peer: Peer, socket: socket.socket):
        self.__logger.info(f"New peer attempting connection: {peer}")
        if self._lobby.is_password_protected():
            socket.settimeout(5)  # TODO: Magic number
            # If the lobby is password-protected, ask for the password
            self._message_handler.send(socket, "password?".encode())
            password = self._message_handler.receive(socket).decode()
            if self._lobby.check_password(password):
                # TODO add peer to lobby and notify everyone
                pass
            else:
                self._message_handler.send_obj(
                    socket, ValueError("Incorrect password."))
        else:
            # If no password is set, add the peer directly
            # TODO add peer to lobby and notify everyone
            pass

    def start_game(self):
        # TODO: Implement game start logic
        pass

    def end_game(self):
        # TODO: Implement game end logic
        pass
