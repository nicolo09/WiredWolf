import asyncio
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.lobbies import Lobby, TcpMdnsLobbyBrowser
from wiredwolf.controller.server import GameServer

async def main():
    lobby = Lobby("Test Lobby", "password123")
    server = GameServer(lobby)
    browser = TcpMdnsLobbyBrowser()
    my_self = Peer("Test Peer")

    await server.start_listening()

    await asyncio.sleep(50)  # Give the server a moment to start

asyncio.run(main())