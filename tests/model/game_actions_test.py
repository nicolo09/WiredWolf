import unittest
from wiredwolf.model.game import Game, can_perform_action_on
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.player import BasicRole, Status, Alignment
from wiredwolf.model.exceptions import *
from tests.model.game_test import populate_players, get_index_by_name, create_game_info


class GameActionsTest(unittest.TestCase):
    
    def setUp(self):
        self.players = populate_players()
        self.game = Game(self.players, create_game_info(), GamePhase.DAY_DISCUSSION)

    # Test Werewolves Actions

    def test_werewolf_action(self):

        alice_index = get_index_by_name(self.players, "Alice")

        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.DEAD)

    def test_werewolf_targets_werewolf(self):
        self.game.advance_phase()
        self.game.advance_phase()
        with self.assertRaises(InvalidActionError):
            self.game.perform_night_action("Bob", "Frank")

    def test_werewolf_action_error(self):
        self.game.kill_player("Alice")
        self.game.advance_phase()
        self.game.advance_phase()
        with self.assertRaises(InvalidActionError):
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
        
    def test_werewolf_targets(self):
        self.game.kill_player("Grace")
        self.game.advance_phase()
        self.game.advance_phase()
        possible_targets = can_perform_action_on(self.players[get_index_by_name(self.players, "Bob")], self.game.get_game_status())
        target_names = {player.name for player in possible_targets}
        expected_names = {player.name for player in self.players if player.name in {"Alice", "Charlie", "Diana", "Eve"}}
        self.assertEqual(target_names, expected_names)

    # Test Special Role Actions

    def test_escort_action(self):

        alice_index = get_index_by_name(self.players, "Alice")

        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.perform_night_action("Charlie", "Alice")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.ALIVE)
        
    def test_escort_removal_after_action(self):

        alice_index = get_index_by_name(self.players, "Alice")

        self.game.advance_phase()
        self.game.advance_phase()
        self.game.perform_night_action("Bob", "Alice")
        self.game.perform_night_action("Charlie", "Alice")
        self.game.kill_player("Charlie")
        self.game.advance_phase()
        self.assertEqual(self.game.players[alice_index].status, Status.DEAD)

    def test_clairvoyant_action(self):
        self.game.advance_phase()
        self.game.advance_phase()
        self.assertTrue(Alignment.EVIL_ALIGNMENT.value in self.game.perform_night_action("Diana", "Bob").message)

    def test_medium_action(self):
        self.game.kill_player("Bob")
        self.game.advance_phase()
        self.game.advance_phase()
        self.assertTrue(Alignment.EVIL_ALIGNMENT.value in self.game.perform_night_action("Eve", "Bob").message)
        
    def test_special_roles_targets(self):
        self.game.kill_player("Grace")
        self.game.advance_phase()
        self.game.advance_phase()
        
        escort_targets = can_perform_action_on(self.players[get_index_by_name(self.players, "Charlie")], self.game.get_game_status())
        escort_target_names = {player.name for player in escort_targets}
        expected_escort_names = {player.name for player in self.players if player.is_alive()}
        self.assertEqual(escort_target_names, expected_escort_names)
        
        medium_targets = can_perform_action_on(self.players[get_index_by_name(self.players, "Eve")], self.game.get_game_status())
        medium_target_names = {player.name for player in medium_targets}
        expected_medium_names = {player.name for player in self.players if not player.is_alive()}
        self.assertEqual(medium_target_names, expected_medium_names)
        
        clayvoyant_targets = can_perform_action_on(self.players[get_index_by_name(self.players, "Diana")], self.game.get_game_status())
        clayvoyant_target_names = {player.name for player in clayvoyant_targets}
        expected_clayvoyant_names = {player.name for player in self.players if player.is_alive() and player.role != BasicRole.CLAIRVOYANT}
        self.assertEqual(clayvoyant_target_names, expected_clayvoyant_names)
