import asyncio
from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.view.custom_events import EventSender

LOBBY_NAME = "Test Lobby"


@pytest_asyncio.fixture
async def controller(
    browser: TcpMdnsLobbyBrowser,
) -> AsyncGenerator[tuple[GameController, EventSender], None]:
    event_sender = mock.Mock()
    controller = GameController(browser=browser, event_sender=event_sender)
    controller.set_username("TestUser")
    yield controller, event_sender
    try:
        await controller.leave()
    except Exception:
        pass


second_controller = controller


@pytest.mark.asyncio
async def test_controller_initialization(
    controller: tuple[GameController, EventSender],
):
    game_controller, event_sender = controller
    assert isinstance(game_controller, GameController)
    assert game_controller.lobby is None





@pytest.mark.asyncio
async def test_controller_publish_discover_lobby(
    controller: tuple[GameController, EventSender],
    second_controller: tuple[GameController, EventSender],
):
    game_controller, event_sender = controller
    second_game_controller, second_event_sender = second_controller
    second_game_controller.start_listening_for_lobbies()
    if isinstance(second_event_sender, mock.Mock):
        second_event_sender.new_discovered_lobby.assert_not_called()
    await game_controller.create_lobby(name=LOBBY_NAME, password=None)

    if isinstance(second_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(5):
                while not second_event_sender.new_discovered_lobby.called:
                    await asyncio.sleep(0.1)
                second_event_sender.new_discovered_lobby.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "Second controller did not discover the lobby within the timeout period."
            )


@pytest.mark.asyncio
async def test_controller_join_lobby(
    controller: tuple[GameController, EventSender],
    second_controller: tuple[GameController, EventSender],
):
    game_controller, event_sender = controller
    second_game_controller, second_event_sender = second_controller
    await game_controller.create_lobby(name=LOBBY_NAME, password=None)
    assert game_controller.lobby is not None
    second_game_controller.start_listening_for_lobbies()

    lobby_info = None
    if isinstance(second_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(5):
                # Wait until the second controller discovers the lobby and captures the lobby info from the call arguments
                while (
                    not second_event_sender.new_discovered_lobby.called
                    or lobby_info is None
                ):
                    if second_event_sender.new_discovered_lobby.call_args:
                        calls = second_event_sender.new_discovered_lobby.call_args_list
                        calls = [
                            call
                            for call in calls
                            if call.args
                            and call.args[0].uuid
                            == game_controller.lobby.lobby_info().uuid
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
    assert lobby_info == game_controller.lobby.lobby_info(), (
        "The discovered lobby info does not match the created lobby info."
    )

    await second_game_controller.join_lobby(lobby_name=lobby_info, lobby_password=None)

    assert second_game_controller.lobby is not None

    assert game_controller.lobby == second_game_controller.lobby
    assert len(second_game_controller.lobby.peers) == 2
