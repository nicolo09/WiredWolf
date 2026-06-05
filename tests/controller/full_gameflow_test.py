

import asyncio
import logging
from unittest import mock

import pytest

from tests.controller.conftest import TEST_TIMEOUT
from tests.controller.controller_test import test_start_game
from wiredwolf.controller.commons import FIRST_DAY_PHASE_DURATION_SECONDS, PHASE_DURATION_SECONDS
from wiredwolf.controller.controller import GameController
from wiredwolf.model.player import BasicRole
from wiredwolf.view.custom_events import EventSender


@pytest.mark.asyncio
@pytest.mark.parametrize("controllers", [8], indirect=True)
async def test_game_flow(
    caplog,
    controllers: list[tuple[GameController, EventSender]],
):
    """This is the mega test that tries to verify the entire game flow
    """
    caplog.set_level(logging.DEBUG)
    await test_start_game(controllers)
    #Wait for the first day phase to end
    await asyncio.sleep(FIRST_DAY_PHASE_DURATION_SECONDS) #TODO: Mock this to avoid waiting for the actual duration
    #Verify that the phase advancement message is received by all controllers and that the first night starts 
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify phase advancement event.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.start_night.called:
                    await asyncio.sleep(0.1)
            event_sender.start_night.assert_called_once()
            event_sender.reset_mock() 
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
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.end_night.called:
                    await asyncio.sleep(0.1)
            event_sender.end_night.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive second day phase advancement message within the timeout period."
            )
    # Get right players for each role
    villagers = [controller for controller, _ in controllers if controller.my_self_as_player().role == BasicRole.VILLAGER] # pyright: ignore[reportOptionalMemberAccess]
    werewolves = [controller for controller, _ in controllers if controller.my_self_as_player().role == BasicRole.WEREWOLF] # pyright: ignore[reportOptionalMemberAccess]
    clairvoyant = [controller for controller, _ in controllers if controller.my_self_as_player().role == BasicRole.CLAIRVOYANT].pop() # pyright: ignore[reportOptionalMemberAccess]

    # Verify that the voting phase starts
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify phase advancement event.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.start_nomination_for_execution.called:
                    await asyncio.sleep(0.1)
            event_sender.start_nomination_for_execution.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive voting phase advancement message within the timeout period."
            )
    
    # Nominate a player for execution
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify nomination event.")
            async with asyncio.timeout(TEST_TIMEOUT):
                if controller.my_self is not villagers[0].my_self: 
                    await controller.choose_player(villagers[0].my_self)
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller couldn't vote within the timeout period."
            )

    # Verify that all controllers receive the correct ballot message with the nominated player
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify ballot message.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.user_to_nominated_for_ballot.called:
                    await asyncio.sleep(0.1)
            event_sender.user_to_nominated_for_ballot.assert_called_once()
            nominated_player = event_sender.user_to_nominated_for_ballot.call_args.args[0]
            assert nominated_player == villagers[0].my_self
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive ballot message within the timeout period."
            )

    # Vote to execute the nominated player
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify vote message.")
            async with asyncio.timeout(TEST_TIMEOUT):
                if controller.my_self is not villagers[0].my_self: 
                    await controller.vote_guilty()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller couldn't vote within the timeout period."
            )

    # Wait for the night
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.start_night.called:
                    await asyncio.sleep(0.1)
            event_sender.start_night.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive night start message within the timeout period after execution."
            )

    # Verify that all controllers receive the correct execution result message with the executed player and their role
    should_be_executed = villagers[0].my_self_as_player().name # pyright: ignore[reportOptionalMemberAccess]
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock, cannot verify execution result message.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.message_player_executed.called:
                    await asyncio.sleep(0.1)
            event_sender.message_player_executed.assert_called_once()
            assert event_sender.message_player_executed.call_args.args[0] == should_be_executed
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive execution result message within the timeout period."
            )

    # Resets all mocks
    for _, event_sender in controllers:
        if isinstance(event_sender, mock.Mock):
            event_sender.reset_mock()

    # The werewolves vote for a villager to be killed
    for controller in werewolves:
        try:
            async with asyncio.timeout(TEST_TIMEOUT):
                await controller.choose_player(villagers[1].my_self)
        except asyncio.TimeoutError:
            pytest.fail(
                "A werewolf controller couldn't choose a player to kill within the timeout period."
            )

    # Wait for the day
    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.end_night.called:
                    await asyncio.sleep(0.1)
            event_sender.end_night.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive day start message within the timeout period after night."
            )
    
    # Verify that all controllers receive the correct kill result message with the killed player
    assert villagers[1].my_self_as_player().is_alive() is False, "The chosen player was not killed." # pyright: ignore[reportOptionalMemberAccess]

    for controller, event_sender in controllers:
        try:
            if not isinstance(event_sender, mock.Mock):
                pytest.fail("Event sender is not a mock.")
            async with asyncio.timeout(TEST_TIMEOUT):
                while not event_sender.message_player_killed_during_night.called:
                    await asyncio.sleep(0.1)
            event_sender.message_player_killed_during_night.assert_called_once()
            assert villagers[1].my_self_as_player().name == event_sender.message_player_killed_during_night.call_args.args[0] # pyright: ignore[reportOptionalMemberAccess]
        except asyncio.TimeoutError:
            pytest.fail(
                "A controller did not receive kill result message within the timeout period after night."
            )

