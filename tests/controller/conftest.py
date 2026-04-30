"""
This is where fixture used in many places should stay
"""

import pytest_asyncio

from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser

TIMEOUT = 5


@pytest_asyncio.fixture
async def browser():
    lobby_browser = TcpMdnsLobbyBrowser()
    yield lobby_browser