import dataclasses
import gzip
import os
import struct
import zlib
from base64 import b64decode
from collections import namedtuple
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Dict
from xml.etree import ElementTree

from pytmx.dc import (
    Circle,
    Group,
    Image,
    ImageLayer,
    Map,
    Object,
    ObjectGroup,
    Polygon,
    Polyline,
    Property,
    Tile,
    TileLayer,
    Tileset,
    Text,
    Point,
)
from pytmx.util_pygame import smart_convert, handle_transformation

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29

TileFlags = namedtuple("TileFlags", ["horizontal", "vertical", "diagonal"])


class MasonException(Exception):
    pass


@dataclass
class Context:
    map: Map = None
    path: str = None
    folder: str = None
    image_loader: Any = None
    invert_y: bool = None
    tiles: Dict = field(default_factory=dict)
    firstgid: int = 0


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


@dataclass
class Grid:
    orientation: str
    width: int
    height: int


@dataclass
class TilesetTile:
    gid: int
    image: Any


def decode_gid(raw_gid):
    """Decode a GID from TMX data"""
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
    )
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid, flags


def default_image_loader(filename, flags, **kwargs):
    """This default image loader just returns filename, rect, and any flags"""

    def load(rect=None, flags=None):
        return filename, rect, flags

    return load


def unpack_gids(text: str, encoding: str = None, compression: str = None):
    """Return all gids from encoded/compressed layer data"""
    if encoding == "base64":
        data = b64decode(text)
        if compression == "gzip":
            data = gzip.decompress(data)
        elif compression == "zlib":
            data = zlib.decompress(data)
        elif compression:
            raise MasonException(f"layer compression {compression} is not supported.")
        fmt = struct.Struct("<L")
        iterator = (data[i : i + 4] for i in range(0, len(data), 4))
        return [fmt.unpack(i)[0] for i in iterator]
    elif encoding == "csv":
        return [int(i) for i in text.split(",")]
    elif encoding:
        raise MasonException(f"layer encoding {encoding} is not supported.")


def reshape_data(gids, width):
    """Change the shape of the data"""
    return [gids[i : i + width] for i in range(0, len(gids), width)]


def iter_image_tiles(width, height, tilewidth, tileheight, margin, spacing):
    """Iterate tiles in the image"""
    return product(
        range(margin, height + margin - tileheight + 1, tileheight + spacing),
        range(margin, width + margin - tilewidth + 1, tilewidth + spacing),
    )


def getdefault(d):
    """Return dictionary key as optional type, with a default"""

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
    elif name == "Ellipse":
        return Circle()
    elif name == "Grid":
        return Grid(get("orientation"), get("width", int), get("height", int))
    elif name == "Group":
        return Group(
            name=get("name"),
            opacity=get("opacity", float, 1.0),
            visible=get("visible", bool, True),
            tintcolor=get("tintcolor"),
            offsetx=get("offsetx"),
            offsety=get("offsety"),
        )
    elif name == "Image":
        return Image(
            source=get("source"),
            width=get("width", int),
            height=get("height", int),
            trans=get("trans"),
        )
    elif name == "Imagelayer":
        return ImageLayer(
            name=get("name"), visible=get("visible", bool, True), image=get("image")
        )
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
        y = get("y", float)
        height = get("height", float)
        return Object(
            name=get("name"),
            type=get("type"),
            x=get("x", float),
            y=y,
            width=get("width", float),
            height=height,
            rotation=get("rotation", float),
            gid=get("gid", int, 0),
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
    elif name == "Point":
        return Point(get("x", int), get("y", int))
    elif name == "Polygon":
        text = get("points")
        points = list(tuple(map(float, i.split(","))) for i in text.split())
        return Polygon(points=points)
    elif name == "Polyline":
        return Polyline(points=get("points"))
    elif name == "Properties":
        return Properties(dict())
    elif name == "Property":
        return Property(attrib["name"], attrib.get("type", None), attrib["value"])
    elif name == "Tile":
        return Tile(
            id=get("id", int, None),
            gid=get("gid", int, None),
            type=get("type"),
            terrain=get("terrain"),
        )
    elif name == "Text":
        return Text(
            fontfamily=get("fontfamily"),
            pixelsize=get("pixelsize"),
            wrap=get("wrap"),
            color=get("color"),
            bold=get("bold"),
            italic=get("italic"),
            underline=get("underline"),
            strikeout=get("strikeout"),
            kerning=get("kerning"),
            halign=get("halign"),
            valign=get("valign"),
        )
    elif name == "Tileset":
        source = get("source")
        firstgid = get("firstgid", int)
        if firstgid:
            ctx.firstgid = firstgid
        if source:
            path = os.path.join(ctx.folder, source)
            tileset = parse_tmxdata(ctx, path)
            return tileset
        return Tileset(
            firstgid=get("firstgid", int, 0),
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
    if path == "Data.Tile":
        raise MasonException(
            "Map using XML Tile elements not supported.  Save file under a newer format."
        )
    elif path == "Group.Layer":
        parent.layers.append(child)
    elif path == "Group.Objectgroup":
        parent.layers.append(child)
    elif path == "Imagelayer.Image":
        path = os.path.join(ctx.folder, child.source)
        image = ctx.image_loader(path)()
        parent.image = image
    elif path == "Layer.Data":
        data = list()
        for raw_gid in unpack_gids(child.text, child.encoding, child.compression):
            if raw_gid:
                gid, flags = decode_gid(raw_gid)
                tile = ctx.tiles[gid]
                if gid != raw_gid:
                    # TODO: get the colorkey/pixelapha from the tileset
                    image = smart_convert(
                        handle_transformation(tile.image, flags), None, True
                    )
                    tile = dataclasses.replace(tile, image=image)
                    ctx.tiles[raw_gid] = tile
                data.append(tile)
            else:
                data.append(None)
        map = search(stack, "Map")
        parent.data = reshape_data(data, map.width)
    elif path == "Layer.Properties":
        parent.properties = child.data
    elif path == "Map":
        pass
    elif path == "Map.Group":
        parent.add_layer(child)
    elif path == "Map.Imagelayer":
        parent.add_layer(child)
    elif path == "Map.Layer":
        parent.add_layer(child)
    elif path == "Map.Objectgroup":
        parent.add_layer(child)
    elif path == "Map.Properties":
        parent.properties = child.data
    elif path == "Map.Tileset":
        pass
    elif path == "Object.Ellipse":
        parent.shapes.append(child)
    elif path == "Object.Point":
        parent.shapes.append(child)
    elif path == "Object.Properties":
        parent.properties = child.data
    elif path == "Object.Polygon":
        parent.shapes.append(child)
    elif path == "Object.Polyline":
        parent.shapes.append(child)
    elif path == "Objectgroup.Object":
        if child.gid:
            child.image = ctx.tiles[child.gid].image
        parent.objects.append(child)
    elif path == "Object.Text":
        parent.shapes.append(child)
    elif path == "Properties.Property":
        parent.data[child.name] = child.value
    elif path == "Tileset.Grid":
        parent.orientation = child.orientation
        assert parent.orientation == "orthogonal"
    elif path == "Tileset.Image":
        path = os.path.join(ctx.folder, child.source)
        loader = ctx.image_loader(path, child.trans, tileset=parent)
        p = iter_image_tiles(
            child.width,
            child.height,
            parent.tilewidth,
            parent.tileheight,
            parent.margin,
            parent.spacing,
        )
        for gid, (y, x) in enumerate(p, parent.firstgid):
            rect = (x, y, parent.tilewidth, parent.tileheight)
            ctx.tiles[gid] = Tile(gid=gid, image=loader(rect, None))
    elif path == "Tileset.Properties":
        parent.properties = child.data
    elif path == "Tile.Properties":
        parent.properties = child.data
    elif path == "Tile.Image":
        path = os.path.join(ctx.folder, child.source)
        image = ctx.image_loader(path)()
        parent.image = image
    elif path == "Tileset":
        pass
    elif path == "Tileset.Tile":
        if not parent.firstgid:
            parent.firstgid = ctx.firstgid
        ctx.tiles[parent.firstgid + child.id] = child
    else:
        raise ValueError(path)


def search(stack, type):
    for token in reversed(stack):
        if token.type == type:
            return token.obj


def parse_tmxdata(ctx, path):
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
    return t.obj


def load_tmxmap(path, image_loader):
    invert_y = False
    ctx = Context()
    ctx.path = path
    ctx.folder = os.path.dirname(path)
    ctx.image_loader = image_loader
    ctx.invert_y = invert_y
    ctx.tiles = {0: None}
    mason_map = parse_tmxdata(ctx, path)
    return mason_map
