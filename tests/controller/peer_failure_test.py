import asyncio
from typing import cast
from unittest import mock

import pytest

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer, ReconnectedOutcome
from wiredwolf.controller.connections.connections import (
    AsyncTCPClientConnectionHandler,
    AsyncTCPServerConnectionHandler,
)
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.messages import BaseMessage, PauseGameMessage, ResumeGameMessage
from wiredwolf.controller.server.game_server import GameServerFactory
from wiredwolf.model.game_phases import GamePhase

TEST_ADDRESS: tuple[str, int] = ("127.0.0.1", DEFAULT_SERVER_PORT)


async def _connect_client(peer: Peer) -> AsyncTCPClientConnectionHandler:
    """Connects the peer to the running server."""
    browser = TcpMdnsLobbyBrowser()
    client_handler, _ = await browser.connect_to_lobby_directly(
        my_self=peer,
        address=TEST_ADDRESS,
        lobby_password=None,
    )
    await client_handler.start_receiving()
    return cast(AsyncTCPClientConnectionHandler, client_handler)


def _set_pause_resume_observer(
    handler: AsyncTCPClientConnectionHandler,
    pause_event: asyncio.Event,
    resume_event: asyncio.Event,
) -> None:
    """Capture the pause/resume messages that the server sends over the socket."""

    def on_message(message: BaseMessage) -> None:
        if isinstance(message, PauseGameMessage):
            pause_event.set()
        elif isinstance(message, ResumeGameMessage):
            resume_event.set()

    handler.set_on_message(on_message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reconnect_outcome",
    [ReconnectedOutcome.SUCCESS, ReconnectedOutcome.FAILURE],
)
async def test_peer_error_pauses_and_resumes_game_for_all_clients(
    reconnect_outcome: ReconnectedOutcome,
) -> None:
    """A failed peer should pause everyone, wait for recovery result, and always resume."""
    owner = Peer("Owner")
    lobby = Lobby(owner=owner, name="Peer Failure Lobby")
    server, owner_handler = await GameServerFactory.get_game_server(lobby)
    owner_handler = cast(AsyncTCPClientConnectionHandler, owner_handler)
    tcp_server = cast(AsyncTCPServerConnectionHandler, server._server_conn_handler)
    server._game = mock.Mock()
    server._game.phase = GamePhase.NIGHT
    server._game.get_game_status.return_value = None
    await server.start_listening()

    # The client stays connected and represents the remaining peer in the lobby.
    client = Peer("Client")
    client_handler = await _connect_client(client)

    # This peer is connected to the lobby first and then dropped, which mirrors the real
    # recovery path: the server pauses everyone else when a connected peer disappears.
    failing_client = Peer("Failed Client")
    failing_connection = await _connect_client(failing_client)

    # The UI-facing sender is mocked because the test is only concerned with the protocol messages.
    owner_pause_event = asyncio.Event()
    owner_resume_event = asyncio.Event()
    client_pause_event = asyncio.Event()
    client_resume_event = asyncio.Event()

    # Both real sockets must be actively receiving before the server sends the pause/resume
    # notifications, otherwise the protocol messages would be dropped on the floor.
    owner_handler.set_on_message(lambda message: None)
    await owner_handler.start_receiving()
    _set_pause_resume_observer(owner_handler, owner_pause_event, owner_resume_event)
    _set_pause_resume_observer(client_handler, client_pause_event, client_resume_event)

    try:
        # Simulate peer disconnection: closing the socket makes the server detect the network
        # error and start the pause/resume recovery flow
        failing_connection._writer.close()
        await failing_connection._writer.wait_closed()

        # Wait until the server has created the internal reconnect future for the disconnected peer.
        async with asyncio.timeout(5):
            while failing_client not in tcp_server._recovery_futures:
                await asyncio.sleep(0.05)

        # The server pauses the game for all still-connected peers after the disconnect is detected.
        async with asyncio.timeout(5):
            await asyncio.gather(owner_pause_event.wait(), client_pause_event.wait())

        # Once the pause is observed, resolve the server-created reconnect future to let the
        # recovery flow complete and trigger the final resume message.
        recovery_future = tcp_server._recovery_futures[failing_client]
        recovery_future.set_result(reconnect_outcome)

        async with asyncio.timeout(5):
            await asyncio.gather(owner_resume_event.wait(), client_resume_event.wait())
    finally:
        await server.close()
        await owner_handler.close()
        await client_handler.close()
        await failing_connection.close()