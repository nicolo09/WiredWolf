import logging
from wiredwolf.controller.commons import PasswordRequest, Peer
from wiredwolf.controller.connections import ServerConnectionHandler, TCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby


class GameServer:
    __logger = logging.getLogger(__name__)
    _server_conn_handler: ServerConnectionHandler
    _lobby: Lobby

    def __init__(self, lobby: Lobby):  # TODO: Add owner peer and socket
        self._lobby = lobby
        self._server_conn_handler = TCPServerConnectionHandler(
            lambda peer: self._on_new_peer(peer))
        self._players = {}

    @property
    def connection_handler(self) -> ServerConnectionHandler:
        """
        Returns the connection handler for this server.
        """
        return self._server_conn_handler

    def _on_new_peer(self, peer: Peer):
        self.__logger.info(f"New peer attempting connection: {peer}")
        try:
            if self._lobby.is_password_protected():
                # If the lobby is password-protected, ask for the password
                req = PasswordRequest()
                self._server_conn_handler.send_obj(peer, req)
                resp: PasswordRequest = self._server_conn_handler.receive_obj(
                    peer)
                if resp.id != req.id:
                    self._server_conn_handler.send_obj(
                        peer, ValueError("Invalid password request."))
                    return
                if resp.password and self._lobby.check_password(resp.password):
                    self._add_peer_and_notify_updates(peer)
                    self._server_conn_handler.send_obj(peer, self._lobby)
                else:
                    self._server_conn_handler.send_obj(
                        peer, ValueError("Incorrect password."))
            else:
                # If no password is set, add the peer directly
                self._add_peer_and_notify_updates(peer)
                self._server_conn_handler.send_obj(peer, self._lobby)
        except Exception as e:
            self.__logger.error(f"Error handling new peer {peer}: {e}")

    def _add_peer_and_notify_updates(self, peer: Peer):
        # Update lobby
        self._lobby.add_peer(peer)
        # Notify other peers of the updated lobby sending the updated lobby object
        for p in self._lobby.peers:
            if p != peer:
                self._server_conn_handler.send_obj(p, self._lobby)
        self.__logger.info(
            f"Peer {peer} joined the lobby. Current peers: {self._lobby.peers}")

    def start_game(self):
        # TODO: Implement game start logic
        pass

    def end_game(self):
        # TODO: Implement game end logic
        pass

    def stop_new_connections(self):
        self._server_conn_handler.stop_new_connections()
