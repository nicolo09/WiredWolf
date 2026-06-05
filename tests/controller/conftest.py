"""
This is where fixture used in many places should stay
"""

from typing import AsyncGenerator
from unittest import mock

from pytest import MonkeyPatch
import pytest_asyncio

from wiredwolf.controller import commons
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.view.custom_events import EventSender

TEST_TIMEOUT = 5
TEST_PHASE_DURATION_SECONDS = 3

TEST_USER_BASE = "TestUser"

@pytest_asyncio.fixture
async def browser():
    lobby_browser = TcpMdnsLobbyBrowser()
    yield lobby_browser

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

# Set short phase durations for testing, so we don't have to wait long for phases to advance in tests
monkeypatch = MonkeyPatch()
monkeypatch.setattr(commons, "FIRST_DAY_PHASE_DURATION_SECONDS", TEST_PHASE_DURATION_SECONDS)
monkeypatch.setattr(commons, "PHASE_DURATION_SECONDS", TEST_PHASE_DURATION_SECONDS)