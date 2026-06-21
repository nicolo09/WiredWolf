import unittest

from wiredwolf.view.components import *

class TestComponents(unittest.TestCase):
    """Unit test for view components"""

    def setUp(self) -> None:
        self.text=Text("Test", (0,0))
        self.display_screen = pygame.display.set_mode((100, 100), pygame.RESIZABLE)

    def test_container_changes_positioning(self)->None:
        """A container changes the positioning of all elements inside it"""
        self.assertEqual(self.text.text, "Test")
        self.assertEqual(self.text.position, (0,0))
        HContainer(SMALL_ELEMENT_DIV, [self.text], self.display_screen.size, position=(50,50))
        self.assertNotEqual(self.text.position, (0,0))

    def test_on_resize_change_positioning(self)->None:
        """A container changes the positioning of all elements inside it when the window gets resized"""
        before=self.text.position
        container=HContainer(SMALL_ELEMENT_DIV, [self.text], (10,10), position=(50,50))
        container.draw(self.display_screen)
        after=self.text.position
        self.assertNotEqual(before, after)


    
