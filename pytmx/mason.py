import gzip
import os
import struct
import zlib
from base64 import b64decode
from collections import namedtuple
from dataclasses import dataclass
from itertools import product
from typing import Any
from xml.etree import ElementTree

from pytmx.dc import (
    Map,
    Property,
    Tileset,
    Tile,
    Group,
    TileLayer,
    ObjectGroup,
    Object,
    Polygon,
    Polyline,
    ImageLayer,
    Image,
)

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29

TileFlags = namedtuple("TileFlags", ["horizontal", "vertical", "diagonal"])


def decode_gid(raw_gid):
    """Decode a GID from TMX data"""
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT)
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid, flags


def default_image_loader(filename, flags, **kwargs):
    """This default image loader just returns filename, rect, and any flags"""

    def load(rect=None, flags=None):
        return filename, rect, flags

    return load


def unpack_gids(text: str, encoding: str = None, compression: str = None):
    """Return iterator of all gids from encoded/compressed layer data"""
    if encoding == "base64":
        data = b64decode(text)
        if compression == "gzip":
            data = gzip.decompress(data)
        elif compression == "zlib":
            data = zlib.decompress(data)
        elif compression:
            raise Exception(f"layer compression {compression} is not supported.")
        fmt = struct.Struct("<L")
        iterator = (data[i: i + 4] for i in range(0, len(data), 4))
        return (fmt.unpack(i)[0] for i in iterator)
    elif encoding == "csv":
        return [int(i) for i in text.split(",")]
    elif encoding:
        raise Exception(f"layer encoding {encoding} is not supported.")


def shape_data(gids, width, height):
    """Change the shape of the data"""
    data = [[None] * width] * height
    for (y, x) in product(range(height), range(width)):
        data[y][x] = next(gids)
    return data


@dataclass
class Context:
    map: Map = None
    path: str = None
    image_loader: Any = None


@dataclass
class Token:
    type: str
    attrib: str
    text: str
    obj: Any


@dataclass
class Properties:
    data: dict


@dataclass
class Data:
    encoding: str
    compression: str
    text: str


def iter_image_tiles(width, height, tilewidth, tileheight, margin, spacing):
    return product(
        range(margin, height + margin - tileheight + 1, tileheight + spacing),
        range(margin, width + margin - tilewidth + 1, tilewidth + spacing),
    )


def getdefault(d):
    def get(key, type=None, default=None):
        try:
            value = d[key]
        except KeyError:
            return default
        if type:
            return type(value)
        return value

    return get


def start(ctx, name, attrib, text):
    get = getdefault(attrib)

    if name == "Data":
        return Data(
            encoding=get("encoding", None),
            compression=get("compression", None),
            text=text,
        )
    elif name == "Group":
        return Group(**attrib)
    elif name == "Image":
        return Image(source=get("source"), width=get("width", int), height=get("height", int), trans=get("trans"))
    elif name == "Imagelayer":
        return ImageLayer(name=get("name"), visible=get("visible"))
    elif name == "Layer":
        return TileLayer(
            name=get("name"),
            opacity=get("opacity", float, 1.0),
            visible=get("visible", bool, True),
            tintcolor=get("tintcolor"),
            offsetx=get("offsetx"),
            offsety=get("offsety"),
            data=get("data"),
        )
    elif name == "Map":
        return Map(
            version=get("version"),
            tiledversion=get("tiledversion"),
            orientation=get("orientation"),
            renderorder=get("renderorder"),
            compressionlevel=get("compressionlevel"),
            width=get("width", int),
            height=get("height", int),
            tilewidth=get("tilewidth", int),
            tileheight=get("tileheight", int),
            hexsidelength=get("hexsidelength", int),
            staggeraxis=get("staggeraxis", int),
            staggerindex=get("staggerindex", int),
            background_color=get("backgroundcolor"),
            infinite=get("infinite", bool, False),
            filename=ctx.path,
        )
    elif name == "Object":
        return Object(
            name=get("name"),
            type=get("type"),
            x=get("x", float),
            y=get("y", float),
            width=get("width", float),
            height=get("height", float),
            rotation=get("rotation", float),
            tile=get("tile"),
            visible=get("visible", bool, True),
        )
    elif name == "Objectgroup":
        return ObjectGroup(
            name=get("name"),
            color=get("color"),
            opacity=get("opacity", float, 1.0),
            visible=get("visible", bool, True),
            tintcolor=get("tintcolor"),
            offsetx=get("offsetx", float),
            offsety=get("offsety", float),
            draworder=get("draworder"),
        )
    elif name == "Polygon":
        return Polygon(points=get("points"))
    elif name == "Polyline":
        return Polyline(points=get("points"))
    elif name == "Properties":
        return Properties(dict())
    elif name == "Property":
        return Property(attrib["name"], attrib.get("type", None), attrib["value"])
    elif name == "Tile":
        return Tile(**attrib)
    elif name == "Tileset":
        return Tileset(
            firstgid=get("firstgid", int),
            source=get("source"),
            name=get("name"),
            tilewidth=get("tilewidth", int),
            tileheight=get("tileheight", int),
            spacing=get("spacing", int, 0),
            margin=get("margin", int, 0),
            tilecount=get("tilecount"),
            columns=get("columns"),
            objectalignment=get("objectalignment"),
        )
    raise ValueError(name)


def end(ctx, path, parent, child, stack):
    if path == "Properties.Property":
        parent.data[child.name] = child.value
    elif path == "Imagelayer.Image":
        parent.image = child
    elif path == "Layer.Data":
        parent.data = unpack_gids(child.text, child.encoding, child.compression)
    elif path == "Map":
        tiles = {0: None}
        for ts in child.tilesets:
            assert len(ts.images) == 1
            image = ts.images[0]
            path = os.path.join(os.path.dirname(child.filename), image.source)
            loader = ctx.image_loader(path, image.trans, tileset=ts)
            p = iter_image_tiles(image.width, image.height, ts.tilewidth, ts.tileheight, ts.margin, ts.spacing)
            for raw_gid, (y, x) in enumerate(p, ts.firstgid):
                gid, flags = decode_gid(raw_gid)
                rect = (x, y, ts.tilewidth, ts.tileheight)
                assert raw_gid not in tiles
                tiles[raw_gid] = loader(rect, flags)
        for tl in child.tile_layers:
            data = (tiles[gid] for gid in tl.data)
            tl.data = shape_data(data, child.width, child.height)
        pass
    elif path == "Map.Imagelayer":
        parent.add_layer(child)
    elif path == "Map.Layer":
        parent.add_layer(child)
    elif path == "Map.Objectgroup":
        parent.add_layer(child)
    elif path == "Map.Properties":
        parent.properties = child.data
    elif path == "Map.Tileset":
        parent.add_tileset(child)
    elif path == "Object.Properties":
        parent.properties = child.data
    elif path == "Object.Polygon":
        parent.shape = child
    elif path == "Object.Polyline":
        parent.shape = child
    elif path == "Objectgroup.Object":
        parent.objects.append(child)
    elif path == "Tileset.Image":
        parent.images.append(child)
    elif path == "Tileset.Properties":
        parent.properties = child.data
    elif path == "Tile.Properties":
        parent.properties = child.data
    elif path == "Tileset.Tile":
        pass
    else:
        raise ValueError(path)


def search(stack, type):
    for token in reversed(stack):
        if token.type == type:
            return token.obj


def iter_tmx(path, image_loader):
    ctx = Context()
    ctx.path = path
    ctx.image_loader = image_loader
    stack = list()
    root = ElementTree.iterparse(path, events=("start", "end"))
    for event, element in root:
        name = element.tag.title()
        attrib = element.attrib
        text = element.text
        if event == "start":
            obj = start(ctx, name, attrib, text)
            t = Token(name, attrib, text, obj)
            stack.append(t)
        elif event == "end":
            t = stack.pop()
            if stack:
                parent = stack[-1].obj
                child = t.obj
                path = ".".join((stack[-1].type, t.type))
                end(ctx, path, parent, child, stack)
            else:
                end(ctx, t.type, None, t.obj, stack)
            element.clear()
            yield t.obj
        else:
            raise Exception


def load_tmx(path, image_loader):
    mason_map = list(iter_tmx(path, image_loader))[-1]
    return mason_map
