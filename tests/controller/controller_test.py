from unittest import mock

import pytest
import pytest_asyncio
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser

@pytest_asyncio.fixture
async def controller(browser: TcpMdnsLobbyBrowser):
    event_sender = mock.Mock()
    yield GameController(browser=browser, event_sender=event_sender), event_sender


@pytest.mark.asyncio
async def test_controller_initialization(controller):
    game_controller, event_sender = controller
    assert isinstance(game_controller, GameController)
    assert game_controller.lobby is None
