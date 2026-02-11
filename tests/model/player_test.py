import unittest

from wiredwolf.model.player import *


class TestPlayer(unittest.TestCase):

    def setUp(self):
        self.villager = Player("01", "Alice", Role.VILLAGER)
        self.werewolf = Player("02", "Bob", Role.WEREWOLF)

    def test_player_creation(self):
        ids: dict[str, str] = {
            "01": "Alice",
            "02": "Bob",
            "03": "Charlie",
            "04": "Diana",
            "05": "Eve",
            "06": "Frank",
            "07": "Grace",
            "08": "Hank",
        }
        special_roles: set[Role] = {
            Role.ESCORT,
            Role.CLAIRVOYANT,
            Role.WEREWOLF,
            Role.VILLAGER,
        }
        players = create_players(ids, special_roles)
        self.assertEqual(len(players), 8)

        villagers_count = 0
        werewolves_count = 0
        escorts_count = 0
        clairvoyants_count = 0
        mediums_count = 0

        for player in players:
            match player.role:
                case Role.VILLAGER:
                    villagers_count += 1
                case Role.WEREWOLF:
                    werewolves_count += 1
                case Role.ESCORT:
                    escorts_count += 1
                case Role.CLAIRVOYANT:
                    clairvoyants_count += 1
                case Role.MEDIUM:
                    mediums_count += 1

        self.assertEqual(escorts_count, 1)
        self.assertEqual(clairvoyants_count, 1)
        self.assertEqual(werewolves_count, 2)
        self.assertEqual(villagers_count, 4)
        self.assertEqual(mediums_count, 0)

    def test_initial_status(self):
        self.assertEqual(self.villager.status, Status.ALIVE)
        self.assertEqual(self.werewolf.status, Status.ALIVE)

    def test_different_roles(self):
        self.assertNotEqual(self.villager.role, self.werewolf.role)

    def test_change_status(self):
        self.villager.status = Status.DEAD
        self.assertEqual(self.villager.status, Status.DEAD)
