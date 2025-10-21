import socket

from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    TCPClientConnectionHandler,
    TCPServerConnectionHandler,
)
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.server import GameServer


class TestFactory:
    @staticmethod
    def create_tcp_server_with_connected_clients(
        num_clients: int, lobby: Lobby
    ) -> tuple[GameServer, list[ClientConnectionHandler]]:
        """
        Creates a GameServer with a specified number of connected clients.

        Args:
            num_clients (int): The number of clients to connect to the server.
            lobby (Lobby): The lobby to be managed by the server.

        Returns:
            GameServer: The created game server.
            list[ClientConnectionHandler]: List of connected client handlers.
        """
        server: GameServer = GameServer(lobby)
        clients: list[ClientConnectionHandler] = []

        if isinstance(server.connection_handler, TCPServerConnectionHandler):
            for i in range(num_clients):
                client_peer = Peer(f"client_{i}")
                client_handler = TCPClientConnectionHandler(
                    client_peer,
                    socket.create_connection(
                        server.connection_handler.get_receiver_socket().getsockname()
                    ),
                )
                client_handler.send_obj(client_peer)
                clients.append(client_handler)

        return server, clients
