"""
Mason: a fast library to read Tiled TMX files.

For Python 3.3+

* TMX and JSON parsing
* Embedded images are supported
* Supports many features up to version 1.4.0

Mason is designed to read Tiled TMX files and prepare them for easy use for games.

This file uses a template to generate the library for map loading.
"""
import array
import logging
import os
import struct
from collections import deque, namedtuple
from itertools import product
from unittest import TestCase

__version__ = 1
tiled_version = "1.4.2"

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
    "flipped_horizontally",
    "flipped_vertically",
    "flipped_diagonally",
)

def default_image_loader(filename, flags, **kwargs):
    """This default image loader just returns filename, rect, and any flags"""

    def load(rect=None, flags=None):
        return filename, rect, flags
    return load


def decompress_zlib(data):
    import zlib

    return zlib.decompress(data)


def decompress_gzip(data):
    import gzip
    import io

    with gzip.GzipFile(fileobj=io.BytesIO(data)) as fh:
        return fh.read()


def decode_base64(data):
    from base64 import b64decode

    return b64decode(data.strip())


def decode_csv(data):
    return map(int, "".join(i.strip() for i in data.strip()).split(","))


def get_data_xform(prefix, exception):
    """Generic function to transform data and raise exception"""

    def func(data, xform):
        if xform:
            try:
                xformer = globals()[prefix + xform]
            except KeyError:
                raise exception(xform)
            return xformer(data)

    return func


decompress = get_data_xform("decompress_", UnsupportedFeature)
decode = get_data_xform("decode_", UnsupportedFeature)


def unpack(data, encoding, compression):
    """Decode and decompress level tile data"""
    for func, arg in [(decode, encoding), (decompress, compression)]:
        temp = func(data, arg)
        if temp is not None:
            data = temp
    return data


def unroll_layer_data(data):
    fmt = struct.Struct("<L")
    every_4 = range(0, len(data), 4)
    return [decode_gid(fmt.unpack_from(data, i)[0]) for i in every_4]


def rowify(gids, w, h):
    return tuple(array.array("H", gids[i * w : i * w + w]) for i in range(h))


if content:
    data = unpack(content, self.encoding, self.compression)
    self.data = rowify(unroll_layer_data(data), w, h)
elif self.tiles:
    self.data = rowify([i.gid for i in self.tiles], w, h)


def read_points(text):
    """Parse a text string of float tuples and return [(x,...),...]"""
    return tuple(tuple(map(float, i.split(","))) for i in text.split())


def move_points(points, x, y):
    """Given list of points, return new one offset by (x, y)"""
    return tuple((i[0] + x, i[1] + y) for i in points)


def calc_bounds(points):
    """Given list of points, return mix/max of each axis"""
    x1 = x2 = y1 = y2 = 0
    for x, y in points:
        if x < x1:
            x1 = x
        elif x > x2:
            x2 = x
        if y < y1:
            y1 = y
        elif y > y2:
            y2 = y
    return abs(x1) + abs(x2), abs(y1) + abs(y2)


def decode_gid(raw_gid):
    """Decode a GID from TMX data

    as of Tiled 0.7.0 tile can be flipped when rendered
    as of Tiled 0.8.0 bit 30 determines if GID is rotated
    """
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
    )
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid



        self.points = move_points(item.points, self.x, self.y)
        self.attrib["closed"] = False


class TilesetSourceToken(Token):
    def end(self, content, context):
        if source[-4:].lower() == ".tsx":

            # external tilesets don"t save this, store it for later
            self.firstgid = int(content.get("firstgid"))

            # we need to mangle the path - tiled stores relative paths
            dirname = os.path.dirname(self.parent.filename)
            path = os.path.abspath(os.path.join(dirname, source))
            try:
                content = ElementTree.parse(path).getroot()
            except IOError:
                msg = "Cannot load external tileset: {0}"
                logger.error(msg.format(path))
                raise Exception

        else:
            msg = "Found external tileset, but cannot handle type: {0}"
            logger.error(msg.format(self.source))
            raise UnsupportedFeature(self.source)


    def load_tiles(self, content, context):
        tw, th = self.tilewidth, self.tileheight

        width = self.image.width
        height = self.image.height

        p = product(
            range(self.margin, height + self.margin - th + 1, th + self.spacing),
            range(self.margin, width + self.margin - tw + 1, tw + self.spacing),
        )

        path = self.image.source
        loader_class = context["image_loader"]
        loader = loader_class(path, None, colorkey=self.image.trans)

        # iterate through the tiles
        for gid, (y, x) in enumerate(p, self.firstgid):
            flags = None
            image = loader((x, y, tw, th), flags)

def get_loader(path):
    name, ext = os.path.splitext(path.lower())
    try:
        func = globals()["load_" + ext[1:]]
        return func(path)
    except KeyError:
        raise UnsupportedFeature(ext)


def load_tmx(path):
    from xml.etree import ElementTree
    root = ElementTree.iterparse(path, events=("start", "end"))
    for event, element in root:
        yield event, element.tag.title(), element.attrib, element.text
        if event == "end":
            element.clear()
