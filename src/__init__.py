import asyncio
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser
from wiredwolf.controller.server import GameServer

async def main():
    lobby = Lobby("Test Lobby", "password123")
    server = GameServer(lobby)
    browser = LobbyBrowser()
    my_self = Peer("Test Peer")

    await server.start_listening()

    await asyncio.sleep(50)  # Give the server a moment to start

asyncio.run(main())