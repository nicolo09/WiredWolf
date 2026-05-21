import unittest
from wiredwolf.model.game import Game
from wiredwolf.model.game_phases import GamePhase, GamePhaseOutcome
from wiredwolf.model.player import Player, Status
from tests.model.game_test import populate_players, get_index_by_name, create_game_info


class GamePhaseTest(unittest.TestCase):

    def setUp(self):
        self.players: list[Player] = populate_players()
        self.game: Game = Game(self.players, create_game_info(), GamePhase.DAY_DISCUSSION)

    def test_regular_phase_transitions(self):
        
        test_game: Game = Game(self.players, create_game_info())
        outcome: GamePhaseOutcome
        
        outcome = test_game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.NIGHT)
        outcome = test_game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_DISCUSSION)
        outcome = test_game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_ACCUSING)
        test_game.accuse_player("Alice", "Bob")
        outcome = test_game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_BALLOT)
        outcome = test_game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.NIGHT)
        

    def test_skip_ballot_vote_draw(self):

        outcome: GamePhaseOutcome

        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_ACCUSING)
        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.NIGHT)
        
    def test_get_accused_player(self):

        outcome: GamePhaseOutcome

        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_ACCUSING)
        self.game.accuse_player("Alice", "Bob")
        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_BALLOT)
        accused: Player | None = outcome.get_accused_player()
        if accused is not None:
            self.assertEqual(accused.name, "Bob")
        else:
            self.fail("Accused player should not be None")

    def test_advance_all_phases(self):

        outcome: GamePhaseOutcome

        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_ACCUSING)
        self.game.accuse_player("Alice", "Bob")
        outcome = self.game.advance_phase()
        self.assertEqual(outcome.new_phase, GamePhase.DAY_BALLOT)
        outcome = self.game.advance_phase()
        self.assertFalse(outcome.someone_died())
        self.assertEqual(outcome.new_phase, GamePhase.NIGHT)
        outcome = self.game.advance_phase()
        self.assertFalse(outcome.someone_died())
        self.assertEqual(outcome.new_phase, GamePhase.DAY_DISCUSSION)
        for player in self.game.players:
            self.assertEqual(player.status, Status.ALIVE)

    def test_skip_ballot_accused_killed(self):

        bob_index = get_index_by_name(self.players, "Bob")

        self.game.advance_phase()
        self.game.accuse_player("Alice", "Bob")
        self.game.advance_phase()
        self.game.ballot_vote("Alice", True)
        self.game.ballot_vote("Charlie", False)
        self.game.ballot_vote("Diana", False)
        self.game.ballot_vote("Frank", False)
        self.game.kill_player("Bob")
        self.assertEqual(self.game.phase, GamePhase.NIGHT)
        self.assertEqual(self.game.players[bob_index].status, Status.DEAD)
