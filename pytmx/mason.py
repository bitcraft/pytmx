# encoding: utf-8
"""
Mason: a fast library to read Tiled TMX files.

For python 2.7 and python 3.3+
Supports all major features to version 1.1.0

* TMX and JSON parsing
* Embedded images are supported

Mason is designed to read Tiled TMX files and prepare them for easy use for games.

This file uses a template to generate the library for map loading.
"""
from __future__ import absolute_import, division, print_function

import logging
import struct
from collections import deque, namedtuple
from itertools import product
from unittest import TestCase

import os

import array
import six

__version__ = (3, 22, 0)
target_version = '1.1.0'
logger = logging.getLogger(__name__)

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29

flag_names = (
    'flipped_horizontally',
    'flipped_vertically',
    'flipped_diagonally',)

TileFlags = namedtuple('TileFlags', flag_names)
AnimationFrame = namedtuple('AnimationFrame', ('gid', 'duration'))
Attr = namedtuple('Attribute', ('name', 'klass', 'default', 'comment'))

Visible = Attr('visible', bool, True, 'visible, or not')
Opacity = Attr('opacity', float, 1.0, 'opacity')
Color = Attr('color', str, None, 'color of the thing')


class MissingDecoderError(Exception):
    pass


class MissingDecompressorError(Exception):
    pass


class UnsupportedFeature(Exception):
    pass


# casting for properties types
tiled_property_type = {
    'string': str,
    'int': int,
    'float': float,
    'bool': bool,
    'color': str,
    'file': str
}


def default_image_loader(filename, flags, **kwargs):
    """ This default image loader just returns filename, rect, and any flags
    """

    def load(rect=None, flags=None):
        return filename, rect, flags

    return load


def noop(arg):
    return arg


def decompress_zlib(data):
    import zlib
    return zlib.decompress(data)


def decompress_gzip(data):
    import gzip
    with gzip.GzipFile(fileobj=six.BytesIO(data)) as fh:
        return fh.read()


def decode_base64(data):
    from base64 import b64decode
    return b64decode(data.strip())


def decode_csv(data):
    return map(int, ''.join(i.strip() for i in data.strip()).split(','))


def unpack(data, encoding, compression):
    """ Decode and decompress level tile data

    :return:
    """
    for func, arg in [(decode, encoding),
                      (decompress, compression)]:
        temp = func(data, arg)
        if temp is not None:
            data = temp
    return data


def get_datathing(prefix, exception):
    def func(data, xform):
        if xform:
            try:
                xformer = globals()[prefix + xform]
            except KeyError:
                raise exception(xform)
            return xformer(data)

    return func


decompress = get_datathing('decompress_', MissingDecompressorError)
decode = get_datathing('decode_', MissingDecoderError)


def unroll_layer_data(data):
    fmt = struct.Struct('<L')
    every_4 = range(0, len(data), 4)
    return [decode_gid(fmt.unpack_from(data, i)[0]) for i in every_4]


def rowify(gids, w, h):
    return tuple(array.array('H', gids[i * w:i * w + w]) for i in range(h))


def read_points(text):
    """parse a text string of float tuples and return [(x,...),...]
    """
    return tuple(tuple(map(float, i.split(','))) for i in text.split())


def move_points(points, x, y):
    return tuple((i[0] + x, i[1] + y) for i in points)


def calc_bounds(points):
    x1 = x2 = y1 = y2 = 0
    for x, y in points:
        if x < x1: x1 = x
        if x > x2: x2 = x
        if y < y1: y1 = y
        if y > y2: y2 = y
    return abs(x1) + abs(x2), abs(y1) + abs(y2)


def decode_gid(raw_gid):
    """ Decode a GID from TMX data

    as of 0.7.0 it determines if the tile should be flipped when rendered
    as of 0.8.0 bit 30 determines if GID is rotated

    :param raw_gid: 32-bit number from TMX layer data
    :return: gid, flags
    """
    flags = TileFlags(raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
                      raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
                      raw_gid & GID_TRANS_ROT == GID_TRANS_ROT)
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid


class Dummy(object):
    def __init__(self, attrib, properties):
        self.properties = properties
        self.attrib = attrib
        for key, value in attrib.items():
            setattr(self, key, value)


class TokenMeta(type):
    def __init__(cls, name, bases, dct):
        attr = dct.get('attributes', [])
        cls.attrib_types = {item.name: item for item in attr}
        super(TokenMeta, cls).__init__(name, bases, dct)


class Token(object):
    __metaclass__ = TokenMeta

    def __init__(self):
        self.attrib = dict()
        self.properties = dict()

    def __getattr__(self, name):
        try:
            return self.attrib[name]
        except KeyError:
            raise AttributeError

    def start(self, init, context):
        """

        :type init: dict
        :type context: dict
        :return: None
        """
        attrib = dict()
        self.attrib = attrib

        # check the defaults
        for key, value in self.attrib_types.items():
            try:
                raw_value = init[key]
            except KeyError:
                raw_value = value.default

            attrib[key] = raw_value

        # cast values to their type
        for key, value in attrib.items():
            if value is not None:
                attrib[key] = self.attrib_types[key].klass(value)

    def end(self, content, context):
        """
        :type content: str
        :type context: dict
        :return: Processor
        """
        pass

    def combine(self, child, tag):
        try:
            func = getattr(self, 'add_' + tag)
        except AttributeError:
            raise UnsupportedFeature(tag)
        func(child)

    def add_properties(self, item):
        self.properties = item.dictionary


class AnimationToken(Token):
    # No attributes defined

    def __init__(self):
        super(AnimationToken, self).__init__()
        self.frames = list()

    def add_frame(self, item):
        self.frames.append(item)


class ChunkToken(Token):
    attributes = (
        Attr('x', int, None, 'x tile coord of chunk'),
        Attr('y', int, None, 'y tile coord of chunk'),
        Attr('width', int, None, 'tile width of chunk'),
        Attr('height', int, None, 'x tile height of chunk'),
    )


class DataToken(Token):
    """ TILE DATA """
    attributes = (
        Attr('encoding', str, None, 'base64, csv, None'),
        Attr('compression', str, None, 'gzip, zip, None', )
    )

    def __init__(self):
        super(DataToken, self).__init__()
        self.tiles = list()
        self.chunks = list()
        self.data = None

    def end(self, content, context):
        # get map dimension info from the parent
        parent = context['parent']
        w, h = parent.width, parent.height

        # the content must be stripped before testing because
        # it may be a just a bunch of whitespace.
        # only the content will contain encoded/compressed tile data.
        if content.strip():
            # 1. unpack into list of 32-bit integers
            # 2. split data into several arrays, one per row
            data = unpack(content, self.encoding, self.compression)
            self.data = rowify(unroll_layer_data(data), w, h)

        # if for some reason tile elements are used
        elif self.tiles:
            self.data = rowify([i.gid for i in self.tiles], w, h)

        else:
            raise Exception('no layer data?')

    def add_tile(self, item):
        self.tiles.append(item)

    def add_chunk(self, item):
        self.chunks.append(item)


class EllipseToken(Token):
    """ No attributes defined """
    pass


class FrameToken(Token):
    attributes = (
        Attr('tileid', int, None, 'gid'),
        Attr('duration', int, None, 'duration in milliseconds'),
    )


class GroupToken(Token):
    attributes = (
        Attr('name', str, None, 'name of group'),
        Attr('offsetx', int, 0, 'pixel offset, applied to all descendants'),
        Attr('offsety', int, 0, 'pixel offset, applied to all descendants'),
        Visible, Opacity
    )


class ImageToken(Token):
    attributes = (
        Attr('format', str, None, 'png, jpg, etc'),
        Attr('source', str, None, 'path, relative to the map'),
        Attr('trans', str, None, 'transparent color'),
        Attr('width', int, None, 'pixel width, optional'),
        Attr('height', int, None, 'pixel height, optional'),
    )

    def end(self, content, context):
        loader_class = context['image_loader']
        loader = loader_class(self.source, None)
        self.image = loader()

    def add_data(self, item):
        # data is used to load image into memory.  uses ImageToken.format
        raise NotImplementedError


class ImagelayerToken(Token):
    attributes = (
        Attr('name', str, 'ImageLayer', 'name of layer'),
        Attr('offsetx', int, 0, 'not used, per spec.'),
        Attr('offsety', int, 0, 'not used, per spec.'),
        Visible, Opacity
    )

    def __init__(self):
        super(ImagelayerToken, self).__init__()
        self.image = None

    def add_image(self, item):
        self.image = item


class LayerToken(Token):
    """ TILE LAYER """
    attributes = (
        Attr('name', str, 'TileLayer', 'name of layer'),
        Attr('width', int, None, 'tile width'),
        Attr('height', int, None, 'tile height'),
        Attr('offsetx', int, 0, 'Not used, per spec'),
        Attr('offsety', int, 0, 'Not used, per spec'),
        Visible, Opacity
    )

    def __init__(self):
        super(LayerToken, self).__init__()
        self.data = None

    def add_data(self, data):
        self.data = data


class MapToken(Token):
    attributes = (
        Attr('version', str, None, 'TMX format version'),
        Attr('tiledversion', str, None, 'software version'),
        Attr('orientation', str, 'orthogonal', 'map orientation'),
        Attr('renderorder', str, 'right-down', 'order of tiles to be drawn'),
        Attr('width', int, None, 'tile width'),
        Attr('height', int, None, 'tile height'),
        Attr('tilewidth', int, None, 'pixel width of tile'),
        Attr('tileheight', int, None, 'pixel height of tile'),
        Attr('hexsidelength', float, None, 'length of hex tile edge'),
        Attr('staggeraxis', str, None, '[hex] x/y axis is staggered'),
        Attr('staggerindex', str, None, '[hex] even/odd staggered axis'),
        Attr('backgroundcolor', str, None, 'background color of map'),
        Attr('nextobjectid', int, None, 'the next gid available to use'),
    )

    def __init__(self):
        super(MapToken, self).__init__()
        self.tilesets = list()
        self.layers = list()

    def add_tileset(self, item):
        self.tilesets.append(item)

    def add_layer(self, item):
        self.layers.append(item)

    def add_(self, item):
        self.layers.append(item)

    def add_imagelayer(self, item):
        self.layers.append(item)


class ObjectToken(Token):
    attributes = (
        Attr('name', str, None, 'name of object'),
        Attr('id', int, None, 'unique id assigned to object'),
        Attr('type', str, None, 'defined by editor'),
        Attr('x', float, None, 'tile x coordinate'),
        Attr('y', float, None, 'tile y coordinate'),
        Attr('width', float, None, 'pixel widht'),
        Attr('height', float, None, 'pixel height'),
        Attr('rotation', float, 0, 'rotation'),
        Attr('gid', int, None, 'reference a tile id'),
        Attr('template', str, None, 'path, optional'),
        Visible, Opacity
    )

    def __init__(self):
        super(ObjectToken, self).__init__()
        self.points = list()
        self.ellipse = False

    def add_ellipse(self, item):
        self.ellipse = True

    def add_polygon(self, item):
        self.points = move_points(item.points, self.x, self.y)
        self.attrib['closed'] = True

    def add_polyline(self, item):
        self.points = move_points(item.points, self.x, self.y)
        self.attrib['closed'] = False


class ObjectgroupToken(Token):
    attributes = (
        Attr('name', str, None, 'name of group'),
        Attr('x', float, 0, 'not used, per spec'),
        Attr('y', float, 0, 'not used, per spec'),
        Attr('width', int, None, 'not used, per spec'),
        Attr('height', int, None, 'not used, per spec'),
        Color, Visible, Opacity
    )

    def __init__(self):
        super(ObjectgroupToken, self).__init__()
        self.objects = list()

    def add_object(self, item):
        self.objects.append(item)


class PointToken(Token):
    # No attributes defined
    pass


class PolygonToken(Token):
    attributes = (
        Attr('points', read_points, None, 'coordinates of the polygon'),
    )


class PolylineToken(Token):
    attributes = (
        Attr('points', read_points, None, 'coordinates of the polyline'),
    )


class PropertiesToken(Token):
    def __init__(self):
        super(PropertiesToken, self).__init__()
        self.dictionary = dict()

    def add_property(self, item):
        self.dictionary[item.name] = item.value


class PropertyToken(Token):
    attributes = (
        Attr('type', noop, None, ''),
        Attr('name', noop, None, ''),
        Attr('value', noop, None, ''),
    )

    def __init__(self):
        super(PropertyToken, self).__init__()

    def start(self, init, context):
        super(PropertyToken, self).start(init, context)
        try:
            _type = tiled_property_type[init['type']]
            self.attrib['value'] = _type(init['value'])
        except KeyError:
            self.attrib['value'] = init['value']


class TemplateToken(Token):
    pass


class TerrainToken(Token):
    pass


class TerraintypesToken(Token):
    pass


class TextToken(Token):
    pass


class TileToken(Token):
    attributes = (
        Attr('id', int, None, ''),
        Attr('gid', int, None, 'global id'),
        Attr('type', str, None, 'defined in editor'),
        Attr('terrain', str, None, ''),
        Attr('probability', float, None, ''),
    )

    def __init__(self):
        super(TileToken, self).__init__()
        self.image = None

    def add_image(self, item):
        self.image = item


class TileoffsetToken(Token):
    attributes = (
        Attr('x', int, None, 'horizontal (left) tile offset'),
        Attr('y', int, None, 'vertical (down) tile offset'),
    )


class TilesetToken(Token):
    attributes = (
        Attr('firstgid', int, None, ''),
        Attr('source', str, None, ''),
        Attr('name', str, None, ''),
        Attr('tilewidth', int, None, ''),
        Attr('tileheight', int, None, ''),
        Attr('spacing', int, 0, 'pixels between each tile'),
        Attr('margin', int, 0, 'pixels between tile and image edge'),
        Attr('tilecount', int, None, ''),
        Attr('columns', int, None, ''),
    )

    def __init__(self):
        super(TilesetToken, self).__init__()
        self.image = None
        self.tiles = list()

    def end(self, content, context):
        super(TilesetToken, self).end(content, context)
        if self.source is None:
            self.load_tiles(content, context)

    def load_tiles(self, content, context):
        tw, th = self.tilewidth, self.tileheight

        width = self.image.width
        height = self.image.height

        p = product(range(self.margin, height + self.margin - th + 1, th + self.spacing),
                    range(self.margin, width + self.margin - tw + 1, tw + self.spacing))

        path = self.image.source
        loader_class = context['image_loader']
        loader = loader_class(path, None, colorkey=self.image.trans)

        # iterate through the tiles
        for gid, (y, x) in enumerate(p, self.firstgid):
            flags = None
            image = loader((x, y, tw, th), flags)

    def add_image(self, image):
        self.image = image

    def add_tile(self, tile):
        self.tiles.append(tile)


class TilesetSourceToken(Token):
    def end(self, content, context):
        if source[-4:].lower() == '.tsx':

            # external tilesets don't save this, store it for later
            self.firstgid = int(content.get('firstgid'))

            # we need to mangle the path - tiled stores relative paths
            dirname = os.path.dirname(self.parent.filename)
            path = os.path.abspath(os.path.join(dirname, source))
            try:
                content = ElementTree.parse(path).getroot()
            except IOError:
                msg = 'Cannot load external tileset: {0}'
                logger.error(msg.format(path))
                raise Exception

        else:
            msg = 'Found external tileset, but cannot handle type: {0}'
            logger.error(msg.format(self.source))
            raise UnsupportedFeature(self.source)


def get_processor(feature):
    try:
        return globals()[feature + 'Token']()
    except KeyError:
        raise UnsupportedFeature(feature)


def load_tmx(path):
    # required for python versions < 3.3
    try:
        from xml.etree import cElementTree as ElementTree
    except ImportError:
        from xml.etree import ElementTree

    root = ElementTree.iterparse(path, events=('start', 'end'))

    for event, element in root:
        yield event, element.tag.title(), element.attrib, element.text
        if event == 'end':
            element.clear()


def load_json(path):
    import json

    with open(path) as fp:
        root = json.load(fp)

    yield 'start', 'Map', root, None
    for key, value in root.items():
        yield 'start', key, value, None
        yield 'end', key, value, None
    yield 'end', 'Map', root, None


def get_loader(path):
    name, ext = os.path.splitext(path.lower())
    try:
        func = globals()['load_' + ext[1:]]
        return func(path)
    except KeyError:
        raise UnsupportedFeature(ext)


def write_codegen(name, func, fp):
    attrib = globals()[name].attrib_types

    if func == '__init__':
        kwargs = sorted(attrib)
        kwargs_str = ''.join([', {}=None'.format(i) for i in kwargs])
        fp.write('    def __init__(self{}):\n\n'.format(kwargs_str))

    elif func == 'attributes':
        fp.write('        # Attributes, as of Tiled {}\n'.format(target_version))
        for kwarg, info in sorted(attrib.items()):
            fp.write('        self.{0} = {0}  # {1}\n'.format(kwarg, info.comment))


def write_pytmx(in_file, out_file):
    for raw_line in in_file:
        line = raw_line.strip()
        if line.startswith('# codegen:'):
            head, tail = line.split(': ')
            name, func = tail.split('.')
            write_codegen(name, func, out_file)
        else:
            out_file.write(raw_line)


def slurp(path):
    stack = deque([None])
    token = None

    context = {
        'image_loader': default_image_loader,
        'path_root': os.path.dirname(path),
        'parent': None,
        'stack': stack
    }

    for event, tag, attrib, text in get_loader(path):
        if event == 'start':
            token = get_processor(tag)
            token.start(attrib, context)
            stack.append(token)

        elif event == 'end':
            token = stack.pop()
            parent = stack[-1]
            context['parent'] = parent
            token.end(text, context)
            if parent:
                parent.combine(token, tag.lower())

    from pytmx import TiledMap

    return TiledMap(token)


class TestCase2(TestCase):
    def test_init(self):
        # import glob
        # for filename in glob.glob('../apps/data/0.9.1/*tmx'):
        #     print(filename)
        #     token = slurp(filename)
        #     pprint.pprint((token, token.properties))

        with open('pytmx_template.py') as in_file:
            with open('pytmx.py', 'w') as out_file:
                write_pytmx(in_file, out_file)

