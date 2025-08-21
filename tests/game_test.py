import unittest
from wiredwolf.model.game import Game, GamePhase, GameStatus
from wiredwolf.model.game_modifiers import AbstractGameInfo, BasicGameInfoFactory, ClairvoyantGameInfoDecorator, EscortGameInfoDecorator, MediumGameInfoDecorator, MinimalGameInfo
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
        self.game = Game(self.players, BasicGameInfoFactory.build())
        
    def test_initial_state(self):
        self.assertEqual(self.game.phase, GamePhase.DAY_DISCUSSION)
        for player in self.game.players:
            self.assertEqual(player.status, Status.ALIVE)
            
    def test_game_status_equals(self):

        correct_players = populate_players()
        correct_status: GameStatus = GameStatus(correct_players,
                                                BasicGameInfoFactory.build(),
                                                GamePhase.NIGHT)

        correct_status.players[get_index_by_name(correct_players, "Alice")].status = Status.DEAD
        correct_status.players[get_index_by_name(correct_players, "Bob")].status = Status.DEAD

        escort: Player = correct_status.players[get_index_by_name(correct_players, "Charlie")]
        medium: Player = correct_status.players[get_index_by_name(correct_players, "Eve")]

        correct_status.game_info.handle_night_actions(escort, medium)

        self.game.kill_player("Alice")
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Charlie", "Eve")

        self.assertEqual(self.game.get_game_status(), correct_status)
        
    def test_game_info_equals(self):
        game_info_comparison: AbstractGameInfo =  MinimalGameInfo()
        game_info_comparison = MediumGameInfoDecorator(game_info_comparison)
        game_info_comparison = ClairvoyantGameInfoDecorator(game_info_comparison)
        game_info_comparison = EscortGameInfoDecorator(game_info_comparison)

        self.assertEqual(self.game.get_game_status().game_info, game_info_comparison)

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
    