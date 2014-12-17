"""
some tests for pytmx

WIP - all code that isn't abandoned is WIP
"""

from unittest import TestCase

import pytmx
from pytmx import handle_bool

class TiledMapTest(TestCase):
    filename = 'tests/test01.tmx'

    def setUp(self):
        self.m = pytmx.TiledMap(self.filename)

    def test_load(self):
        pass

    def test_get_tile_image(self):
        image = self.m.get_tile_image(0, 0, 0)

    def test_get_tile_image_by_gid(self):
        # 0 should always return None
        image = self.m.get_tile_image_by_gid(0)
        self.assertIsNone(image)

        image = self.m.get_tile_image_by_gid(1)
        self.assertIsNotNone(image)

    def test_import_pytmx_doesnt_import_pygame(self):
        import pytmx
        import sys
        self.assertTrue('pygame' not in sys.modules)



class handle_bool_TestCase(TestCase):

    def test_when_passed_true_it_should_return_true(self):
        self.assertTrue(handle_bool("true"))

    def test_when_passed_yes_it_should_return_true(self):
        self.assertTrue(handle_bool("yes"))

    def test_when_passed_false_it_should_return_false(self):
        self.assertFalse(handle_bool("false"))

    def test_when_passed_no_it_should_return_false(self):
        self.assertFalse(handle_bool("no"))

    def test_when_passed_zero_it_should_return_false(self):
        self.assertFalse(handle_bool("0"))

    def test_when_passed_non_zero_it_should_return_true(self):
        self.assertTrue(handle_bool("1337"))

    def test_when_passed_garbage_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            handle_bool("garbage")

    def test_when_passed_None_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            handle_bool(None)
