import pytest
import pytest_asyncio
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.connections import AsyncTCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer

@pytest.fixture()
def lobby():
    owner = Peer("Test Peer")
    lobby = Lobby(owner, "Test Lobby", "password123")
    yield lobby

@pytest_asyncio.fixture()
async def server(lobby: Lobby):
    server = GameServer(lobby)
    assert isinstance(server.connection_handler, AsyncTCPServerConnectionHandler)
    await server.start_listening()
    yield server
    await server.close()

@pytest.fixture()
def tcp_mdns_lobby_browser():
    browser = TcpMdnsLobbyBrowser()
    yield browser
    try:
        browser.stop_publishing_lobby()
        browser.stop_lobby_browser()
    except RuntimeError:
        pass

@pytest.mark.asyncio
async def test_client_connect_to_server(lobby: Lobby, server: GameServer, tcp_mdns_lobby_browser: TcpMdnsLobbyBrowser):
    myself = Peer("Test Peer")
    handler, recv_lobby = await tcp_mdns_lobby_browser.connect_to_lobby_directly(
        myself,
        (
            "localhost",
            DEFAULT_SERVER_PORT,
        ),
        "password123"
    )
    assert recv_lobby == lobby
    await handler.close()

def test_peer_connect(lobby: Lobby, server: GameServer, tcp_mdns_lobby_browser: TcpMdnsLobbyBrowser):
    # Start the lobby browser
    lobbies: list[Lobby] = []
    tcp_mdns_lobby_browser.start_lobby_browser(on_lobby_found=lobbies.append, on_lobby_lost=lobbies.remove, on_lobby_updated=lambda x: None,)  # type: ignore
    tcp_mdns_lobby_browser.publish_lobby(
        lobby.name, DEFAULT_SERVER_PORT
    )
    # Wait for the lobby to be discovered
    while not lobbies:
        pass
