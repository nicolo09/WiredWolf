"""
This is where fixture used in many places should stay
"""

from pytest import MonkeyPatch
import pytest_asyncio

from wiredwolf.controller import commons
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser

TEST_TIMEOUT = 5

TEST_PHASE_DURATION_SECONDS = 3

@pytest_asyncio.fixture
async def browser():
    lobby_browser = TcpMdnsLobbyBrowser()
    yield lobby_browser

# Set short phase durations for testing, so we don't have to wait long for phases to advance in tests
monkeypatch = MonkeyPatch()
monkeypatch.setattr(commons, "FIRST_DAY_PHASE_DURATION_SECONDS", TEST_PHASE_DURATION_SECONDS)
monkeypatch.setattr(commons, "PHASE_DURATION_SECONDS", TEST_PHASE_DURATION_SECONDS)