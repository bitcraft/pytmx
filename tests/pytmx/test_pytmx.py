import unittest

import pytmx
from pytmx import TiledElement, convert_to_bool


class TestConvertToBool(unittest.TestCase):
    def test_string_string_true(self) -> None:
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

    def test_string_string_false(self) -> None:
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

    def test_string_number_true(self) -> None:
        self.assertTrue(convert_to_bool(1))
        self.assertTrue(convert_to_bool(1.0))

    def test_string_number_false(self) -> None:
        self.assertFalse(convert_to_bool(0))
        self.assertFalse(convert_to_bool(0.0))
        self.assertFalse(convert_to_bool(-1))
        self.assertFalse(convert_to_bool(-1.1))

    def test_string_bool_true(self) -> None:
        self.assertTrue(convert_to_bool(True))

    def test_string_bool_false(self) -> None:
        self.assertFalse(convert_to_bool(False))

    def test_string_bool_none(self) -> None:
        self.assertFalse(convert_to_bool(None))

    def test_string_bool_empty(self) -> None:
        self.assertFalse(convert_to_bool(""))

    def test_string_bool_whitespace_only(self) -> None:
        self.assertFalse(convert_to_bool(" "))

    def test_non_boolean_string_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            convert_to_bool("garbage")

    def test_non_boolean_number_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            convert_to_bool("200")


class TiledMapTest(unittest.TestCase):
    filename = "tests/resources/test01.tmx"

    def setUp(self) -> None:
        self.m = pytmx.TiledMap(self.filename)

    def test_build_rects(self) -> None:
        try:
            from pytmx import util_pygame

            rects = util_pygame.build_rects(self.m, "Grass and Water", "tileset", None)
            self.assertEqual(rects[0], [0, 0, 240, 240])
            rects = util_pygame.build_rects(self.m, "Grass and Water", "tileset", 18)
            self.assertNotEqual(0, len(rects))
        except ImportError:
            pass

    def test_get_tile_image(self) -> None:
        image = self.m.get_tile_image(0, 0, 0)

    def test_get_tile_image_by_gid(self) -> None:
        image = self.m.get_tile_image_by_gid(0)
        self.assertIsNone(image)

        image = self.m.get_tile_image_by_gid(1)
        self.assertIsNotNone(image)

    def test_reserved_names_check_disabled_with_option(self) -> None:
        pytmx.TiledElement.allow_duplicate_names = False
        pytmx.TiledMap(allow_duplicate_names=True)
        self.assertTrue(pytmx.TiledElement.allow_duplicate_names)

    def test_map_width_height_is_int(self) -> None:
        self.assertIsInstance(self.m.width, int)
        self.assertIsInstance(self.m.height, int)

    def test_layer_width_height_is_int(self) -> None:
        self.assertIsInstance(self.m.layers[0].width, int)
        self.assertIsInstance(self.m.layers[0].height, int)

    def test_properties_are_converted_to_builtin_types(self) -> None:
        self.assertIsInstance(self.m.properties["test_bool"], bool)
        self.assertIsInstance(self.m.properties["test_color"], str)
        self.assertIsInstance(self.m.properties["test_file"], str)
        self.assertIsInstance(self.m.properties["test_float"], float)
        self.assertIsInstance(self.m.properties["test_int"], int)
        self.assertIsInstance(self.m.properties["test_string"], str)

    def test_properties_are_converted_to_correct_values(self) -> None:
        self.assertFalse(self.m.properties["test_bool"])
        self.assertTrue(self.m.properties["test_bool_true"])

    def test_pixels_to_tile_pos(self) -> None:
        self.assertEqual(self.m.pixels_to_tile_pos((0, 33)), (0, 2))
        self.assertEqual(self.m.pixels_to_tile_pos((33, 0)), (2, 0))
        self.assertEqual(self.m.pixels_to_tile_pos((0, 0)), (0, 0))
        self.assertEqual(self.m.pixels_to_tile_pos((65, 86)), (4, 5))


class TiledImageLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.m = pytmx.TiledMap("tests/resources/image_layers.tmx")

    def test_hidden_image_layer_is_not_visible(self) -> None:
        self.assertEqual(
            [layer.name for layer in self.m.visible_layers],
            ["shown", "default", "transparent"],
        )

    def test_image_layer_visibility_is_boolean(self) -> None:
        self.assertIs(self.m.get_layer_by_name("hidden").visible, False)
        self.assertIs(self.m.get_layer_by_name("shown").visible, True)

    def test_image_layer_opacity_is_numeric(self) -> None:
        hidden = self.m.get_layer_by_name("hidden")
        shown = self.m.get_layer_by_name("shown")
        self.assertEqual(hidden.opacity, 0.25)
        self.assertEqual(shown.opacity, 0.75)
        self.assertEqual(hidden.opacity * 255, 63.75)

    def test_zero_opacity_is_preserved(self) -> None:
        layer = self.m.get_layer_by_name("transparent")
        self.assertEqual(layer.opacity, 0.0)
        self.assertTrue(layer.visible)

    def test_image_layer_defaults(self) -> None:
        layer = self.m.get_layer_by_name("default")
        self.assertTrue(layer.visible)
        self.assertEqual(layer.opacity, 1)

    def test_image_and_custom_properties_are_preserved(self) -> None:
        layer = self.m.get_layer_by_name("hidden")
        self.assertEqual(layer.source, "tileset.png")
        self.assertEqual(layer.trans, "ff00ff")
        self.assertEqual(layer.properties, {"description": "Hidden background"})
        self.assertIsNotNone(layer.image)


class TiledElementTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.element = TiledElement()

    def test_from_xml_string_should_raise_on_TiledElement(self) -> None:
        with self.assertRaises(AttributeError):
            TiledElement.from_xml_string("<element></element>")

    def test_contains_reserved_property_name(self) -> None:
        """Reserved names are checked from any attributes in the instance
        after it is created.  Instance attributes are defaults from the
        specification.  We check that new properties are not named same
        as existing attributes.
        """
        self.element.name = "foo"
        items = {"name": None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertTrue(result)

    def test_not_contains_reserved_property_name(self) -> None:
        """Reserved names are checked from any attributes in the instance
        after it is created.  Instance attributes are defaults from the
        specification.  We check that new properties are not named same
        as existing attributes.
        """
        items = {"name": None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertFalse(result)

    def test_reserved_names_check_disabled_with_option(self) -> None:
        """Reserved names are checked from any attributes in the instance
        after it is created.  Instance attributes are defaults from the
        specification.  We check that new properties are not named same
        as existing attributes.

        Check that passing an option will disable the check
        """
        pytmx.TiledElement.allow_duplicate_names = True
        self.element.name = "foo"
        items = {"name": None}
        result = self.element._contains_invalid_property_name(items.items())
        self.assertFalse(result)

    def test_repr(self) -> None:
        self.element.name = "foo"
        self.assertEqual('<TiledElement: "foo">', self.element.__repr__())
