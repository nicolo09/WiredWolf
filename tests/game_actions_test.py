import unittest
from wiredwolf.model.game import Game
from wiredwolf.model.player import Status
from tests.game_test import populate_players, get_index_by_name

class GameActionsTest(unittest.TestCase):
    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players)

    # Test Werewolves Actions    
        
    def test_werewolf_action(self):
        
        alice_index = get_index_by_name(self.players, "Alice")
        
        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.DEAD)

    def test_werewolf_action_error(self):
        self.game.kill_player("Alice")
        self.game.advance_phase()
        self.game.advance_phase()
        with self.assertRaises(ValueError):
            self.game.perform_night_action("Bob", "Alice")
        
    def test_werewolf_action_draw(self):

        alice_index = get_index_by_name(self.players, "Alice")
        grace_index = get_index_by_name(self.players, "Grace")

        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.perform_night_action("Frank", "Grace")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.ALIVE)
        self.assertEqual(self.game.players[grace_index].status, Status.ALIVE)

    # Test Special Role Actions

    def test_escort_action(self):

        alice_index = get_index_by_name(self.players, "Alice")

        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.perform_night_action("Charlie", "Alice")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.ALIVE)

    def test_clairvoyant_action(self):
        self.game.advance_phase()
        self.game.advance_phase()
        self.assertTrue(self.game.perform_night_action("Diana", "Bob"))
        
    
    def test_medium_action(self):
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.advance_phase()
        self.assertTrue(self.game.perform_night_action("Eve", "Bob"))