import unittest
from wiredwolf.model.game import Game, GamePhase
from wiredwolf.model.player import Player, Role, Status

def populate_players() -> list[Player]:

    # For simplicity, the name of the players is used as their ID.
    # In a real game, IDs would likely be more complex.
    
    return [
        Player("Alice", Role.VILLAGER),
        Player("Bob", Role.WEREWOLF),
        Player("Charlie", Role.ESCORT),
        Player("Diana", Role.CLAIRVOYANT),
        Player("Eve", Role.MEDIUM),
        Player("Frank", Role.WEREWOLF),
        Player("Grace", Role.VILLAGER),
    ]
    
def get_index_by_name(players: list[Player], name: str) -> int:
    """
    Helper function to get the index of a player by their name.
    """
    for index, player in enumerate(players):
        if player.id == name:
            return index
    raise ValueError(f"Player with name {name} not found.")

class GameTest(unittest.TestCase):
    def setUp(self):

        self.players = populate_players()
        self.game = Game(self.players)
        
    def test_initial_state(self):
        self.assertEqual(self.game.phase, GamePhase.DAY_DISCUSSION)
        for player in self.game.players:
            self.assertEqual(player.status, Status.ALIVE)
    
    def test_villagers_victory(self):
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Frank")
        self.game.advance_phase()
        self.game.ballot_vote("Alice", True)
        self.game.ballot_vote("Charlie", True)
        self.game.ballot_vote("Diana", True)
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.VILLAGERS_VICTORY)
        
    def test_werewolves_victory(self):
        self.game.kill_player("Alice")
        self.game.kill_player("Charlie")
        self.game.kill_player("Diana")
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Grace")
        self.game.perform_night_action("Frank", "Grace")
        self.game.advance_phase()
        self.game.kill_player("Eve")
        self.assertEqual(self.game.phase, GamePhase.WEREWOLVES_VICTORY)
    