"""
some tests for pytmx

WIP - all code that isn't abandoned is WIP
"""

from unittest import TestCase
from mock import Mock
from mock import patch

import pytmx
from pytmx import convert_to_bool
from pytmx import TiledElement

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
        self.assertTrue(convert_to_bool("true"))

    def test_when_passed_yes_it_should_return_true(self):
        self.assertTrue(convert_to_bool("yes"))

    def test_when_passed_false_it_should_return_false(self):
        self.assertFalse(convert_to_bool("false"))

    def test_when_passed_no_it_should_return_false(self):
        self.assertFalse(convert_to_bool("no"))

    def test_when_passed_zero_it_should_return_false(self):
        self.assertFalse(convert_to_bool("0"))

    def test_when_passed_non_zero_it_should_return_true(self):
        self.assertTrue(convert_to_bool("1337"))

    def test_when_passed_garbage_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool("garbage")

    def test_when_passed_None_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool(None)


class TiledElementTestCase(TestCase):

    def setUp(self):
        self.tiled_element = TiledElement()
        self.tiled_element.name = "Foo"

    def test_from_xml_string_should_raise_on_TiledElement(self):
        with self.assertRaises(AttributeError):
            TiledElement.from_xml_string("<element></element>")

    def test_when_property_is_reserved_contains_invalid_property_name_returns_true(self):
        self.tiled_element = TiledElement()
        self.tiled_element.name = "Foo"
        items = [("contains_invalid_property_name", None)]
        self.assertTrue(self.tiled_element.contains_invalid_property_name(items))

    def test_when_property_is_not_reserved_contains_invalid_property_name_returns_false(self):
        self.assertFalse(self.tiled_element.contains_invalid_property_name(list()))

    @patch("pytmx.parse_properties")
    def test_set_properties_raises_value_error_if_invalid_property_name_in_node(self, mock_parse_properties):
        mock_node = Mock()
        mock_node.items.return_value = list()
        self.tiled_element.contains_invalid_property_name = Mock(return_value=True)
        with self.assertRaises(ValueError):
            self.tiled_element.set_properties(mock_node)

    def test_repr(self):
        self.assertEqual("<TiledElement: \"Foo\">it add ..", self.tiled_element.__repr__())
