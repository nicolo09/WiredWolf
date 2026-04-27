import unittest

from wiredwolf.model.game_builder import GameInfoBuilder
from wiredwolf.model.game_template import AbstractGameInfo, GameActionData, GameInfoBase, GameInfoDecorator
from wiredwolf.model.player import Alignment, BasicRole, Player, Role
from wiredwolf.model.role_extensions import ClairvoyantDecorator, MediumDecorator

class CustomRole(Role):
    TEST = ("Test", Alignment.GOOD_ALIGNMENT)


class TestDecorator(GameInfoDecorator):
    def __init__(self, wrapped: AbstractGameInfo, game_data: GameActionData | None = None) -> None:
        super().__init__(wrapped)
        self.game_data = game_data
        
    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {CustomRole.TEST}
    
    def get_decorator_data(self) -> GameActionData:
        return GameActionData({})
    
    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        return []
    
    def _compare_decorator(self, other: AbstractGameInfo) -> bool:
        return isinstance(other, TestDecorator)

class GameBuilderTest(unittest.TestCase):
    
    def test_game_creation(self):
        
        expected_game_info: AbstractGameInfo = MediumDecorator(ClairvoyantDecorator(GameInfoBase()))
        
        builder = GameInfoBuilder.new().with_roles({BasicRole.MEDIUM, BasicRole.CLAIRVOYANT})
        
        game_info: AbstractGameInfo = builder.build()
        
        self.assertTrue(BasicRole.MEDIUM in game_info.get_all_handled_roles())
        self.assertTrue(BasicRole.CLAIRVOYANT in game_info.get_all_handled_roles())
        
        self.assertEqual(game_info, expected_game_info)
        
    def test_game_creation_with_game_data(self):
        
        game_data = GameActionData({"clairvoyant_acted": True})
        
        expected_game_info: AbstractGameInfo = MediumDecorator(ClairvoyantDecorator(GameInfoBase(), game_data))
        
        builder = GameInfoBuilder.with_game_data(game_data, []).with_roles({BasicRole.MEDIUM, BasicRole.CLAIRVOYANT})
        
        game_info: AbstractGameInfo = builder.build()
        
        self.assertEqual(game_info, expected_game_info)
        
        try:
            game_info.handle_night_actions(Player("Test", "Test", BasicRole.CLAIRVOYANT), Player("Target", "Target", BasicRole.WEREWOLF))
            self.fail("Expected an exception when handling night actions with Clairvoyant already acted.")
        except Exception:
            pass
        
    def test_game_creation_with_custom_role(self):
        
        expected_game_info: AbstractGameInfo = TestDecorator(GameInfoBase())
        custom_module = "tests.model.game_builder_test"
        
        builder = GameInfoBuilder.new().add_decorator_module(custom_module).with_roles({CustomRole.TEST})
        
        game_info: AbstractGameInfo = builder.build()
        
        self.assertTrue(CustomRole.TEST in game_info.get_all_handled_roles())
        
        self.assertEqual(game_info, expected_game_info)
