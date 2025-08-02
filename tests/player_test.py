import unittest

from wiredwolf.model.player import Player, Role, Status

class TestPlayer(unittest.TestCase):

    def setUp(self):
        self.villager = Player("Alice", Role.VILLAGER)
        self.werewolf = Player("Bob", Role.WEREWOLF)
        
    def test_initial_status(self):
        self.assertEqual(self.villager.status, Status.ALIVE)
        self.assertEqual(self.werewolf.status, Status.ALIVE)
        
    def test_different_roles(self):
        self.assertNotEqual(self.villager.role, self.werewolf.role)
        
    def test_change_status(self):
        self.villager.status = Status.DEAD
        self.assertEqual(self.villager.status, Status.DEAD)
