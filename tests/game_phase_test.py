import unittest
from wiredwolf.model.game import Game, GamePhase
from wiredwolf.model.player import Status
from tests.game_test import populate_players, get_index_by_name

class GamePhaseTest(unittest.TestCase):
    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players)
        
    def test_skip_ballot_vote_draw(self):
            self.game.advance_phase()
            self.assertEqual(self.game.phase, GamePhase.DAY_ACCUSING)
            self.game.advance_phase()
            self.assertEqual(self.game.phase, GamePhase.NIGHT)
            
    def test_advance_all_phases(self):
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.DAY_ACCUSING)
        self.game.accuse_player("Alice", "Bob")
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.DAY_BALLOT)
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.NIGHT)
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.DAY_DISCUSSION)
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