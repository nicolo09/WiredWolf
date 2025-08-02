import unittest
from wiredwolf.model.game import Game, GamePhase
from wiredwolf.model.player import Status
from tests.game_test import populate_players, get_index_by_name

class GameVotingTest(unittest.TestCase):
    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players)

    def test_double_vote(self):
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Bob")
        with self.assertRaises(ValueError):
            self.game.accuse_player("Alice", "Charlie")
            
    def test_vote_dead_player(self):
        self.game.advance_phase()
        self.game.kill_player("Bob")
        with self.assertRaises(ValueError):
            self.game.accuse_player("Alice", "Bob")
            
    def test_vote_after_death(self):
        self.game.advance_phase()
        self.game.kill_player("Bob")
        with self.assertRaises(ValueError):
            self.game.accuse_player("Bob", "Alice")
            
    def test_reset_vote(self):
        
        alice_index = get_index_by_name(self.players, "Alice")
        
        self.game.advance_phase()
        self.game.accuse_player("Bob", "Alice")
        self.game.kill_player("Alice")
        self.game.accuse_player("Bob", "Charlie")
        self.assertEqual(self.game.players[alice_index].status, Status.DEAD)
        with self.assertRaises(ValueError):
            self.game.accuse_player("Bob", "Eve")
    
    def test_accusation_vote_draw(self):
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Bob")
        self.game.accuse_player("Charlie", "Bob")
        self.game.accuse_player("Diana", "Bob")
        self.game.accuse_player("Bob", "Alice")
        self.game.accuse_player("Frank", "Alice")
        self.game.accuse_player("Grace", "Alice")
        self.game.advance_phase()
        self.assertEqual(self.game.phase, GamePhase.NIGHT)
        
    def test_ballot_vote_approved(self):
        
        bob_index = get_index_by_name(self.players, "Bob")
        
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Bob")
        self.game.advance_phase()
        self.game.ballot_vote("Alice", True)
        self.game.ballot_vote("Charlie", True)
        self.game.ballot_vote("Diana", True)
        self.game.ballot_vote("Frank", False)
        self.game.advance_phase()
        self.assertEqual(self.game.players[bob_index].status, Status.DEAD)

    def test_ballot_vote_rejected(self):
        
        bob_index = get_index_by_name(self.players, "Bob")
        
        self.game.advance_phase()
        self.game.accuse_player("Alice", "Bob")
        self.game.advance_phase()
        self.game.ballot_vote("Frank", False)
        self.game.ballot_vote("Grace", False)
        self.game.ballot_vote("Alice", True)
        self.game.advance_phase()
        self.assertEqual(self.game.players[bob_index].status, Status.ALIVE)
