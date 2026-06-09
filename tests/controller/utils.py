from logging import Logger
import logging
from typing import Any

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.connections import (
    ClientConnectionHandler,
    AsyncTCPServerConnectionHandler
)
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser, TcpMdnsLobbyBrowser
from wiredwolf.controller.messages import LobbyUpdatedMessage
from wiredwolf.controller.server import GameServer, GameServerFactory


class TestFactory:

    logger: Logger = logging.getLogger(__name__)

    @staticmethod
    async def create_tcp_server_with_connected_clients(
        num_clients: int, lobby: Lobby
    ) -> tuple[GameServer, list[ClientConnectionHandler]]:
        """
        Creates a GameServer with a specified number of connected clients.
        Number 0 is the lobby owner.

        Args:
            num_clients (int): The number of clients to connect to the server.
            lobby (Lobby): The lobby to be managed by the server.

        Returns:
            tuple[GameServer, list[ClientConnectionHandler]]: The created GameServer and a list of connected clients, of which the first is the owner.
        """
        server, owner_handler = await GameServerFactory.get_game_server(lobby)
        await server.start_listening()
        clients: list[ClientConnectionHandler] = [owner_handler]

        if isinstance(server.connection_handler, AsyncTCPServerConnectionHandler):
            def on_message(msg: Any) -> None:
                if type(msg) is not LobbyUpdatedMessage:
                    TestFactory.logger.error(f"Unexpected message type received in test: {type(msg)}")
                    raise RuntimeError("Unexpected message type")
                else:
                    return None
            owner_handler.set_on_message(on_message)
            await owner_handler.start_receiving()
            browser: LobbyBrowser = TcpMdnsLobbyBrowser()
            for i in range(num_clients-1):
                client_peer = Peer(f"client_{i}")
                client_handler, _ = await browser.connect_to_lobby_directly(
                    client_peer,
                    ("127.0.0.1", DEFAULT_SERVER_PORT),
                    None
                )
                client_handler.set_on_message(on_message)
                await client_handler.start_receiving()
                clients.append(client_handler)
        return server, clients
