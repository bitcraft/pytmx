import itertools
import tempfile
import unittest
from pathlib import Path

import pytmx
from pytmx import TiledElement, convert_to_bool
from pytmx.pytmx import decode_gid


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


class TestGidFlags(unittest.TestCase):
    def test_decode_all_flag_combinations(self):
        for flags in itertools.product((False, True), repeat=4):
            encoded_flags = sum(int(value) << (31 - i) for i, value in enumerate(flags))
            for gid in (0, 1, 0x0FFFFFFF):
                with self.subTest(flags=flags, gid=gid):
                    decoded, transform = decode_gid(gid | encoded_flags)
                    self.assertEqual(decoded, gid)
                    self.assertEqual(tuple(transform), flags[:3])

    def test_registration_ignores_hexagonal_rotation_bit(self):
        map_ = pytmx.TiledMap()
        for flags in itertools.product((False, True), repeat=3):
            raw_gid = 1 | sum(int(value) << (31 - i) for i, value in enumerate(flags))
            with self.subTest(flags=flags):
                original = map_.register_gid_check_flags(raw_gid)
                ignored = map_.register_gid_check_flags(raw_gid | 0x10000000)
                self.assertEqual(ignored, original)
                self.assertEqual(map_.tiledgidmap[ignored], 1)

    def test_flagged_layer_and_object_images(self):
        gids = [1 | (combination << 28) for combination in range(16)]
        objects = "".join(
            '<object id="{}" gid="{}" x="0" y="16" width="16" height="16"/>'.format(
                i + 1, gid
            )
            for i, gid in enumerate(gids)
        )
        document = """<map orientation="orthogonal" width="16" height="1" tilewidth="16" tileheight="16">
          <tileset firstgid="1" name="tiles" tilewidth="16" tileheight="16" tilecount="1" columns="1">
            <image source="tile.png" width="16" height="16"/>
          </tileset>
          <layer name="tiles" width="16" height="1"><data encoding="csv">{}</data></layer>
          <objectgroup name="objects">{}</objectgroup>
        </map>""".format(
            ",".join(str(gid) for gid in gids), objects
        )
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "map.tmx"
            filename.write_text(document, encoding="utf-8")
            # The default loader returns image references without opening pixels.
            map_ = pytmx.TiledMap(str(filename))
            objects = list(map_.objects)
            for i, raw_gid in enumerate(gids):
                with self.subTest(raw_gid=raw_gid):
                    gid = map_.layers[0].data[0][i]
                    image = map_.get_tile_image_by_gid(gid)
                    self.assertIsNotNone(image)
                    self.assertEqual(map_.tiledgidmap[gid], 1)
                    self.assertEqual(objects[i].gid, gid)
                    self.assertEqual(map_.get_tile_image_by_gid(objects[i].gid), image)
                    self.assertEqual(gid, map_.layers[0].data[0][i ^ 1])
