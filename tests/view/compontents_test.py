import unittest

from wiredwolf.view.components import *

class TestComponents(unittest.TestCase):
    """Unit test for view components"""

    def setUp(self) -> None:
        self.MAX=5
        self.list=LimitedList(self.MAX)

    def test_component_empty(self):
        """A limited list starts out as empty"""
        self.assertEqual(len(self.list.list),0)

    def test_component_limit(self):
        """A limited list can hold at most max elements"""
        for i in range(0,self.MAX+1):
            self.list.add_element(str(i))
        self.assertEqual(len(self.list.list), self.MAX)

    def test_component_order(self):
        """A limited list stores items as a FIFO list"""
        ordinary_list:list[str]=[]
        for i in range(0,self.MAX-1):
            self.list.add_element(str(i))
            ordinary_list.insert(0, (str(i)))
        self.assertEqual(len(self.list.list), self.MAX-1)
        self.assertEqual(self.list.list, ordinary_list)
