import unittest
from wiredwolf.model.game import Game, GameStatus
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.game_template import AbstractGameInfo
from wiredwolf.model.role_extensions import MediumDecorator
from wiredwolf.model.game_builder import GameInfoBuilder

from wiredwolf.model.player import Player, BasicRole, Status


def populate_players() -> list[Player]:

    # For simplicity, we are using the same name as id,
    # but in a real implementation these would be unique identifiers.

    return [
        Player("Alice", "Alice", BasicRole.VILLAGER),
        Player("Bob", "Bob", BasicRole.WEREWOLF),
        Player("Charlie", "Charlie", BasicRole.ESCORT),
        Player("Diana", "Diana", BasicRole.CLAIRVOYANT),
        Player("Eve", "Eve", BasicRole.MEDIUM),
        Player("Frank", "Frank", BasicRole.WEREWOLF),
        Player("Grace", "Grace", BasicRole.VILLAGER),
    ]


def create_game_info() -> AbstractGameInfo:
    return GameInfoBuilder.new().with_roles({BasicRole.CLAIRVOYANT, BasicRole.MEDIUM, BasicRole.ESCORT}).build()

#FIXME: remove and make it better
def get_index_by_name(players: list[Player], name: str) -> int:
    """
    Helper function to get the index of a player by their name.
    """
    for index, player in enumerate(players):
        if player.name == name:
            return index
    raise ValueError(f"Player with name {name} not found.")


class GameInfoTest(unittest.TestCase):

    def test_game_info_equals(self):
        game_info_comparison: AbstractGameInfo = (
            GameInfoBuilder.new()
            .with_roles({BasicRole.MEDIUM, BasicRole.CLAIRVOYANT, BasicRole.ESCORT})
            .build()
        )

        self.assertEqual(create_game_info(), game_info_comparison)

    def test_game_info_not_equals(self):
        game_info_different: AbstractGameInfo = (
            GameInfoBuilder.new().with_roles({BasicRole.MEDIUM, BasicRole.CLAIRVOYANT}).build()
        )

        self.assertNotEqual(create_game_info(), game_info_different)

    def test_duplicate_roles_error(self):
        base_game_info: AbstractGameInfo = (
            GameInfoBuilder.new().with_roles({BasicRole.MEDIUM}).build()
        )
        with self.assertRaises(ValueError):
            _ = MediumDecorator(base_game_info)
            self.fail("Expected ValueError for duplicate roles not raised.")

class GameTest(unittest.TestCase):

    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players, create_game_info(), GamePhase.DAY_DISCUSSION)

    def test_initial_state(self):
        self.assertEqual(self.game.phase, GamePhase.DAY_DISCUSSION)
        self.assertEqual(self.game.day_count, 1)
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
        self.assertEqual(self.game.day_count, 2)
        self.game.kill_player("Eve")
        self.assertEqual(self.game.phase, GamePhase.WEREWOLVES_VICTORY)
        
class GameStatusTest(unittest.TestCase):

    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players, create_game_info(), GamePhase.DAY_DISCUSSION)
        
    def test_game_status_equals(self):

        test_players = populate_players()
        test_game_info: AbstractGameInfo = create_game_info()

        test_players[get_index_by_name(test_players, "Alice")].status = (
            Status.DEAD
        )
        test_players[get_index_by_name(test_players, "Bob")].status = Status.DEAD

        escort: Player = test_players[get_index_by_name(test_players, "Charlie")]
        medium: Player = test_players[get_index_by_name(test_players, "Eve")]

        test_game_info.handle_night_actions(escort, medium)

        test_status: GameStatus = GameStatus(
            test_players,
            test_game_info.get_all_handled_roles(),
            test_game_info.get_game_modules(),
            test_game_info.get_game_data(),
            GamePhase.NIGHT,
            1
        )
        
        self.game.kill_player("Alice")
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Charlie", "Eve")

        self.assertEqual(self.game.get_game_status(), test_status)
        
    def test_game_status_consistency_between_phases(self):
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Frank")

        first_status: GameStatus = self.game.get_game_status()
        first_game_copy: Game = Game.from_game_status(first_status)

        first_game_copy.advance_phase()
        first_game_copy.ballot_vote("Alice", True)

        second_status = first_game_copy.get_game_status()
        second_game_copy: Game = Game.from_game_status(second_status)

        second_game_copy.ballot_vote("Charlie", True)
        second_game_copy.ballot_vote("Diana", True)
        second_game_copy.advance_phase()
        second_game_copy.advance_phase()
        
        self.assertEqual(second_game_copy.phase, GamePhase.VILLAGERS_VICTORY)
        
        for status in [first_status, second_status]:
            self.assertNotEqual(second_game_copy.get_game_status(), status)
            
    def test_game_status_consistency_between_actions(self):
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        
        gs_werewolf_action: GameStatus = self.game.get_game_status()

        self.game.perform_night_action("Charlie", "Alice")
        
        gs_escort_action: GameStatus = self.game.get_game_status()
        
        self.game.perform_night_action("Diana", "Alice")
        
        gs_clairvoyant_action: GameStatus = self.game.get_game_status()
        
        self.game.kill_player("Grace")
        self.game.perform_night_action("Eve", "Grace")

        for status in [gs_werewolf_action, gs_escort_action, gs_clairvoyant_action]:
            self.assertNotEqual(self.game.get_game_status(), status)

    def test_player_status_consistency(self):
            self.game.advance_phase()
            self.game.advance_phase() # Night phase
            
            self.game.perform_night_action("Bob", "Alice") # Werewolf targets Alice
            self.game.perform_night_action("Charlie", "Alice") # Escort protects Alice
            
            status: GameStatus = self.game.get_game_status()
            #TODO: if possible serialize and deserialize the game status to ensure that it is consistent even after serialization
            new_game: Game = Game.from_game_status(status) # Previous game crashed, so recreate it
            
            new_game.advance_phase() # Day phase
            
            # Alice should be alive because she was protected by the Escort
            self.assertEqual(
                new_game.players[get_index_by_name(new_game.players, "Alice")].status,
                Status.ALIVE,
            )

class GameSnapshotTest(unittest.TestCase):

    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players, create_game_info(), GamePhase.DAY_DISCUSSION)

    def test_restore_game_from_snapshot(self):
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Frank")
        self.game.accuse_player("Charlie", "Frank")
        self.game.accuse_player("Frank", "Alice")
        
        snapshot: GameStatus = self.game.get_game_snapshot()
        restored_game: Game = Game.from_game_status(snapshot)
        
        self.assertEqual(restored_game.phase, self.game.phase)
        
        try:
            restored_game.accuse_player("Alice", "Frank")
            restored_game.accuse_player("Charlie", "Alice")
        except Exception as e:
            self.fail(f"Votes should be cleared after restoring from snapshot, but got exception: {e}")
