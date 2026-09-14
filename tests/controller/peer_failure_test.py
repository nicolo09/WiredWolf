import asyncio
from typing import cast
from unittest.mock import Mock

import pytest

from tests.controller.conftest import TEST_PHASE_DURATION_SECONDS, TEST_TIMEOUT
from tests.controller.controller_test import make_client_join_host
from wiredwolf.controller.connections.connections import AsyncTCPClientConnectionHandler
from wiredwolf.controller.controller import GameController
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.game import Game
from wiredwolf.view.custom_events import EventSender


LOBBY_NAME = "Test Lobby"


@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_peer_disconnection_pauses_game(
	controllers: list[tuple[GameController, EventSender]],
):
	host_controller, host_event_sender = controllers[0]
	# Build a real lobby with enough connected peers to start a game.
	await host_controller.create_lobby(name=LOBBY_NAME, password=None)

	for controller, event_sender in controllers[1:]:
		await make_client_join_host(
			host_controller,
			host_event_sender,
			controller,
			event_sender,
		)

	await host_controller.start_game()

	disconnected_controller = controllers[-1][0]
	assert disconnected_controller.connection_handler is not None
	# Close the live client transport to simulate an actual peer failure.
	await disconnected_controller.connection_handler.close()
	error_occurred = cast(Mock, host_event_sender.error_occurred)

	try:
		async with asyncio.timeout(TEST_TIMEOUT):
			# PauseGameMessage is handled by the controller through this view event.
			while not any(
				call.args == (
					"Game Paused",
					"The game has been paused by the server.",
				)
				for call in error_occurred.call_args_list
			):
				await asyncio.sleep(0.1)
	except asyncio.TimeoutError:
		pytest.fail("Host controller did not receive the game pause event in time")

	error_occurred.assert_any_call(
		"Game Paused",
		"The game has been paused by the server.",
	)

@pytest.mark.asyncio
async def test_peer_disconnection_before_game_does_not_pause_or_recover(
	controllers: list[tuple[GameController, EventSender]],
):
	host_controller, host_event_sender = controllers[0]
	client_controller, client_event_sender = controllers[1]
	host_remove_user = cast(Mock, host_event_sender.remove_user_in_lobby)
	host_error_occurred = cast(Mock, host_event_sender.error_occurred)
	client_waiting_for_reconnection = cast(
		Mock, client_event_sender.waiting_for_reconnection
	)

	# Establish a real connection, but leave the game in the lobby phase.
	await host_controller.create_lobby(name=LOBBY_NAME, password=None)
	await make_client_join_host(
		host_controller,
		host_event_sender,
		client_controller,
		client_event_sender,
	)

	assert client_controller.connection_handler is not None
	# Closing the transport simulates the peer disconnecting before the game starts.
	await client_controller.connection_handler.close()

	try:
		async with asyncio.timeout(TEST_TIMEOUT):
			# The lobby update confirms that the server handled the disconnection.
			while not host_remove_user.called:
				await asyncio.sleep(0.1)
	except asyncio.TimeoutError:
		pytest.fail("Host controller did not receive the lobby update in time")

	# The disconnected peer must no longer be part of the host's lobby.
	assert host_controller.lobby is not None
	assert len(host_controller.lobby.peers) == 1
	assert client_controller.my_self not in host_controller.lobby.peers

	# Without an active game, the server must not pause or start recovery.
	host_error_occurred.assert_not_called()
	# The disconnected client must not be prompted to wait for reconnection.
	client_waiting_for_reconnection.assert_not_called()

@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_peer_disconnection_after_game_does_not_pause_or_recover(
	controllers: list[tuple[GameController, EventSender]],
):
	host_controller, host_event_sender = controllers[0]
	disconnected_controller, disconnected_event_sender = controllers[-1]
	host_remove_user = cast(Mock, host_event_sender.remove_user_in_lobby)
	host_error_occurred = cast(Mock, host_event_sender.error_occurred)
	disconnected_waiting_for_reconnection = cast(
		Mock, disconnected_event_sender.waiting_for_reconnection
	)

	# Mock only the game state: the connection and disconnect path remain real.
	finished_game = Mock(spec=Game)
	finished_game.phase = GamePhase.VILLAGERS_VICTORY
	finished_game.players = []
	finished_game_status = Mock()
	finished_game_status.phase = GamePhase.VILLAGERS_VICTORY
	finished_game.get_game_status.return_value = finished_game_status

	# Let the controller establish the real server and connections as usual.
	await host_controller.create_lobby(name=LOBBY_NAME, password=None)
	assert host_controller._server is not None
	host_controller._server._game = finished_game
	for controller, event_sender in controllers[1:]:
		await make_client_join_host(
			host_controller,
			host_event_sender,
		controller,
			event_sender,
		)

	# Keep every controller in the same terminal state as the injected server game.
	for controller, _ in controllers:
		controller._game_status = finished_game_status

	assert host_controller.game_status is not None
	assert host_controller.game_status.phase is GamePhase.VILLAGERS_VICTORY
	assert disconnected_controller.connection_handler is not None
	# A disconnected peer in a finished game must not trigger recovery.
	await disconnected_controller.connection_handler.close()

	try:
		async with asyncio.timeout(TEST_TIMEOUT):
			while not host_remove_user.called:
				await asyncio.sleep(0.1)
	except asyncio.TimeoutError:
		pytest.fail("Host controller did not receive the lobby update in time")

	host_error_occurred.assert_not_called()
	disconnected_waiting_for_reconnection.assert_not_called()

@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_game_does_not_advance_during_recovery(
    controllers: list[tuple[GameController, EventSender]],
):
    host_controller, host_event_sender = controllers[0]
    disconnected_controller = controllers[-1][0]

    # Build a real lobby with enough connected peers to start a game.
    await host_controller.create_lobby(name=LOBBY_NAME, password=None)

    for controller, event_sender in controllers[1:]:
        await make_client_join_host(
            host_controller,
            host_event_sender,
            controller,
            event_sender,
        )

    await host_controller.start_game()

    # Wait for all controllers to have received the role assignment and started the first day.
    for controller, event_sender in controllers:
        user_role = cast(Mock, event_sender.user_role)
        try:
            async with asyncio.timeout(TEST_TIMEOUT):
                while not user_role.called:
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pytest.fail(f"Controller {controller.my_self.name} did not receive role assignment within the timeout period.")

    # Record the current game phase.
    assert host_controller.game_status is not None
    initial_phase = host_controller.game_status.phase
    assert initial_phase is not GamePhase.VILLAGERS_VICTORY
    assert initial_phase is not GamePhase.WEREWOLVES_VICTORY

    # Disconnect a peer to trigger recovery.
    assert disconnected_controller.connection_handler is not None
    await disconnected_controller.connection_handler.close()

    # Wait for the game to be paused.
    error_occurred = cast(Mock, host_event_sender.error_occurred)
    try:
        async with asyncio.timeout(TEST_TIMEOUT):
            while not any(
                call.args == (
                    "Game Paused",
                    "The game has been paused by the server.",
                )
                for call in error_occurred.call_args_list
            ):
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("Host controller did not receive the game pause event in time")

    # Wait longer than the phase duration to confirm the phase does not advance.
    await asyncio.sleep(TEST_PHASE_DURATION_SECONDS*2)

    # The game phase must still be the same as before the disconnection.
    assert host_controller.game_status is not None
    assert host_controller.game_status.phase == initial_phase, (
        f"Game phase advanced from {initial_phase} to {host_controller.game_status.phase} during recovery."
    )

@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_game_resumes_after_reconnection_phase_with_failed_reconnection(
    controllers: list[tuple[GameController, EventSender]],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that after the reconnection phase, even if the peer couldn't reconnect,
    the game server resumes the game."""
    host_controller, host_event_sender = controllers[0]
    disconnected_controller = controllers[-1][0]
    disconnected_peer_uuid = disconnected_controller.my_self.uuid

    # Patch reconnection and heartbeat timeouts so the server doesn't wait the defaults.
    from wiredwolf.controller.connections import connections as conn_module
    from wiredwolf.model.player import Status
    monkeypatch.setattr(conn_module, "MAX_RECONNECT_TIMEOUT", 1)
    monkeypatch.setattr(conn_module, "HEARTBEAT_INTERVAL", 1)

    # Build a real lobby with enough connected peers to start a game.
    await host_controller.create_lobby(name=LOBBY_NAME, password=None)

    for controller, event_sender in controllers[1:]:
        await make_client_join_host(
            host_controller,
            host_event_sender,
            controller,
            event_sender,
        )

    await host_controller.start_game()

    # Wait for all controllers to have received the role assignment and started the first day.
    for controller, event_sender in controllers:
        user_role = cast(Mock, event_sender.user_role)
        try:
            async with asyncio.timeout(TEST_TIMEOUT):
                while not user_role.called:
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pytest.fail(
                f"Controller {controller.my_self.name} did not receive role assignment within the timeout period."
            )

    # Record the current game phase.
    assert host_controller.game_status is not None
    initial_phase = host_controller.game_status.phase
    assert initial_phase is not GamePhase.VILLAGERS_VICTORY
    assert initial_phase is not GamePhase.WEREWOLVES_VICTORY

    # Disconnect a peer to trigger the server-side _on_peer_error path.
    # The disconnected peer's _on_disconnect is not called
    assert disconnected_controller.connection_handler is not None
    await disconnected_controller.connection_handler.close()

    # Wait for the game to be paused.
    error_occurred = cast(Mock, host_event_sender.error_occurred)
    try:
        async with asyncio.timeout(TEST_TIMEOUT):
            while not any(
                call.args == (
                    "Game Paused",
                    "The game has been paused by the server.",
                )
                for call in error_occurred.call_args_list
            ):
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("Host controller did not receive the game pause event in time")

    # Wait for the game to resume: the phase must change from the initial phase.
    try:
        async with asyncio.timeout(15):
            while host_controller.game_status is None or host_controller.game_status.phase == initial_phase:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "Host controller did not receive a phase change within the timeout period."
        )

    # The game phase must have changed from the initial phase, confirming the game resumed.
    assert host_controller.game_status is not None
    assert host_controller.game_status.phase != initial_phase, (
        f"Game phase did not change from {initial_phase} after recovery."
    )

    # Verify that all connected controllers (except the disconnected one) have an updated game status
    # (not just the host), and that the disconnected peer is marked as dead.
    for controller, _ in controllers:
        
        if controller is disconnected_controller:
            continue  # Skip the disconnected controller
        
        controller_status = controller.game_status
        assert controller_status is not None, (
            f"Controller {controller.my_self.name} does not have an updated game status."
        )
        assert controller_status.phase != initial_phase, (
            f"Controller {controller.my_self.name} game phase did not change from {initial_phase}."
        )
        # There must be at least one dead player (the disconnected peer).
        dead_player_ids = [
            p.id for p in controller_status.players if p.status == Status.DEAD
        ]
        assert len(dead_player_ids) >= 1, (
            f"Controller {controller.my_self.name} has no dead players."
        )
        # The disconnected peer must be among the dead players.
        assert disconnected_peer_uuid in dead_player_ids, (
            f"Disconnected peer {disconnected_peer_uuid} is not marked as dead "
            f"in controller {controller.my_self.name} game status."
        )

@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_game_resumes_after_reconnection_phase_with_successful_reconnection(
    controllers: list[tuple[GameController, EventSender]],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that after the reconnection phase, if the peer successfully reconnects,
    the game server resumes the game and the peer remains alive."""
    host_controller, host_event_sender = controllers[0]
    reconnected_controller = controllers[-1][0]
    reconnected_peer_uuid = reconnected_controller.my_self.uuid

    # Patch reconnection and heartbeat timeouts so the server doesn't wait the defaults.
    # Patch direct reconnection retries to 1 so we don't waste time on retries on localhost.
    from wiredwolf.controller.connections import connections as conn_module
    from wiredwolf.model.player import Status
    monkeypatch.setattr(conn_module, "HEARTBEAT_INTERVAL", 1)

    # Build a real lobby with enough connected peers to start a game.
    await host_controller.create_lobby(name=LOBBY_NAME, password=None)

    for controller, event_sender in controllers[1:]:
        await make_client_join_host(
            host_controller,
            host_event_sender,
            controller,
            event_sender,
        )
        
    await host_controller.start_game()

    # Wait for all controllers to have received the role assignment and started the first day.
    for controller, event_sender in controllers:
        user_role = cast(Mock, event_sender.user_role)
        try:
            async with asyncio.timeout(TEST_TIMEOUT):
                while not user_role.called:
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pytest.fail(
                f"Controller {controller.my_self.name} did not receive role assignment within the timeout period."
            )

    # Record the current game phase.
    assert host_controller.game_status is not None
    initial_phase = host_controller.game_status.phase
    assert initial_phase is not GamePhase.VILLAGERS_VICTORY
    assert initial_phase is not GamePhase.WEREWOLVES_VICTORY

    # Override _handle_receive_loop_closed on the disconnected peer's connection handler
    # so that it always triggers the _on_disconnect callback.
    # By default the method enters an if block that does not call _on_disconnect,
    # so we patch it here for this test only.
    disconnected_handler = cast(AsyncTCPClientConnectionHandler, reconnected_controller.connection_handler)
    
    if disconnected_handler is None:
        pytest.fail("Reconnected controller does not have a connection handler.")

    def patched_handle_receive_loop_closed(task: asyncio.Task[None]) -> None:
        if disconnected_handler._on_disconnect is not None:
            asyncio.create_task(disconnected_handler._on_disconnect())

    if disconnected_handler._receiving_task is None:
        pytest.fail("Reconnected controller does not have a receiving task.")

    # Replacing the original callback with the patched one to ensure _on_disconnect is called.
    disconnected_handler._receiving_task.remove_done_callback(disconnected_handler._handle_receive_loop_closed)  
    disconnected_handler._receiving_task.add_done_callback(patched_handle_receive_loop_closed)

    # Disconnect a peer to trigger the server-side _on_peer_error path.
    # The client's _on_disconnect will automatically attempt to reconnect.
    assert reconnected_controller.connection_handler is not None
    await reconnected_controller.connection_handler.close()

    # Wait for the game to be paused.
    error_occurred = cast(Mock, host_event_sender.error_occurred)
    try:
        async with asyncio.timeout(TEST_TIMEOUT):
            while not any(
                call.args == (
                    "Game Paused",
                    "The game has been paused by the server.",
                )
                for call in error_occurred.call_args_list
            ):
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("Host controller did not receive the game pause event in time")

    # Wait for the game to resume: the phase must change from the initial phase.
    try:
        async with asyncio.timeout(15):
            while host_controller.game_status is None or host_controller.game_status.phase == initial_phase:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "Host controller did not receive a phase change within the timeout period."
        )

    # The game phase must have changed from the initial phase, confirming the game resumed.
    assert host_controller.game_status is not None
    assert host_controller.game_status.phase != initial_phase, (
        f"Game phase did not change from {initial_phase} after recovery."
    )

    # Verify that all connected controllers have an updated game status
    # (not just the host), and that the reconnected peer is NOT marked as dead.
    for controller, _ in controllers:
        controller_status = controller.game_status
        assert controller_status is not None, (
            f"Controller {controller.my_self.name} does not have an updated game status."
        )
        assert controller_status.phase != initial_phase, (
            f"Controller {controller.my_self.name} game phase did not change from {initial_phase}."
        )
        assert controller_status == host_controller.game_status, (
            f"Controller {controller.my_self.name} game status does not match host controller's game status."
        )
        # The reconnected peer must NOT be among the dead players.
        dead_player_ids = [
            p.id for p in controller_status.players if p.status == Status.DEAD
        ]
        assert reconnected_peer_uuid not in dead_player_ids, (
            f"Reconnected peer {reconnected_peer_uuid} is marked as dead "
            f"in controller {controller.my_self.name} game status."
        )
        # The reconnected peer must be among the alive players.
        alive_player_ids = [
            p.id for p in controller_status.players if p.status == Status.ALIVE
        ]
        assert reconnected_peer_uuid in alive_player_ids, (
            f"Reconnected peer {reconnected_peer_uuid} is not alive "
            f"in controller {controller.my_self.name} game status."
        )
        