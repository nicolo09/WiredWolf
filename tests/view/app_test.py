import unittest

from wiredwolf.view.app import *

class TestApp(unittest.TestCase):
    """Unit test for view custom events"""

    def setUp(self) -> None:
        pygame.init()
        self.display_screen = pygame.display.set_mode((100, 100), pygame.RESIZABLE)
        self.gui_manager=pygame_gui.UIManager((100, 100))
        self.panel_handeler=PanelHandler(self.gui_manager)
        self.start_screen=Screens.HOME
        self.game_state_manager=GameStateManager(self.start_screen, self.panel_handeler)

    def test_game_state_manager_state(self)->None:
        """The game state manager must change state correctly"""
        other_screen=Screens.VILLAGER_WIN
        self.assertEqual(self.game_state_manager.current_state, self.start_screen)
        self.game_state_manager.change_screen(other_screen)
        self.assertNotEqual(self.game_state_manager.current_state, self.start_screen)
        self.assertEqual(self.game_state_manager.current_state, other_screen)
        self.game_state_manager.change_screen(self.start_screen)
        self.assertNotEqual(self.game_state_manager.current_state, other_screen)
        self.assertEqual(self.game_state_manager.current_state, self.start_screen)
