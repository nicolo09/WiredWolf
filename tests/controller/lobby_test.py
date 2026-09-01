import asyncio

import pytest
import pytest_asyncio
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.lobbies import Lobby, LobbyInfo, TcpMdnsLobbyBrowser
from wiredwolf.controller.game_server import GameServer, GameServerFactory


@pytest.fixture()
def lobby():
    owner = Peer("Test Peer")
    lobby = Lobby(owner=owner, name="Test Lobby", password="password123")
    yield lobby


@pytest_asyncio.fixture()
async def server(lobby: Lobby):
    server, _ = await GameServerFactory.get_game_server(lobby)
    await server.start_listening()
    yield server
    await server.close()


@pytest_asyncio.fixture()
async def tcp_mdns_lobby_browser():
    browser = TcpMdnsLobbyBrowser()
    yield browser
    try:
        await browser.stop_publishing_lobby()
        browser.stop_lobby_browser()
    except RuntimeError:
        pass


@pytest.mark.asyncio
async def test_client_connect_to_server(
    lobby: Lobby, server: GameServer, tcp_mdns_lobby_browser: TcpMdnsLobbyBrowser
):
    myself = Peer("Test Peer")
    handler, recv_lobby = await tcp_mdns_lobby_browser.connect_to_lobby_directly(
        myself,
        (
            "localhost",
            DEFAULT_SERVER_PORT,
        ),
        "password123",
    )
    assert recv_lobby == lobby
    await handler.close()


@pytest.mark.asyncio
async def test_peer_connect(
    lobby: Lobby, server: GameServer, tcp_mdns_lobby_browser: TcpMdnsLobbyBrowser
):
    # Start the lobby browser
    lobbies: list[LobbyInfo] = []

    def remove_lobby(lobby_info: LobbyInfo):
        nonlocal lobbies
        lobbies = [lobby for lobby in lobbies if lobby.name != lobby_info.name]

    tcp_mdns_lobby_browser.start_lobby_browser(
        on_lobby_found=lobbies.append,
        on_lobby_lost=remove_lobby,
        on_lobby_updated=lambda x: None,
    )  # type: ignore
    try:
        async with asyncio.timeout(5):
            await tcp_mdns_lobby_browser.publish_lobby(lobby.lobby_info(), DEFAULT_SERVER_PORT)
    except asyncio.TimeoutError:
        pytest.fail("Failed to publish the lobby within the timeout period.")
    # Wait for the lobby to be discovered
    try:
        async with asyncio.timeout(5):
            while not lobbies:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("Lobby was not discovered within the timeout period.")
    await tcp_mdns_lobby_browser.stop_publishing_lobby()
    tcp_mdns_lobby_browser.stop_lobby_browser()


@pytest.mark.asyncio
async def test_receive_correct_lobby_info(
    lobby: Lobby, tcp_mdns_lobby_browser: TcpMdnsLobbyBrowser
):
    # Start the lobby browser
    lobbies: list[LobbyInfo] = []

    def remove_lobby(lobby_info: LobbyInfo):
        nonlocal lobbies
        lobbies = [lobby for lobby in lobbies if lobby.name != lobby_info.name]

    tcp_mdns_lobby_browser.start_lobby_browser(
        on_lobby_found=lobbies.append,
        on_lobby_lost=remove_lobby,
        on_lobby_updated=lambda x: None,
    )
    await tcp_mdns_lobby_browser.publish_lobby(lobby.lobby_info(), DEFAULT_SERVER_PORT)
    # Wait for the lobby to be discovered (with timeout to avoid infinite loop in case of failure)
    try:
        async with asyncio.timeout(5):
            while not lobbies:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail("Lobby was not discovered within the timeout period.")
    assert lobbies[0] == lobby.lobby_info()
    await tcp_mdns_lobby_browser.stop_publishing_lobby()
    tcp_mdns_lobby_browser.stop_lobby_browser()

