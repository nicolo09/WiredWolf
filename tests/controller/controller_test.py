import asyncio
from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from tests.controller.conftest import TIMEOUT
from wiredwolf.controller.commons import FIRST_DAY_PHASE_DURATION_SECONDS, PHASE_DURATION_SECONDS
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import LobbyInfo, TcpMdnsLobbyBrowser
from wiredwolf.view.custom_events import EventSender

LOBBY_NAME = "Test Lobby"
TEST_USER_BASE = "TestUser"

"""
This test suite verifies the functionality of the entire game except for the view which is modeled only by the EventSender mock. 

Every test in this suite advances a step further in the game flow, starting from controller initialization, to lobby discovery, 
joining, leaving, starting the game and finally the game flow itself. Every test also uses part of the previous test's flow as
a prerequisite, SO THE TESTS ARE NOT INDEPENDENT, even though they can be run in any order. 

The tests in this suite uses mock.Mock which cannot easily be type checked, the mocked methods name cannot be verified, double 
check that in case of errors.
"""


@pytest_asyncio.fixture
async def controllers(
    request,
) -> AsyncGenerator[list[tuple[GameController, EventSender]], None]:
    """
    Return a list of (GameController, EventSender) tuples.

    To parametrize the number of controllers, decorate the test with:
    - `@pytest.mark.parametrize("controllers", [n], indirect=True)` where `n` is the number of controllers to create.

    Defaults to 2 controllers when no parameter is provided.
    """
    # Prefer indirect parametrization value when present
    num = getattr(request, "param", None)
    if num is None:
        num = 2

    controllers = []
    for i in range(num):
        event_sender = mock.Mock()
        controller = GameController(
            browser=TcpMdnsLobbyBrowser(), event_sender=event_sender
        )
        controller.set_username(f"{TEST_USER_BASE}{i}")
        controllers.append((controller, event_sender))

    yield controllers

    for controller, _ in controllers:
        try:
            await controller.leave()  # TODO: Change this to a more robust method that ensures the controller is properly cleaned up after each test
        except Exception:
            pass


@pytest.mark.asyncio
async def test_controller_initialization(
    controllers: list[tuple[GameController, EventSender]],
):
    host_game_controller, event_sender = controllers[0]
    assert isinstance(host_game_controller, GameController)
    assert host_game_controller.lobby is None


@pytest.mark.asyncio
async def test_controller_publish_discover_lobby(
    controllers: list[tuple[GameController, EventSender]],
):
    host_game_controller, host_event_sender = controllers[0]
    client_game_controller, client_event_sender = controllers[1]
    client_game_controller.start_listening_for_lobbies()

    if isinstance(client_event_sender, mock.Mock):
        client_event_sender.new_discovered_lobby.assert_not_called()
    await host_game_controller.create_lobby(name=LOBBY_NAME, password=None)

    if isinstance(client_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(TIMEOUT):
                while not client_event_sender.new_discovered_lobby.called:
                    await asyncio.sleep(0.1)
                client_event_sender.new_discovered_lobby.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "Client controller did not discover the lobby within the timeout period."
            )


@pytest.mark.asyncio
async def test_controller_join_lobby(
    controllers: list[tuple[GameController, EventSender]],
):
    host_game_controller, host_event_sender = controllers[0]
    client_game_controller, client_event_sender = controllers[1]
    await host_game_controller.create_lobby(name=LOBBY_NAME, password=None)
    await make_client_join_host(
        host_game_controller,
        host_event_sender,
        client_game_controller,
        client_event_sender,
    )
    assert client_game_controller.lobby is not None
    assert len(client_game_controller.lobby.peers) == 2


async def make_client_join_host(
    host_game_controller: GameController,
    host_event_sender: EventSender,
    client_game_controller: GameController,
    client_event_sender: EventSender,
):
    assert host_game_controller.lobby is not None
    client_game_controller.start_listening_for_lobbies()

    lobby_info: LobbyInfo|None = None
    if isinstance(client_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(TIMEOUT):
                # Wait until the second controller discovers the lobby and captures the lobby info from the call arguments
                while (
                    not client_event_sender.new_discovered_lobby.called
                    or lobby_info is None
                ):
                    if client_event_sender.new_discovered_lobby.call_args:
                        calls = client_event_sender.new_discovered_lobby.call_args_list
                        calls = [
                            call
                            for call in calls
                            if call.args
                            and call.args[0].uuid
                            == host_game_controller.lobby.lobby_info().uuid
                        ]
                        if calls:
                            lobby_info = calls[0].args[0]
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pytest.fail(
                "Second controller did not discover the lobby within the timeout period."
            )

    assert lobby_info is not None, (
        "Lobby info was not received by the second controller."
    )
    assert lobby_info is not None, "Lobby info was not received by the second controller."
    assert lobby_info.uuid == host_game_controller.lobby.lobby_info().uuid, (
        "The discovered lobby info does not match the created lobby info."
    )

    await client_game_controller.join_lobby(lobby_name=lobby_info, lobby_password=None)

    assert client_game_controller.lobby is not None

    try:
        async with asyncio.timeout(TIMEOUT):
            # Wait for the first controller to update its lobby state
            while len(host_game_controller.lobby.peers) < 2:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "First controller did not update its lobby state after the second controller joined within the timeout period."
        )
    try:
        async with asyncio.timeout(TIMEOUT):
            while host_game_controller.lobby != client_game_controller.lobby:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "Lobbies do not match between controllers."
        )


@pytest.mark.asyncio
async def test_controller_leave_lobby(
    controllers: list[tuple[GameController, EventSender]],
):
    await test_controller_join_lobby(controllers)
    host_game_controller, host_event_sender = controllers[0]
    client_game_controller, client_event_sender = controllers[1]
    assert isinstance(host_event_sender, mock.Mock)
    assert isinstance(client_event_sender, mock.Mock)
    host_event_sender.remove_user_in_lobby.assert_not_called()
    await client_game_controller.leave()
    assert client_game_controller.lobby is None
    assert host_game_controller.lobby is not None
    try:
        # Wait for the first controller to update its lobby state after the second controller leaves
        async with asyncio.timeout(TIMEOUT):
            while len(host_game_controller.lobby.peers) != 1:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "First controller did not update its lobby state after the second controller left within the timeout period."
        )
    assert len(host_game_controller.lobby.peers) == 1
    assert any(peer == host_game_controller.my_self for peer in host_game_controller.lobby.peers)
    assert not any(peer == client_game_controller.my_self for peer in host_game_controller.lobby.peers)
    host_event_sender.remove_user_in_lobby.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_start_game(
    controllers: list[tuple[GameController, EventSender]],
):
    assert len(controllers) == 8, "Expected 8 controllers for this test"
    host_game_controller, host_event_sender = controllers[0]
    await host_game_controller.create_lobby(name=LOBBY_NAME, password=None)
    client_game_controllers, client_event_senders = zip(*controllers[1:])
    for controller, event_sender in controllers[1:]:
        await make_client_join_host(
            host_game_controller, host_event_sender, controller, event_sender
        )
    #Start the game and verify that all controllers receive the game start event
    await host_game_controller.start_game()
    if isinstance(host_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(TIMEOUT):
                while not host_event_sender.game_started_by_master.called:
                    await asyncio.sleep(0.1)
            host_event_sender.game_started_by_master.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "Host controller did not receive game start message within the timeout period."
            )
    else:
        pytest.fail("Host event sender is not a mock, cannot verify game start event.")
    for client_event_sender in client_event_senders:
        try:
            async with asyncio.timeout(TIMEOUT):
                while not client_event_sender.game_started_by_master.called:
                    await asyncio.sleep(0.1)
            client_event_sender.game_started_by_master.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A client controller did not receive game start message within the timeout period."
            )
    #Check that everyone has their role assigned and the first day started
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify role assignment event.")
            async with asyncio.timeout(TIMEOUT):
                while not event_sender.user_role.called and event_sender.start_first_day.called:
                    await asyncio.sleep(0.1)
            event_sender.user_role.assert_called_once()
            event_sender.start_first_day.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive role assignment message within the timeout period."
            )

@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_game_flow(
    controllers: list[tuple[GameController, EventSender]],
):
    await test_start_game(controllers)
    #Wait for the first day phase to end
    await asyncio.sleep(FIRST_DAY_PHASE_DURATION_SECONDS) #TODO: Mock this to avoid waiting for the actual duration
    #Verify that the phase advancement message is received by all controllers and that the first night starts 
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify phase advancement event.")
            async with asyncio.timeout(TIMEOUT):
                while not event_sender.start_night.called:
                    await asyncio.sleep(0.1)
            event_sender.start_night.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive first night phase advancement message within the timeout period."
            )
    await asyncio.sleep(PHASE_DURATION_SECONDS) #TODO: Mock this to avoid waiting for the actual duration
    #Verify that the second day starts
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify phase advancement event.")
            async with asyncio.timeout(TIMEOUT):
                while not event_sender.end_night.called:
                    await asyncio.sleep(0.1)
            event_sender.end_night.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive second day phase advancement message within the timeout period."
            )
