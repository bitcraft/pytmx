# encoding: utf-8
"""
Mason: a fast library to read Tiled TMX files.

For python 2.7 and python 3.3+
Supports all major features to version 1.1.0

* Embedded images are supported

Mason is designed to read Tiled TMX files and
prepare them for easy use for games.
"""
from __future__ import absolute_import, division, print_function

import logging
import array
import struct
from unittest import TestCase
from collections import defaultdict, namedtuple

import six

# required for python versions < 3.3
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

__version__ = (3, 22, 0)
logger = logging.getLogger(__name__)

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29

# error message format strings go here
duplicate_name_fmt = 'Cannot set user {} property on {} "{}"; Tiled property already exists.'

flag_names = (
    'flipped_horizontally',
    'flipped_vertically',
    'flipped_diagonally',)

TileFlags = namedtuple('TileFlags', flag_names)
AnimationFrame = namedtuple('AnimationFrame', ['gid', 'duration'])


class MissingDecoderError(Exception):
    pass


class MissingDecompressorError(Exception):
    pass


class UnsupportedTilesetError(Exception):
    pass


def convert_to_bool(text):
    """ Convert a few common variations of "true" and "false" to boolean

    :param text: string to test
    :return: boolean
    :raises: ValueError
    """
    try:
        return bool(int(text))
    except:
        pass

    text = str(text).lower()
    if text == "true":
        return True
    if text == "yes":
        return True
    if text == "false":
        return False
    if text == "no":
        return False

    raise ValueError


types = defaultdict(lambda: six.u)

_str = six.u
types.update({
    "format": str,
    "trans": _str,
    "tile": int,
    "tileid": int,
    "duration": int,
    "color": str,
    "id": int,
    "opacity": float,
    "visible": convert_to_bool,
    "offsetx": int,
    "offsety": int,
    "draworder": str,
    "points": str,
    "fontfamily": str,
    "pixelsize": float,
    "wrap": convert_to_bool,
    "bold": convert_to_bool,
    "italic": convert_to_bool,
    "underline": convert_to_bool,
    "strikeout": convert_to_bool,
    "kerning": convert_to_bool,
    "halign": str,
    "valign": str,
    "gid": int,
    "type": _str,
    "x": float,
    "y": float,
    "value": _str,
    "rotation": float,
})

# casting for properties type
prop_type = {
    'string': str,
    'int': int,
    'float': float,
    'bool': bool,
    'color': str,
    'file': str
}

stack = list()
TiledMap = namedtuple('TiledMap', 'beans')


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
    return map(int, "".join(i.strip() for i in data.strip()).split(","))


decompressors = {
    'gzip': decompress_gzip,
    'zlib': decompress_zlib
}

decoders = {
    'base64': decode_base64,
    'csv': decode_csv
}


def get_data_thing(xform_name, exception):
    def func(element):
        xform = element.get(xform_name, None)
        if xform:
            choocher = decoders.get(xform)
            if choocher is None:
                raise exception(xform)
            return choocher(element.text)

    return func


decompress = get_data_thing('compression', MissingDecompressorError)
decode = get_data_thing('encoding', MissingDecoderError)


def unpack(element):
    """ Decode and decompress level tile data

    :param element:
    :return:
    """
    raw_data = None

    # encoding ===========================================================
    temp = decode(element)
    if temp is not None:
        raw_data = temp

    # compression ========================================================
    temp = decompress(element)
    if temp is not None:
        raw_data = temp

    if raw_data is None:
        raise Exception

    return raw_data


def decode_gid(raw_gid):
    """ Decode a GID from TMX data

    as of 0.7.0 it determines if the tile should be flipped when rendered
    as of 0.8.0 bit 30 determines if GID is rotated

    :param raw_gid: 32-bit number from TMX layer data
    :return: gid, flags
    """
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT)
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid


def cast(element, types):
    return {key: types[key](value) for key, value in element.items()}


class Processor(object):
    def start(self, element, stack):
        """
        :type element: xml.etree.ElementTree.Element
        :type stack: list
        :return:
        """
        pass

    def end(self, element, stack):
        """
        :type element: xml.etree.ElementTree.Element
        :type stack: list
        :return:
        """


class ProcessProperty(Processor):
    def start(self, element, stack):
        """
        :type element: xml.etree.ElementTree.Element
        :type stack: list
        :return:
        """
        _type = element.get('type')
        if _type:
            _type = prop_type[_type]
            value = _type(element.get('value'))
        else:
            value = element.get('value')
        return {element.get('name'): value}


class ProcessProperties(Processor):
    def start(self, element, stack):
        pass

    def add_property(self):
        pass


class ProcessImage(Processor):
    types = {
        'format': str,
        'source': str,
        'trans': str,
        'width': int,
        'height': int,
    }

    def start(self, element, stack):
        return element.attrib


class ProcessTile(Processor):
    types = {
        'id': int,
        'type': str,
        'terrain': str,
        'probability': float,
    }

    def start(self, element, stack):
        return cast(element, self.types)


class ProcessTileset(Processor):
    types = {
        "firstgid": int,
        "source": str,
        "name": str,
        "tilewidth": int,
        "tileheight": int,
        "spacing": int,
        "margin": int,
        "tilecount": int,
        "columns": int,
    }

    def start(self, element, stack):
        """
        :type element: xml.etree.ElementTree.Element
        :type stack: list
        :return:
        """
        attrib = cast(element, self.types)


class ProcessTilesetSource(Processor):
    def start(self, element, stack):
        if source[-4:].lower() == ".tsx":

            # external tilesets don't save this, store it for later
            self.firstgid = int(element.get('firstgid'))

            # we need to mangle the path - tiled stores relative paths
            dirname = os.path.dirname(self.parent.filename)
            path = os.path.abspath(os.path.join(dirname, source))
            try:
                element = ElementTree.parse(path).getroot()
            except IOError:
                msg = "Cannot load external tileset: {0}"
                logger.error(msg.format(path))
                raise Exception

        else:
            msg = "Found external tileset, but cannot handle type: {0}"
            logger.error(msg.format(self.source))
            raise UnsupportedTilesetError


class ProcessOffset(Processor):
    types = {
        'x': int,
        'y': int,
    }

    def end(self, element, stack):
        return cast(element, self.types)


class ProcessData(Processor):
    types = {
        'encoding': str,
        'compression': str
    }

    def end(self, element, stack):
        # decode and decompress data
        data = unpack(element)

        # unpack into list of 32-bit integers
        fmt = struct.Struct('<L')
        every_4 = range(0, len(data), 4)
        gids = [decode_gid(fmt.unpack_from(data, i)[0]) for i in every_4]

        # get layer info from the stack
        layer_data = stack[-2][2]
        width, height = layer_data['width'], layer_data['height']

        # split data into several arrays
        return tuple(array.array('H', gids[i * width:i * width + width]) for i in range(height))


class ProcessLayer(Processor):
    types = {
        "name": str,
        "width": int,
        "height": int,
        "opacity": float,
        "visible": bool,
        "offsetx": int,
        "offsety": int,
    }

    def start(self, element, stack):
        data = {}
        for key, value in element.items():
            data[key] = self.types[key](value)
        return data


class ProcessPolygon(Processor):
    def start(self, element, stack):
        pass


class ProcessObject(Processor):
    def start(self, element, stack):
        pass


class ProcessPolyline(Processor):
    def start(self, element, stack):
        pass


class ProcessObjectgroup(Processor):
    def start(self, element, stack):
        pass


class ProcessImagelayer(Processor):
    types = {
        'name': str,
        'offsetx': int,
        'offsety': int,
        'opacity': float,
        'visbile': bool
    }

    def start(self, element, stack):
        pass


class ProcessMap(Processor):
    types = {
        "version": str,
        "tiledversion": str,
        "orientation": _str,
        "renderorder": str,
        "width": int,
        "height": int,
        "tilewidth": int,
        "tileheight": int,
        "hexsidelength": float,
        "staggeraxis": str,
        "staggerindex": str,
        "backgroundcolor": str,
        "nextobjectid": int,
    }

    def start(self, element, stack):
        data = {}
        for key, value in element.items():
            data[key] = self.types[key](value)
        return data


class ProcessAnimation(Processor):
    def start(self, element, stack):
        pass


class ProcessChunk(Processor):
    def start(self, element, stack):
        pass


class ProcessFrame(Processor):
    types = {
        'tileid': int,
        'duration': int,
    }

    def start(self, element, stack):
        return cast(element, self.types)


class ProcessGroup(Processor):
    def start(self, element, stack):
        pass


class ProcessEllipse(Processor):
    def start(self, element, stack):
        pass


class ProcessTerrain(Processor):
    def start(self, element, stack):
        pass


class ProcessTerraintypes(Processor):
    def start(self, element, stack):
        pass


class ProcessTemplate(Processor):
    def start(self, element, stack):
        pass


class ProcessText(Processor):
    def start(self, element, stack):
        pass


class ProcessTileoffset(Processor):
    def start(self, element, stack):
        pass


handled = [
    'animation',
    'chunk',
    'data',
    'frame',
    'ellipse',
    'group',
    'image',
    'imagelayer',
    'layer',
    'map',
    'object',
    'objectgroup',
    'polygon',
    'polyline',
    'properties',
    'property',
    'template',
    'terrain',
    'terraintypes',
    'text',
    'tile',
    'tileoffset',
    'tileset',
    # 'wangcolorcorner',
    # 'wangedgecolor',
    # 'wangset',
    # 'wangsets',
    # 'wangtile',
]

handlers = {i: globals()['Process' + i.title()]() for i in handled}
print(handlers.keys())


def slurp(filename):
    root = defaultdict(list)
    sem = 0
    flags = 0
    stack.append((None, None, None))

    for event, element in ElementTree.iterparse(filename, events=('start', 'end')):

        try:
            h = globals()['Process' + element.tag.title()]()

        except KeyError:
            raise

        if event == 'start':
            sem += 1

            v = h.start(element, stack)
            # print('{}\t{}:\t\t{}'.format(event, element.tag, v))

            # insert into stack
            stack.append((element.tag, element, v, h))

        elif event == 'end':
            sem -= 1

            # close it up
            h.end(element, stack)

            # free memory from the element
            element.clear()

            # remove from stack
            stack.pop()

            parent = stack[-1][1]
            if parent:
                try:
                    parent = parent[-1]
                    func = getattr(parent, 'add_' + element.tag)
                except AttributeError:
                    print(parent)
                    raise
                func(element)

        print("=" * 80)
        print(sem, element.tag, flags)
        print([i[0] for i in stack])
        print()

    print(stack)
    import pprint
    pprint.pprint(dict(root))


class TestCase2(TestCase):
    def test_init(self):
        slurp('../apps/data/0.9.1/formosa-base64.tmx')
