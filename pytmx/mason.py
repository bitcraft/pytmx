# encoding: utf-8
"""
Mason: a fast library to read Tiled TMX files.

For python 2.7 and python 3.3+
Supports all major features to version 1.1.0

* Embedded images are supported

Mason is designed to read Tiled TMX files and prepare them for easy use for games.
"""
from __future__ import absolute_import, division, print_function

import logging
import pprint
import struct
from collections import deque, namedtuple
from itertools import product
from unittest import TestCase

import os
import six

from pytmx import TiledTileset

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
    return map(int, "".join(i.strip() for i in data.strip()).split(","))


decompressors = {
    'gzip': decompress_gzip,
    'zlib': decompress_zlib
}

decoders = {
    'base64': decode_base64,
    'csv': decode_csv
}


def get_data_thing(xformers, exception):
    def func(data, xform):
        if xform:
            xformer = xformers.get(xform)
            if xformer is None:
                raise exception(xform)
            return xformer(data)

    return func


decompress = get_data_thing(decompressors, MissingDecompressorError)
decode = get_data_thing(decoders, MissingDecoderError)


def read_points(text):
    """parse a text string of float tuples and return [(x,...),...]
    """
    return tuple(tuple(map(float, i.split(','))) for i in text.split())


def unpack(data, encoding, compression):
    """ Decode and decompress level tile data

    :return:
    """
    temp = decode(data, encoding)
    if temp is not None:
        data = temp

    temp = decompress(data, compression)
    if temp is not None:
        data = temp

    return data


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
    try:
        return {key: types[key](value) for key, value in element.items()}
    except KeyError as e:
        raise UnsupportedFeature(element.tag, e.args)
    except (TypeError, UnicodeEncodeError):
        print(element.attrib, types)
        raise


class Dummy(object):
    def __init__(self, *args, **kwargs):
        pass


class Processor(object):
    attrib_types = dict()
    target_class = Dummy

    def __init__(self):
        self.attrib = dict()
        self.properties = dict()

    def apply_attrib(self, element):
        """
        :type element: xml.etree.ElementTree.Element
        :return: None
        """
        try:
            self.attrib = cast(element, self.attrib_types)
        except KeyError:
            raise

    def start(self, element, parent):
        """
        :type element: xml.etree.ElementTree.Element
        :type parent: Processor
        :return:
        """
        self.apply_attrib(element)

    def end(self, element, parent):
        """
        :type element: xml.etree.ElementTree.Element
        :type parent: Processor
        :return:
        """
        return self.as_instance(element, parent)

    def as_instance(self, element, parent):
        return self.target_class(*self.attrib)

    def add_properties(self, item):
        self.properties = item


class ProcessAnimation(Processor):
    def __init__(self):
        super(ProcessAnimation, self).__init__()
        self.frames = list()


class ProcessChunk(Processor):
    pass


class ProcessData(Processor):
    attrib_types = {
        'encoding': str,
        'compression': str
    }

    def __init__(self):
        super(ProcessData, self).__init__()
        self.encoding = None
        self.compression = None
        self.data = None
        self.tiles = list()

    def end(self, element, parent):
        # decode and decompress data
        data = unpack(element.text, self.encoding, self.compression)
        if data:
            # unpack into list of 32-bit integers
            fmt = struct.Struct('<L')
            every_4 = range(0, len(data), 4)
            gids = [decode_gid(fmt.unpack_from(data, i)[0]) for i in every_4]

            # get map dimension info from the stack
            w, h = parent.width, parent.height

            # split data into several arrays
            # self.data = tuple(array.array('H', gids[i * w:i * w + w]) for i in range(h))

    def add_tile(self, item):
        self.tiles.append(item)


class ProcessEllipse(Processor):
    pass


class ProcessFrame(Processor):
    attrib_types = {
        'tileid': int,
        'duration': int,
    }


class ProcessGroup(Processor):
    pass


class ProcessImage(Processor):
    attrib_types = {
        'format': str,
        'source': str,
        'trans': str,
        'width': int,
        'height': int,
    }


class ProcessImagelayer(Processor):
    attrib_types = {
        'name': str,
        'offsetx': int,
        'offsety': int,
        'opacity': float,
        'visbile': bool
    }

    def __init__(self):
        super(ProcessImagelayer, self).__init__()
        self.image = None

    def add_image(self, item):
        self.image = item


class ProcessLayer(Processor):
    attrib_types = {
        "name": str,
        "width": int,
        "height": int,
        "opacity": float,
        "visible": bool,
        "offsetx": int,
        "offsety": int,
    }

    def __init__(self):
        super(ProcessLayer, self).__init__()
        self.data = None

    def add_data(self, data):
        self.data = data


class ProcessMap(Processor):
    attrib_types = {
        "version": str,
        "tiledversion": str,
        "orientation": str,
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

    def __init__(self):
        super(ProcessMap, self).__init__()
        self.tilesets = list()
        self.layers = list()
        self.objectgroups = list()
        self.tilelayers = list()
        self.imagelayers = list()
        self.images = list()
        self.image_loader = default_image_loader
        self.filename = ''

    def add_tileset(self, item):
        self.tilesets.append(item)

    def add_layer(self, item):
        self.layers.append(item)
        self.tilelayers.append(item)

    def add_objectgroup(self, item):
        self.layers.append(item)
        self.objectgroups.append(item)

    def add_imagelayer(self, item):
        self.layers.append(item)
        self.imagelayers.append(item)

    def reload_images(self):
        """ Load the map images from disk

        This method will use the image loader passed in the constructor
        to do the loading or will use a generic default, in which case no
        images will be loaded.

        :return: None
        """
        self.images = [None] * self.maxgid

        # iterate through tilesets to get source images
        for ts in self.tilesets:

            # skip tilesets without a source
            if ts.source is None:
                continue

            path = os.path.join(os.path.dirname(self.filename), ts.source)
            colorkey = getattr(ts, 'trans', None)
            loader = self.image_loader(path, colorkey, tileset=ts)

            p = product(range(ts.margin,
                              ts.height + ts.margin - ts.tileheight + 1,
                              ts.tileheight + ts.spacing),
                        range(ts.margin,
                              ts.width + ts.margin - ts.tilewidth + 1,
                              ts.tilewidth + ts.spacing))

            # iterate through the tiles
            for real_gid, (y, x) in enumerate(p, ts.firstgid):
                rect = (x, y, ts.tilewidth, ts.tileheight)
                gids = self.map_gid(real_gid)

                # gids is None if the tile is never used
                # but give another chance to load the gid anyway
                if gids is None:
                    if self.load_all_tiles or real_gid in self.optional_gids:
                        # TODO: handle flags? - might never be an issue, though
                        gids = [self.register_gid(real_gid, flags=0)]

                if gids:
                    # flags might rotate/flip the image, so let the loader
                    # handle that here
                    for gid, flags in gids:
                        self.images[gid] = loader(rect, flags)

        # load image layer images
        for layer in (i for i in self.layers if isinstance(i, TiledImageLayer)):
            source = getattr(layer, 'source', None)
            if source:
                colorkey = getattr(layer, 'trans', None)
                real_gid = len(self.images)
                gid = self.register_gid(real_gid)
                layer.gid = gid
                path = os.path.join(os.path.dirname(self.filename), source)
                loader = self.image_loader(path, colorkey)
                image = loader()
                self.images.append(image)

        # load images in tiles.
        # instead of making a new gid, replace the reference to the tile that
        # was loaded from the tileset
        for real_gid, props in self.tile_properties.items():
            source = props.get('source', None)
            if source:
                colorkey = props.get('trans', None)
                path = os.path.join(os.path.dirname(self.filename), source)
                loader = self.image_loader(path, colorkey)
                image = loader()
                self.images[real_gid] = image


class ProcessObject(Processor):
    attrib_types = {
        'name': str,
        'id': int,
        'type': str,
        'x': float,
        'y': float,
        'width': float,
        'height': float,
        'rotation': float,
        'gid': int
    }

    def __init__(self):
        super(ProcessObject, self).__init__()
        self.points = None

    def add_polygon(self, item):
        self.points = item

    def add_polyline(self, item):
        self.points = item


class ProcessObjectgroup(Processor):
    attrib_types = {
        'name': str,
        'x': float,
        'y': float,
        'width': int,
        'height': int
    }

    def __init__(self):
        super(ProcessObjectgroup, self).__init__()
        self.objects = list()

    def add_object(self, item):
        self.objects.append(item)


class ProcessOffset(Processor):
    attrib_types = {
        'x': int,
        'y': int,
    }

    def end(self, element, parent):
        return cast(element, self.attrib_types)


class ProcessPolygon(Processor):
    attrib_types = {
        'points': read_points,
    }

    def __init__(self):
        super(ProcessPolygon, self).__init__()
        self.points = None

    def end(self, element, parent):
        return self.points


class ProcessPolyline(Processor):
    attrib_types = {
        'points': read_points,
    }

    def __init__(self):
        super(ProcessPolyline, self).__init__()
        self.points = None

    def end(self, element, parent):
        return self.points


class ProcessProperties(Processor):
    def __init__(self):
        super(ProcessProperties, self).__init__()
        self.dictionary = dict()

    def add_property(self, item):
        self.dictionary[item['name']] = item['value']

    def end(self, element, parent):
        return self.dictionary


class ProcessProperty(Processor):
    attrib_types = {
        'type': noop,
        'name': noop,
        'value': noop
    }

    def __init__(self):
        super(ProcessProperty, self).__init__()
        self.type = None
        self.name = None
        self.value = None

    def end(self, element, parent):
        """
        :type element: xml.etree.ElementTree.Element
        :return:
        """
        if self.type:
            _type = tiled_property_type[self.type]
            value = _type(self.value)
        else:
            value = self.value
        return {'name': self.name, 'value': value}


class ProcessTemplate(Processor):
    pass


class ProcessTerrain(Processor):
    pass


class ProcessTerraintypes(Processor):
    pass


class ProcessText(Processor):
    pass


class ProcessTile(Processor):
    attrib_types = {
        'id': int,
        'gid': int,
        'type': str,
        'terrain': str,
        'probability': float,
    }

    def __init__(self):
        super(ProcessTile, self).__init__()
        self.image = None

    def add_image(self, item):
        self.image = item


class ProcessTileoffset(Processor):
    pass


class ProcessTileset(Processor):
    attrib_types = {
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
    target_class = TiledTileset

    def __init__(self):
        super(ProcessTileset, self).__init__()
        self.image = None
        self.tiles = list()

    def add_image(self, image):
        self.image = image

    def add_tile(self, tile):
        self.tiles.append(tile)


class ProcessTilesetSource(Processor):
    def end(self, element, parent):
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


def get_processor(element):
    feature = element.tag.title()
    try:
        return globals()['Process' + feature]()
    except KeyError:
        raise UnsupportedFeature(feature)


def combine(parent, child, tag):
    try:
        func = getattr(parent, 'add_' + tag)
    except AttributeError:
        raise UnsupportedFeature(tag)
    func(child)


def slurp(filename):
    stack = deque([None])
    token = None

    for event, element in ElementTree.iterparse(filename, events=('start', 'end')):
        if event == 'start':
            parent = stack[-1]
            token = get_processor(element)
            token.start(element, parent)
            stack.append(token)

        elif event == 'end':
            token = stack.pop()
            parent = stack[-1]
            value = token.end(element, parent)
            if parent:
                combine(parent, value, element.tag)
            element.clear()

    return token


class TestCase2(TestCase):
    def test_init(self):
        import glob
        for filename in glob.glob('../apps/data/0.9.1/*tmx'):
            print(filename)
            token = slurp(filename)
            pprint.pprint(token.properties)
