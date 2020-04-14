import unittest

import pytmx
from pytmx import TiledElement
from pytmx import convert_to_bool


class TestConvertToBool(unittest.TestCase):
    def test_string_string_true(self):
        self.assertTrue(convert_to_bool("1"))
        self.assertTrue(convert_to_bool("y"))
        self.assertTrue(convert_to_bool("Y"))
        self.assertTrue(convert_to_bool("t"))
        self.assertTrue(convert_to_bool("T"))
        self.assertTrue(convert_to_bool("yes"))
        self.assertTrue(convert_to_bool("Yes"))
        self.assertTrue(convert_to_bool("YES"))
        self.assertTrue(convert_to_bool("true"))
        self.assertTrue(convert_to_bool("True"))
        self.assertTrue(convert_to_bool("TRUE"))

    def test_string_string_false(self):
        self.assertFalse(convert_to_bool("0"))
        self.assertFalse(convert_to_bool("n"))
        self.assertFalse(convert_to_bool("N"))
        self.assertFalse(convert_to_bool("f"))
        self.assertFalse(convert_to_bool("F"))
        self.assertFalse(convert_to_bool("no"))
        self.assertFalse(convert_to_bool("No"))
        self.assertFalse(convert_to_bool("NO"))
        self.assertFalse(convert_to_bool("false"))
        self.assertFalse(convert_to_bool("False"))
        self.assertFalse(convert_to_bool("FALSE"))

    def test_string_number_true(self):
        self.assertTrue(convert_to_bool(1))
        self.assertTrue(convert_to_bool(1.0))

    def test_string_number_false(self):
        self.assertFalse(convert_to_bool(0))
        self.assertFalse(convert_to_bool(0.0))
        self.assertFalse(convert_to_bool(-1))
        self.assertFalse(convert_to_bool(-1.1))

    def test_string_bool_true(self):
        self.assertTrue(convert_to_bool(True))

    def test_string_bool_false(self):
        self.assertFalse(convert_to_bool(False))

    def test_string_bool_none(self):
        self.assertFalse(convert_to_bool(None))

    def test_string_bool_empty(self):
        self.assertFalse(convert_to_bool(""))

    def test_string_bool_whitespace_only(self):
        self.assertFalse(convert_to_bool(" "))

    def test_non_boolean_string_raises_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool("garbage")

    def test_non_boolean_number_raises_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool("200")


class TiledMapTest(unittest.TestCase):
    filename = '../resources/test01.tmx'

    def setUp(self):
        self.m = pytmx.TiledMap(self.filename)

    def test_build_rects(self):
        from pytmx import util_pygame
        rects = util_pygame.build_rects(self.m, "Grass and Water", "tileset", None)
        self.assertEqual(rects[0], [0, 0, 240, 240])
        rects = util_pygame.build_rects(self.m, "Grass and Water", "tileset", 18)
        self.assertNotEqual(0, len(rects))

    def test_get_tile_image(self):
        image = self.m.get_tile_image(0, 0, 0)

    def test_get_tile_image_by_gid(self):
        image = self.m.get_tile_image_by_gid(0)
        self.assertIsNone(image)

        image = self.m.get_tile_image_by_gid(1)
        self.assertIsNotNone(image)

    def test_reserved_names_check_disabled_with_option(self):
        pytmx.TiledElement.allow_duplicate_names = False
        pytmx.TiledMap(allow_duplicate_names=True)
        self.assertTrue(pytmx.TiledElement.allow_duplicate_names)

    def test_map_width_height_is_int(self):
        self.assertIsInstance(self.m.width, int)
        self.assertIsInstance(self.m.height, int)

    def test_layer_width_height_is_int(self):
        self.assertIsInstance(self.m.layers[0].width, int)
        self.assertIsInstance(self.m.layers[0].height, int)

    def test_properties_are_converted_to_builtin_types(self):
        self.assertIsInstance(self.m.properties['test_bool'], bool)
        self.assertIsInstance(self.m.properties['test_color'], str)
        self.assertIsInstance(self.m.properties['test_file'], str)
        self.assertIsInstance(self.m.properties['test_float'], float)
        self.assertIsInstance(self.m.properties['test_int'], int)
        self.assertIsInstance(self.m.properties['test_string'], str)


class TiledElementTestCase(unittest.TestCase):
    def setUp(self):
        self.element = TiledElement()

    def test_from_xml_string_should_raise_on_TiledElement(self):
        with self.assertRaises(AttributeError):
            TiledElement.from_xml_string("<element></element>")

    def test_contains_reserved_property_name(self):
        """ Reserved names are checked from any attributes in the instance
            after it is created.  Instance attributes are defaults from the
            specification.  We check that new properties are not named same
            as existing attributes.
        """
        self.element.name = 'foo'
        items = {'name': None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertTrue(result)

    def test_not_contains_reserved_property_name(self):
        """ Reserved names are checked from any attributes in the instance
            after it is created.  Instance attributes are defaults from the
            specification.  We check that new properties are not named same
            as existing attributes.
        """
        items = {'name': None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertFalse(result)

    def test_reserved_names_check_disabled_with_option(self):
        """ Reserved names are checked from any attributes in the instance
            after it is created.  Instance attributes are defaults from the
            specification.  We check that new properties are not named same
            as existing attributes.

            Check that passing an option will disable the check
        """
        pytmx.TiledElement.allow_duplicate_names = True
        self.element.name = 'foo'
        items = {'name': None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertFalse(result)

    def test_repr(self):
        self.element.name = 'foo'
        self.assertEqual("<TiledElement: \"foo\">", self.element.__repr__())
