import asyncio
import logging
from collections.abc import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.connections.connections import (
    ClientConnectionHandler,
    ConnectionSuite,
    TCPConnectionSuite,
)
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import (
    Lobby,
    LobbyBrowser,
    TcpMdnsLobbyBrowser,
)
from wiredwolf.controller.server.game_server import GameServer, GameServerFactory
from wiredwolf.controller.server.server_plugins import ChatPlugin, GameLifecyclePlugin
from wiredwolf.view.custom_events import EventSender

logger = logging.getLogger(__name__)

# Numero di client totali (1 owner + 7 clients)
NUM_CLIENTS = 8
TEST_BIND_ADDRESS = ("127.0.0.1", DEFAULT_SERVER_PORT)


class MockTCPConnectionSuite(TCPConnectionSuite):
    """
    Mock implementation of TCPConnectionSuite for testing purposes.
    """

    def __init__(self, mock_ipv4_address: str = "127.0.0.1"):
        self._mock_ipv4_address = mock_ipv4_address
        super().__init__()

    def get_local_ipv4_addresses(self) -> list[list[str]]:
        """
        Returns a list of local IPv4 addresses for testing purposes.
        """
        return [[self._mock_ipv4_address]]

    def get_default_bind_address(self) -> tuple[str, int]:
        """
        Returns a default bind address for testing purposes.
        """
        return (self._mock_ipv4_address, DEFAULT_SERVER_PORT)


@pytest_asyncio.fixture
async def lobby_with_clients() -> AsyncGenerator[
    tuple[Lobby, GameServer, list[ClientConnectionHandler]]
]:
    """
    Creates a lobby with 8 clients connected to a game server.

    Returns: tuple containing the lobby, the game server, and a list of client connection handlers (n.0 is lobby owner).
    """
    myself = Peer("owner")
    lobby = Lobby(myself, "RecoveryTestLobby")

    # Create the game server and start listening for connections
    connection_suite = MockTCPConnectionSuite()
    server, owner_handler = await GameServerFactory.get_game_server(
        lobby, connection_suite
    )
    server.add_plugin(ChatPlugin())
    server.add_plugin(GameLifecyclePlugin())
    await server.start_listening()

    clients = [owner_handler]

    # Connetti i client rimanenti
    browser: LobbyBrowser = connection_suite.lobby_browser()

    await owner_handler.start_receiving()
    if isinstance(browser, TcpMdnsLobbyBrowser):
        for i in range(1, NUM_CLIENTS):
            client_peer = Peer(f"client_{i}")
            client_handler, _lobby = await browser.connect_to_lobby_directly(
                client_peer,
                connection_suite.get_default_bind_address(),
                None,
            )

            await client_handler.start_receiving()
            clients.append(client_handler)

    logger.info("Created lobby with %d clients connected", len(clients))

    yield lobby, server, clients

    # Cleanup
    for client_handler in clients:
        try:
            await client_handler.close()
        except Exception:
            pass
    try:
        await server.close()
    except RuntimeError:
        pass  # Server already stopped


@pytest_asyncio.fixture
async def controllers() -> AsyncGenerator[tuple[GameController, list[GameController]]]:
    """
    Creates a server controller and a list of client controllers for testing purposes.
    """
    server_conn_suite: ConnectionSuite = MockTCPConnectionSuite()
    server_event_sender: EventSender = mock.Mock(spec=EventSender)

    server_controller = GameController(server_conn_suite, server_event_sender)
    server_controller.set_username("ServerController")
    clients: list[GameController] = []

    await server_controller.create_lobby("RecoveryTestLobby")

    for i in range(NUM_CLIENTS):
        connection_suite: ConnectionSuite = MockTCPConnectionSuite(
            "127.0.0." + str(i + 2)
        )  # Different local IP for each client
        event_sender: EventSender = mock.Mock(spec=EventSender)
        client = GameController(connection_suite, event_sender)
        client.set_username(f"Client_{'127.0.0.' + str(i + 2)}")
        client.start_listening_for_lobbies()
        async with asyncio.timeout(5):
            while not event_sender.new_discovered_lobby.called:
                await asyncio.sleep(0.1)
        event_sender.new_discovered_lobby.assert_called()  # Ensure the event sender was called during lobby discovery
        lobby_info = event_sender.new_discovered_lobby.call_args[0][
            0
        ]  # Get the first argument of the first call
        await asyncio.sleep(
            1
        )  # Small delay to ensure the lobby is fully discovered before joining
        await client.join_lobby(lobby_info, None)
        clients.append(client)

    yield server_controller, clients

    # TODO: Cleanup controllers if necessary
    for controller in clients:
        try:
            await controller.leave()  # TODO: Change this to a more robust method that ensures the controller is properly cleaned up after each test
        except Exception:
            logger.warning(
                "Failed to clean up client controller %s", controller.my_self.name
            )
    await server_controller.leave()


@pytest.mark.asyncio
async def test_multiple_clients_detect_disconnection(
    lobby_with_clients: tuple[Lobby, GameServer, list[ClientConnectionHandler]],
):
    """
    Test that verifies that all clients detect the disconnection when the server crashes.
    """
    lobby, server, clients = lobby_with_clients

    # Counter for clients that correctly detected the disconnection
    disconnected_count = 0
    disconnect_events: list[asyncio.Event] = []

    for client_handler in clients:
        event = asyncio.Event()

        def make_on_disconnect(event: asyncio.Event):
            async def on_disconnect():
                nonlocal disconnected_count
                disconnected_count += 1
                event.set()

            return on_disconnect

        client_handler.set_on_disconnect(make_on_disconnect(event))
        disconnect_events.append(event)

    # Close the server to simulate a crash
    conn_handler = server.connection_handler
    await conn_handler.close()

    # Wait for all clients to detect the disconnection
    tasks = [asyncio.create_task(event.wait()) for event in disconnect_events]
    _, not_done = await asyncio.wait(tasks, timeout=5)

    if not_done:
        logger.warning("Some clients failed to detect disconnection.")
        pytest.fail(
            f"Not all clients detected disconnection. Remaining: {len(not_done)}"
        )

    logger.info(
        "Detected disconnections: %d/%d clients", disconnected_count, NUM_CLIENTS
    )


@pytest.mark.asyncio
async def test_server_election(
    controllers: tuple[GameController, list[GameController]],
    caplog: pytest.LogCaptureFixture,
):
    """
    Test that verifies that when the server crashes, a new server is elected among the clients.
    """

    caplog.set_level(logging.DEBUG)

    server = controllers[0]
    clients = controllers[1]

    await server.start_game()

    # Check that the game has started
    async with asyncio.timeout(5):
        while not server.game_status:
            await asyncio.sleep(1)
    assert server.game_status
    # TODO Crash the server and check that a new server is elected among the clients

    await server.leave()

