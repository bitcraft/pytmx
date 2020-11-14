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
    value: dict


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


def decode_gid(raw_gid):
    """Decode a GID from TMX data"""
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
    )
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid, flags


def default_image_loader(filename, ):
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
        iterator = (data[i: i + 4] for i in range(0, len(data), 4))
        return [fmt.unpack(i)[0] for i in iterator]
    elif encoding == "csv":
        return [int(i) for i in text.split(",")]
    elif encoding:
        raise MasonException(f"layer encoding {encoding} is not supported.")


def reshape_data(gids, width):
    """Change the shape of the data"""
    return [gids[i: i + width] for i in range(0, len(gids), width)]


def iter_image_tiles(width, height, tilewidth, tileheight, margin, spacing):
    """Iterate tiles in the image"""
    return product(
        range(margin, height + margin - tileheight + 1, tileheight + spacing),
        range(margin, width + margin - tilewidth + 1, tilewidth + spacing),
    )


# object creation


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


def new_data(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Data(get("encoding"), get("compression"), text=text)


def new_ellipse(ctx, stack, attrib, text):
    return Circle()


def new_grid(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Grid(get("orientation"), get("width", int), get("height", int))


def new_group(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Group(
        name=get("name"),
        opacity=get("opacity", float, 1.0),
        visible=get("visible", bool, True),
        tintcolor=get("tintcolor"),
        offsetx=get("offsetx"),
        offsety=get("offsety"),
    )


def new_image(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Image(
        source=get("source"),
        width=get("width", int),
        height=get("height", int),
        trans=get("trans"),
    )


def new_imagelayer(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return ImageLayer(get("name"), get("visible", bool, True), get("image"))


def new_tile_layer(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return TileLayer(
        name=get("name"),
        opacity=get("opacity", float, 1.0),
        visible=get("visible", bool, True),
        tintcolor=get("tintcolor"),
        offsetx=get("offsetx"),
        offsety=get("offsety"),
        data=get("data"),
    )


def new_map(ctx, stack, attrib, text):
    get = getdefault(attrib)
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


def new_object(ctx, stack, attrib, text):
    get = getdefault(attrib)
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


def new_objectgroup(ctx, stack, attrib, text):
    get = getdefault(attrib)
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


def new_point(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Point(get("x", int), get("y", int))


def new_polygon(ctx, stack, attrib, text):
    get = getdefault(attrib)
    text = get("points")
    points = list(tuple(map(float, i.split(","))) for i in text.split())
    return Polygon(points=points)


def new_polyline(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Polyline(points=get("points"))


def new_properties(ctx, stack, attrib, text):
    return Properties(dict())


def new_property(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Property(get("name"), get("type"), get("value"))


def new_text(ctx, stack, attrib, text):
    get = getdefault(attrib)
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


def new_tile(ctx, stack, attrib, text):
    get = getdefault(attrib)
    return Tile(
        id=get("id", int, None),
        gid=get("gid", int, None),
        type=get("type"),
        terrain=get("terrain"),
        image=get("image"),
    )


def new_tileset(ctx, stack, attrib, text):
    get = getdefault(attrib)
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


# operations


def add_layer(ctx, stack, map: Map, layer):
    map.layers.append(layer)


def add_object(ctx, stack, parent: ObjectGroup, child: Object):
    if child.gid:
        child.image = ctx.tiles[child.gid].image
    parent.objects.append(child)


def add_shape(ctx, stack, parent, child):
    pass


def add_tile_to_tileset(ctx, stack, parent: Tileset, child: Tile):
    if not parent.firstgid:
        parent.firstgid = ctx.firstgid
    ctx.tiles[parent.firstgid + child.id] = child


def add_to_group(ctx, stack, parent: Group, child):
    parent.layers.append(child)


def copy_attribute(name):
    def copy(ctx, stack, parent, child):
        setattr(parent, name, getattr(child, name))

    return copy


def exception(message):
    def raise_exception(*args):
        raise MasonException(message)

    return raise_exception


def finalize_map(ctx, stack, parent: None, child: Map):
    for tile in ctx.tiles.values():
        if tile:
            tile.calc_blit_offset(child.tileheight)
    child.tiles = ctx.tiles


def load_tileset(ctx, stack, parent: Tileset, child: Image):
    path = os.path.join(ctx.folder, child.source)
    loader = ctx.image_loader(path, child.trans)
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


def noop(*args):
    pass


def set_image(ctx, stack, parent, child: Image):
    path = os.path.join(ctx.folder, child.source)
    image = ctx.image_loader(path)()
    parent.image = image


def set_layer_data(ctx, stack, parent: Map, child: Data):
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


def set_properties(ctx, stack, parent, child: Properties):
    parent.properties = child.value


def set_property(ctx, stack, parent: Properties, child: Property):
    parent.value[child.name] = child.value


factory = {
    "Data": new_data,
    "Ellipse": new_ellipse,
    "Grid": new_grid,
    "Group": new_group,
    "Image": new_image,
    "Imagelayer": new_imagelayer,
    "Layer": new_tile_layer,
    "Map": new_map,
    "Object": new_object,
    "Objectgroup": new_objectgroup,
    "Point": new_point,
    "Polygon": new_polygon,
    "Polyline": new_polyline,
    "Properties": new_properties,
    "Property": new_property,
    "Text": new_text,
    "Tile": new_tile,
    "Tileset": new_tileset,
}

operations = {
    (Data, Tile): exception("Map using XML Tile elements not supported"),
    (Group, TileLayer): add_layer,
    (Group, ObjectGroup): add_layer,
    (ImageLayer, Image): set_image,
    (TileLayer, Data): set_layer_data,
    (TileLayer, Properties): set_properties,
    (Map,): finalize_map,
    (Map, Group): add_layer,
    (Map, ImageLayer): add_layer,
    (Map, TileLayer): add_layer,
    (Map, ObjectGroup): add_layer,
    (Map, Properties): set_properties,
    (Map, Tileset): noop,
    (Object, Circle): add_shape,
    (Object, Point): add_shape,
    (Object, Polygon): add_shape,
    (Object, Polyline): add_shape,
    (Object, Properties): set_properties,
    (Object, Text): add_shape,
    (ObjectGroup, Object): add_object,
    (Properties, Property): set_property,
    (Tile, Image): set_image,
    (Tile, Properties): set_properties,
    (Tileset,): noop,
    (Tileset, Grid): copy_attribute("orientation"),
    (Tileset, Image): load_tileset,
    (Tileset, Properties): set_properties,
    (Tileset, Tile): add_tile_to_tileset,
}


def search(stack, type):
    for token in reversed(stack):
        if token.type == type:
            return token.obj


def peek(stack):
    try:
        return stack[-1]
    except IndexError:
        return Token("", "", "", None)


def parse_tmxdata(ctx, path):
    stack = list()
    root = ElementTree.iterparse(path, events=("start", "end"))
    for event, element in root:
        name = element.tag.title()
        attrib = element.attrib
        text = element.text
        if event == "start":
            obj = factory[name](ctx, stack, attrib, text)
            t = Token(name, attrib, text, obj)
            stack.append(t)
        elif event == "end":
            t = stack.pop()
            path = [type(t.obj)]
            parent = peek(stack)
            if parent.obj:
                path.insert(0, type(parent.obj))
            operation = operations[tuple(path)]
            operation(ctx, stack, parent.obj, t.obj)
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
