import pytest
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.connections import AsyncTCPServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer

@pytest.fixture()
def lobby():
    lobby = Lobby("Test Lobby", "password123")
    yield lobby

@pytest.fixture()
def server(lobby: Lobby):
    server = GameServer(lobby)
    yield server
    server.stop_new_connections()
    server.close()

@pytest.fixture()
def browser():
    browser = TcpMdnsLobbyBrowser()
    yield browser

@pytest.mark.asyncio
async def test_client_connect_to_server(lobby: Lobby, server: GameServer, browser: TcpMdnsLobbyBrowser):
    myself = Peer("Test Peer")
    assert isinstance(server.connection_handler, AsyncTCPServerConnectionHandler)
    await server.start_listening()
    handler, recv_lobby = await browser.connect_to_lobby_directly(
        myself,
        (
            "localhost",
            DEFAULT_SERVER_PORT,
        ),
        "password123"
    )
    assert recv_lobby == lobby
    await handler.close()

def test_peer_connect(lobby: Lobby, server: GameServer):
    # Start the lobby browser
    browser = TcpMdnsLobbyBrowser()
    lobbies: list[Lobby] = []
    browser.start_lobby_browser(on_lobby_found=lobbies.append, on_lobby_lost=lobbies.remove, on_lobby_updated=lambda x: None,)  # type: ignore

    assert isinstance(server.connection_handler, AsyncTCPServerConnectionHandler)
    browser.publish_lobby(
        lobby.name, DEFAULT_SERVER_PORT
    )
    # Wait for the lobby to be discovered
    while not lobbies:
        pass
    browser.stop_publishing_lobby()
    browser.stop_lobby_browser()
