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
async def controller(browser: TcpMdnsLobbyBrowser) -> AsyncGenerator[tuple[GameController, EventSender], None]:
    event_sender = mock.Mock()
    controller = GameController(browser=browser, event_sender=event_sender)
    controller.set_username("TestUser")
    yield controller, event_sender
    try:
        controller.stop_listening_for_lobbies()
    except Exception:
        pass

second_controller = controller

@pytest.mark.asyncio
async def test_controller_initialization(controller: tuple[GameController, EventSender]):
    game_controller, event_sender = controller
    assert isinstance(game_controller, GameController)
    assert game_controller.lobby is None

@pytest.mark.asyncio
async def test_controller_publish_discover_lobby(controller: tuple[GameController, EventSender], second_controller: tuple[GameController, EventSender]):
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
            pytest.fail("Second controller did not discover the lobby within the timeout period.")
    
