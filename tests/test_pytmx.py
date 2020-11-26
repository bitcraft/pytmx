import dataclasses
from itertools import chain
from unittest import mock
import unittest

import objects
from pytmx import mason, objects


def make_mock(cls, **kwargs):
    """workaround for autspeccing failing on dataclasses"""
    fields = dataclasses.fields(cls)
    kwargs["spec_set"] = [f.name for f in fields]
    return mock.Mock(**kwargs)


class Testgetdefault(unittest.TestCase):
    d = {"key": "value", "int": "1"}

    def test_get_key(self):
        get = mason.getdefault(self.d)
        self.assertEqual(get("key"), "value")

    def test_get_missing_returns_default(self):
        get = mason.getdefault(self.d)
        self.assertEqual(get("not_key"), None)
        self.assertEqual(get("not_key", default="default"), "default")

    def test_get_convert_type(self):
        get = mason.getdefault(self.d)
        self.assertEqual(get("int", int), 1)

    def test_get_with_type_doesnt_convert_default(self):
        get = mason.getdefault(self.d)
        self.assertEqual(get("not_int", int, None), None)


class TestConvertToBool(unittest.TestCase):
    def test_string_true(self):
        self.assertTrue(mason.convert_to_bool("1"))
        self.assertTrue(mason.convert_to_bool("y"))
        self.assertTrue(mason.convert_to_bool("Y"))
        self.assertTrue(mason.convert_to_bool("t"))
        self.assertTrue(mason.convert_to_bool("T"))
        self.assertTrue(mason.convert_to_bool("yes"))
        self.assertTrue(mason.convert_to_bool("Yes"))
        self.assertTrue(mason.convert_to_bool("YES"))
        self.assertTrue(mason.convert_to_bool("true"))
        self.assertTrue(mason.convert_to_bool("True"))
        self.assertTrue(mason.convert_to_bool("TRUE"))

    def test_string_false(self):
        self.assertFalse(mason.convert_to_bool("0"))
        self.assertFalse(mason.convert_to_bool("n"))
        self.assertFalse(mason.convert_to_bool("N"))
        self.assertFalse(mason.convert_to_bool("f"))
        self.assertFalse(mason.convert_to_bool("F"))
        self.assertFalse(mason.convert_to_bool("no"))
        self.assertFalse(mason.convert_to_bool("No"))
        self.assertFalse(mason.convert_to_bool("NO"))
        self.assertFalse(mason.convert_to_bool("false"))
        self.assertFalse(mason.convert_to_bool("False"))
        self.assertFalse(mason.convert_to_bool("FALSE"))

    def test_number_true(self):
        self.assertTrue(mason.convert_to_bool(1))
        self.assertTrue(mason.convert_to_bool(1.0))

    def test_number_false(self):
        self.assertFalse(mason.convert_to_bool(0))
        self.assertFalse(mason.convert_to_bool(0.0))
        self.assertFalse(mason.convert_to_bool(-1))
        self.assertFalse(mason.convert_to_bool(-1.1))

    def test_bool_true(self):
        self.assertTrue(mason.convert_to_bool(True))

    def test_bool_false(self):
        self.assertFalse(mason.convert_to_bool(False))

    def test_bool_none(self):
        self.assertFalse(mason.convert_to_bool(None))

    def test_bool_empty(self):
        self.assertFalse(mason.convert_to_bool(""))

    def test_bool_whitespace_only(self):
        self.assertFalse(mason.convert_to_bool(" "))


class PointsTest(unittest.TestCase):
    def test_parse(self):
        result = mason.parse_points("-1.5,0 1,1.5 200.5,-1.5")
        self.assertIsInstance(result, list)
        self.assertEqual({type(i) for i in result}, {tuple})
        self.assertEqual({type(i) for i in chain.from_iterable(result)}, {float})
        self.assertEqual(result, [(-1.5, 0.0), (1.0, 1.5), (200.5, -1.5)])


class LayerDataTest(unittest.TestCase):
    def test_reshape(self):
        result = mason.reshape_data([1, 2, 3, 4, 5, 6], 3)
        self.assertEqual(result, [[1, 2, 3], [4, 5, 6]])

    def test_unpack_gids_csv(self):
        data = "1,2,3,4"
        result = mason.unpack_gids(data, encoding="csv", compression=None)
        self.assertEqual([1, 2, 3, 4], result)

    def test_unpack_gids_b64_uncompressed(self):
        data = "AQAAAAIAAAADAAAABAAAAA=="
        result = mason.unpack_gids(data, encoding="base64", compression=None)
        self.assertEqual([1, 2, 3, 4], result)

    def test_unpack_gids_b64_gzip(self):
        data = "H4sIAAAAAAAAA2NkYGBgAmJmIGYBYgDv1AWvEAAAAA=="
        result = mason.unpack_gids(data, encoding="base64", compression="gzip")
        self.assertEqual([1, 2, 3, 4], result)

    def test_unpack_gids_b64_zlib(self):
        data = "eJxjZGBgYAJiZiBmAWIAAGAACw=="
        result = mason.unpack_gids(data, encoding="base64", compression="zlib")
        self.assertEqual([1, 2, 3, 4], result)

    def test_unpack_gids_b64_unsupported(self):
        with self.assertRaises(mason.MasonException):
            mason.unpack_gids("", encoding="base64", compression="foo")

    def test_unpack_gids_unsupported_encoding(self):
        with self.assertRaises(mason.MasonException):
            mason.unpack_gids("", encoding="foo", compression="bar")

    def test_decode_gid_zero(self):
        gid, flags = mason.decode_gid(0)
        self.assertEqual(0, gid)
        self.assertEqual(False, flags.diagonal)
        self.assertEqual(False, flags.horizontal)
        self.assertEqual(False, flags.vertical)

    def test_decode_gid_hvd(self):
        gid, flags = mason.decode_gid(1)
        self.assertEqual(1, gid)
        self.assertEqual(False, flags.diagonal)
        self.assertEqual(False, flags.horizontal)
        self.assertEqual(False, flags.vertical)

    def test_decode_gid_hvD(self):
        gid, flags = mason.decode_gid(536870913)
        self.assertEqual(1, gid)
        self.assertEqual(False, flags.horizontal)
        self.assertEqual(False, flags.vertical)
        self.assertEqual(True, flags.diagonal)

    def test_decode_gid_hVd(self):
        gid, flags = mason.decode_gid(1073741825)
        self.assertEqual(1, gid)
        self.assertEqual(False, flags.horizontal)
        self.assertEqual(True, flags.vertical)
        self.assertEqual(False, flags.diagonal)

    def test_decode_gid_hVD(self):
        gid, flags = mason.decode_gid(1610612737)
        self.assertEqual(1, gid)
        self.assertEqual(False, flags.horizontal)
        self.assertEqual(True, flags.vertical)
        self.assertEqual(True, flags.diagonal)

    def test_decode_gid_Hvd(self):
        gid, flags = mason.decode_gid(2147483649)
        self.assertEqual(1, gid)
        self.assertEqual(True, flags.horizontal)
        self.assertEqual(False, flags.vertical)
        self.assertEqual(False, flags.diagonal)

    def test_decode_gid_HvD(self):
        gid, flags = mason.decode_gid(2684354561)
        self.assertEqual(1, gid)
        self.assertEqual(True, flags.horizontal)
        self.assertEqual(False, flags.vertical)
        self.assertEqual(True, flags.diagonal)

    def test_decode_gid_HVd(self):
        gid, flags = mason.decode_gid(3221225473)
        self.assertEqual(1, gid)
        self.assertEqual(True, flags.horizontal)
        self.assertEqual(True, flags.vertical)
        self.assertEqual(False, flags.diagonal)

    def test_decode_gid_HVD(self):
        gid, flags = mason.decode_gid(3758096385)
        self.assertEqual(1, gid)
        self.assertEqual(True, flags.horizontal)
        self.assertEqual(True, flags.vertical)
        self.assertEqual(True, flags.diagonal)


class TilesetImageTest(unittest.TestCase):
    def test_image_split_no_margin_no_spacing(self):
        result = list(mason.iter_image_tiles(8, 16, 4, 8, 0, 0))
        expected = [(0, 0, 4, 8), (4, 0, 4, 8), (0, 8, 4, 8), (4, 8, 4, 8)]
        self.assertEqual(expected, result)

    def test_image_split_no_margin_with_spacing(self):
        result = list(mason.iter_image_tiles(9, 17, 4, 8, 0, 1))
        expected = [(0, 0, 4, 8), (5, 0, 4, 8), (0, 9, 4, 8), (5, 9, 4, 8)]
        self.assertEqual(expected, result)

    def test_image_split_with_margin_no_spacing(self):
        result = list(mason.iter_image_tiles(10, 18, 4, 8, 1, 0))
        expected = [(1, 1, 4, 8), (5, 1, 4, 8), (1, 9, 4, 8), (5, 9, 4, 8)]
        self.assertEqual(expected, result)

    def test_image_split_with_margin_with_spacing(self):
        result = list(mason.iter_image_tiles(11, 19, 4, 8, 1, 1))
        expected = [(1, 1, 4, 8), (6, 1, 4, 8), (1, 10, 4, 8), (6, 10, 4, 8)]
        self.assertEqual(expected, result)


class NewObjectTest(unittest.TestCase):
    def setUp(self):
        self.ctx = make_mock(mason.Context)
        self.stack = mock.Mock()
        self.text = mock.Mock()

    def test_new_data(self):
        data = dict(encoding="ENCODING", compression="COMPRESSION")
        get = mason.getdefault(data)
        result = mason.new_data(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, mason.Data)
        self.assertEqual("ENCODING", result.encoding)
        self.assertEqual("COMPRESSION", result.compression)
        self.assertEqual(self.text, result.text)

    def test_new_ellipse(self):
        data = dict()
        get = mason.getdefault(data)
        result = mason.new_ellipse(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Circle)

    def test_new_grid(self):
        data = dict(orientation="ORIENTATION", width="1", height="2")
        get = mason.getdefault(data)
        result = mason.new_grid(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, mason.Grid)
        self.assertEqual("ORIENTATION", result.orientation)
        self.assertEqual(1, result.width)
        self.assertEqual(2, result.height)

    def test_new_group(self):
        data = dict(
            name="NAME",
            opacity="0.5",
            visible="1",
            tintcolor="TINTCOLOR",
            offsetx="1",
            offsety="2",
        )
        get = mason.getdefault(data)
        result = mason.new_group(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Group)
        self.assertEqual("NAME", result.name)
        self.assertEqual(0.5, result.opacity)
        self.assertEqual(True, result.visible)
        self.assertEqual("TINTCOLOR", result.tintcolor)
        self.assertEqual(1, result.offsetx)
        self.assertEqual(2, result.offsety)

    def test_new_image(self):
        data = dict(source="SOURCE", width="1", height="2", trans="TRANS",)
        get = mason.getdefault(data)
        result = mason.new_image(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Image)
        self.assertEqual("SOURCE", result.source)
        self.assertEqual(1, result.width)
        self.assertEqual(2, result.height)
        self.assertEqual("TRANS", result.trans)

    def test_new_imagelayer(self):
        data = dict(name="NAME", visible="1", image="IMAGE",)
        get = mason.getdefault(data)
        result = mason.new_imagelayer(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.ImageLayer)
        self.assertEqual("NAME", result.name)
        self.assertEqual(True, result.visible)
        self.assertEqual("IMAGE", result.image)

    def test_new_map(self):
        data = dict(
            version="VERSION",
            orientation="ORIENTATION",
            renderorder="RENDERORDER",
            compressionlevel="COMPRESSIONLEVEL",
            width="1",
            height="2",
            tilewidth="3",
            tileheight="4",
            hexsidelength="5",
            staggeraxis="6",
            staggerindex="7",
            backgroundcolor="BACKGROUND_COLOR",
            infinite="0",
        )
        self.ctx.path = "FILENAME"
        get = mason.getdefault(data)
        result = mason.new_map(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Map)
        self.assertEqual("VERSION", result.version)
        self.assertEqual("ORIENTATION", result.orientation)
        self.assertEqual("RENDERORDER", result.renderorder)
        self.assertEqual("COMPRESSIONLEVEL", result.compressionlevel)
        self.assertEqual(1, result.width)
        self.assertEqual(2, result.height)
        self.assertEqual(3, result.tilewidth)
        self.assertEqual(4, result.tileheight)
        self.assertEqual(5, result.hexsidelength)
        self.assertEqual(6, result.staggeraxis)
        self.assertEqual(7, result.staggerindex)
        self.assertEqual("BACKGROUND_COLOR", result.background_color)
        self.assertEqual(False, result.infinite)
        self.assertEqual("FILENAME", result.filename)

    def test_new_object(self):
        data = dict(
            name="NAME",
            type="TYPE",
            x="1",
            y="2",
            width="3",
            height="4",
            rotation="1.5",
            gid="1",
            visible="1",
        )
        get = mason.getdefault(data)
        result = mason.new_object(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Object)
        self.assertEqual("NAME", result.name)
        self.assertEqual("TYPE", result.type)
        self.assertEqual(1, result.x)
        self.assertEqual(2, result.y)
        self.assertEqual(3, result.width)
        self.assertEqual(4, result.height)
        self.assertEqual(1.5, result.rotation)
        self.assertEqual(1, result.gid)
        self.assertEqual(True, result.visible)

    def test_new_objectgroup(self):
        data = dict(
            name="NAME",
            color="COLOR",
            opacity="1.5",
            visible="0",
            tintcolor="TINTCOLOR",
            offsetx="2.5",
            offsety="3.5",
            draworder="DRAWORDER",
        )
        get = mason.getdefault(data)
        result = mason.new_objectgroup(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.ObjectGroup)
        self.assertEqual("NAME", result.name)
        self.assertEqual("COLOR", result.color)
        self.assertEqual(1.5, result.opacity)
        self.assertEqual(False, result.visible)
        self.assertEqual("TINTCOLOR", result.tintcolor)
        self.assertEqual(2.5, result.offsetx)
        self.assertEqual(3.5, result.offsety)
        self.assertEqual("DRAWORDER", result.draworder)

    def test_new_point(self):
        data = dict(x="1.5", y="2.5",)
        get = mason.getdefault(data)
        result = mason.new_point(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Point)
        self.assertEqual(1.5, result.x)
        self.assertEqual(2.5, result.y)
        self.assertEqual((1.5, 2.5), tuple(result))
        self.assertEqual(1.5, result[0])
        self.assertEqual(2.5, result[1])

    def test_new_polygon(self):
        data = dict(points="0,0 1,1 2,2")
        get = mason.getdefault(data)
        result = mason.new_polygon(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Polygon)
        self.assertEqual([(0, 0), (1, 1), (2, 2)], result.points)

    def test_new_polyline(self):
        data = dict(points="0,0 1,1 2,2")
        get = mason.getdefault(data)
        result = mason.new_polyline(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Polyline)
        self.assertEqual([(0, 0), (1, 1), (2, 2)], result.points)

    def test_new_properties(self):
        data = dict()
        get = mason.getdefault(data)
        result = mason.new_properties(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Properties)
        self.assertIsInstance(result.value, dict)
        self.assertEqual(dict(), result.value)

    def test_new_property(self):
        data = dict(name="NAME", type="TYPE", value="VALUE")
        get = mason.getdefault(data)
        result = mason.new_property(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Property)
        self.assertEqual("NAME", result.name)
        self.assertEqual("TYPE", result.type)
        self.assertEqual("VALUE", result.value)

    def test_new_text(self):
        data = dict(
            bold="BOLD",
            color="COLOR",
            fontfamily="FONTFAMILY",
            halign="HALIGN",
            italic="ITALIC",
            kerning="KERNING",
            pixelsize="PIXELSIZE",
            strikeout="STRIKEOUT",
            test=self.text,
            underline="UNDERLINE",
            valign="VALIGN",
            wrap="WRAP",
        )
        get = mason.getdefault(data)
        result = mason.new_text(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Text)
        self.assertEqual("BOLD", result.bold)
        self.assertEqual("COLOR", result.color)
        self.assertEqual("FONTFAMILY", result.fontfamily)
        self.assertEqual("HALIGN", result.halign)
        self.assertEqual("ITALIC", result.italic)
        self.assertEqual("KERNING", result.kerning)
        self.assertEqual("PIXELSIZE", result.pixelsize)
        self.assertEqual("STRIKEOUT", result.strikeout)
        self.assertEqual(self.text, result.text)
        self.assertEqual("UNDERLINE", result.underline)
        self.assertEqual("VALIGN", result.valign)
        self.assertEqual("WRAP", result.wrap)

    def test_new_tile(self):
        data = dict(id="1", gid="2", type="TYPE", terrain="TERRAIN", image="IMAGE")
        get = mason.getdefault(data)
        result = mason.new_tile(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Tile)
        self.assertEqual(1, result.id)
        self.assertEqual(2, result.gid)
        self.assertEqual("TYPE", result.type)
        self.assertEqual("TERRAIN", result.terrain)
        self.assertEqual("IMAGE", result.image)

    def test_new_tilelayer(self):
        data = dict(
            data="DATA",
            name="NAME",
            offsetx="1.5",
            offsety="2.5",
            opacity="3.5",
            tintcolor="TINTCOLOR",
            visible="0",
        )
        get = mason.getdefault(data)
        result = mason.new_tilelayer(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.TileLayer)
        self.assertEqual("DATA", result.data)
        self.assertEqual("NAME", result.name)
        self.assertEqual(1.5, result.offsetx)
        self.assertEqual(2.5, result.offsety)
        self.assertEqual(3.5, result.opacity)
        self.assertEqual(False, result.visible)

    def test_new_embedded_tileset(self):
        data = dict(
            columns="1",
            firstgid="2",
            margin="3",
            name="NAME",
            objectalignment="OBJECTALIGNMENT",
            source=None,
            spacing="4",
            tilecount="5",
            tileheight="6",
            tilewidth="7",
        )
        get = mason.getdefault(data)
        result = mason.new_tileset(self.ctx, self.stack, get, self.text)
        self.assertIsInstance(result, objects.Tileset)
        self.assertEqual(1, result.columns)
        self.assertEqual(2, result.firstgid)
        self.assertEqual(3, result.margin)
        self.assertEqual("NAME", result.name)
        self.assertEqual("OBJECTALIGNMENT", result.objectalignment)
        self.assertEqual(None, result.source)
        self.assertEqual(4, result.spacing)
        self.assertEqual(5, result.tilecount)
        self.assertEqual(6, result.tileheight)
        self.assertEqual(7, result.tilewidth)

    def test_new_external_tileset(self):
        data = dict(source="SOURCE",)
        self.ctx.firstgid = 1
        self.ctx.folder = "FOLDER"
        get = mason.getdefault(data)
        with mock.patch("pytmx.mason.parse_tmxdata") as mock_parse:
            result = mason.new_tileset(self.ctx, self.stack, get, self.text)
        self.assertEqual(mock_parse(self.ctx, "FOLDER/SOURCE"), result)
        self.assertEqual(1, self.ctx.firstgid)


class OpertionsTest(unittest.TestCase):
    def setUp(self):
        self.ctx = make_mock(mason.Context)
        self.ctx.tiles = dict()
        self.ctx.firstgid = 1
        self.ctx.folder = "FOLDER"
        self.stack = mock.Mock()
        self.text = mock.Mock()
        self.parent = mock.Mock()
        self.child = mock.Mock()

    def call(self, func):
        func(self.ctx, self.stack, self.parent, self.child)

    def test_add_layer(self):
        self.parent = make_mock(objects.Map, layers=list())
        self.call(mason.add_layer)
        self.assertIn(self.child, self.parent.layers)

    def test_add_object_no_gid(self):
        self.parent = make_mock(objects.ObjectGroup, objects=list())
        self.child.gid = None
        self.call(mason.add_object)
        self.assertIn(self.child, self.parent.objects)

    def test_add_object_with_gid(self):
        self.parent = make_mock(objects.ObjectGroup, objects=list())
        self.child.gid = 1
        self.ctx.tiles[1] = mock.Mock()
        self.call(mason.add_object)
        self.assertIn(self.child, self.parent.objects)
        self.assertEqual(self.ctx.tiles[1].image, self.child.image)

    def test_add_objectgroup_to_tile(self):
        self.parent = make_mock(objects.Tile)
        self.child = make_mock(objects.ObjectGroup)
        self.call(mason.add_objectgroup_to_tile)
        self.assertEqual(self.parent.collider_group, self.child)

    def test_add_shape(self):
        pass

    def test_add_tile_to_tileset_no_firstgid(self):
        self.parent = make_mock(objects.Tileset, firstgid=None)
        self.child = make_mock(objects.Tile, id=1)
        self.call(mason.add_tile_to_tileset)
        self.assertIs(self.ctx.tiles[2], self.child)
        self.assertEqual(self.ctx.firstgid, self.parent.firstgid)

    def test_add_tile_to_tileset_with_firstgid(self):
        self.parent = make_mock(objects.Tileset, firstgid=1)
        self.child = make_mock(objects.Tile, id=1)
        self.call(mason.add_tile_to_tileset)
        self.assertIs(self.ctx.tiles[2], self.child)

    def test_add_to_group(self):
        self.parent = make_mock(objects.Group, layers=list())
        self.call(mason.add_to_group)
        self.assertIn(self.child, self.parent.layers)

    def test_copy_attribute(self):
        func = mason.copy_attribute("foo")
        self.child.foo = "bar"
        self.call(func)
        self.assertEqual(self.parent.foo, self.child.foo)

    def test_exception(self):
        func = mason.exception("foo")
        with self.assertRaises(mason.MasonException):
            self.call(func)

    def test_finalize_map(self):
        self.fail("unfinished api")

    def test_load_tileset(self):
        self.parent = make_mock(objects.Tileset, firstgid=1)
        self.child = make_mock(objects.Image)
        self.call(mason.load_tileset)
        self.fail("unfinished api")
