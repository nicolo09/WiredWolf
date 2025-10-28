import asyncio
from logging import Logger
import logging
from typing import Any


from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    AsyncTCPServerConnectionHandler
)
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer


class TestFactory:

    logger: Logger = logging.getLogger(__name__)

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

        if isinstance(server.connection_handler, AsyncTCPServerConnectionHandler):
            for i in range(num_clients):
                client_peer = Peer(f"client_{i}")
                browser = TcpMdnsLobbyBrowser()
                client_handler, _ = asyncio.run(browser.connect_to_lobby_directly(
                    client_peer,
                    ("127.0.0.1", DEFAULT_SERVER_PORT),
                    None
                ))

                def on_message(msg: Any) -> None:
                    if type(msg) is not Lobby:
                        TestFactory.logger.error(f"Unexpected message type received in test: {type(msg)}")
                        raise RuntimeError("Unexpected message type")
                    else:
                        return None

                client_handler.set_on_message(on_message)
                client_handler.start_receiving()
                clients.append(client_handler)

        return server, clients
