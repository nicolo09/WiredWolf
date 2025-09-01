

from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.server import GameServer


def test_join_server():
    lobby: Lobby = Lobby("Test Lobby", "password123")
    server: GameServer = GameServer(lobby)
    