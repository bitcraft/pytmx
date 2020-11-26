"""
Copyright (C) 2012-2020, Leif Theden <leif.theden@gmail.com>

This file is part of pytmx.

pytmx is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

pytmx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with pytmx.  If not, see <http://www.gnu.org/licenses/>.
"""
import gzip
import os
import struct
import threading
import time
import zlib
from base64 import b64decode
from collections import defaultdict
from dataclasses import dataclass, field, replace
from itertools import product
from queue import Queue
from typing import Any, Dict, Tuple, List, Iterator
from xml.etree import ElementTree

from contrib.pygame_adapter import pygame_image_loader
from objects import SubImage, Properties
from pytmx import objects

# objects.Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29


class MasonException(Exception):
    pass


@dataclass
class TileFlags:
    horizontal: bool
    vertical: bool
    diagonal: bool


@dataclass
class Context:
    map: objects.Map = None
    path: str = None
    folder: str = None
    image_loader: Any = None
    invert_y: bool = None
    tiles: Dict = field(default_factory=dict)
    firstgid: int = 0
    gid_refs: defaultdict = None


@dataclass
class Reference:
    target: Any
    attribute_name: str
    gid: int
    replace: Any


@dataclass
class Token:
    type: str
    attrib: str
    text: str
    obj: Any


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
class ImagePlaceholder:
    source: str
    x: int
    y: int
    width: int
    height: int


def convert_to_bool(value: Any) -> bool:
    """ Convert a few common variations of "true" and "false" to boolean
    """
    value = str(value).strip()
    if value:
        value = value.lower()[0]
        if value in ("1", "y", "t"):
            return True
        if value in ("-", "0", "n", "f"):
            return False
        raise ValueError('cannot parse "{}" as bool'.format(value))
    else:
        return False


def decode_gid(raw_gid: int) -> Tuple[int, bool, bool, bool]:
    """Decode a GID from TMX data"""
    return (
        raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT),
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
    )


def default_image_loader(filename: str):
    """This default image loader just returns filename, rect, and any flags"""

    def load(rect=None, flags=None):
        return filename, rect, flags

    return load


def getdefault(d: Dict):
    """Return dictionary key as optional type, with a default"""

    def get(key, type=None, default=None):
        try:
            value = d[key]
        except KeyError:
            return default
        if type is not None:
            return type(value)
        return value

    return get


def iter_image_tiles(
    width: int, height: int, tilewidth: int, tileheight: int, margin: int, spacing: int
) -> Iterator[Tuple[int, int, int, int]]:
    """Iterate tiles in the image"""
    for y, x in product(
        range(margin, height + margin - tileheight + 1, tileheight + spacing),
        range(margin, width + margin - tilewidth + 1, tilewidth + spacing),
    ):
        # tiles.append((x, y, tilewidth, tileheight))
        yield x, y, tilewidth, tileheight


def parse_points(text: str) -> List[Tuple[float, float]]:
    """Return list of tuples representing points"""
    return list(tuple(map(float, i.split(","))) for i in text.split())


def reshape_data(gids: List[int], width: int):
    """Change 1d list to 2d list"""
    return [gids[i : i + width] for i in range(0, len(gids), width)]


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
        fmt = "<%dL" % (len(data) // 4)
        return list(struct.unpack(fmt, data))
    elif encoding == "csv":
        return [int(i) for i in text.split(",")]
    elif encoding:
        raise MasonException(f"layer encoding {encoding} is not supported.")


# object creation


def new_animation(ctx, stack, get, text) -> objects.Animation:
    return objects.Animation()


def new_data(ctx, stack, get, text) -> Data:
    return Data(get("encoding"), get("compression"), text=text)


def new_ellipse(ctx, stack, get, text) -> objects.Circle:
    return objects.Circle()


def new_frame(ctx, stack, get, text) -> objects.AnimationFrame:
    return objects.AnimationFrame(tile=get("tile", int), duration=get("duration", int))


def new_grid(ctx, stack, get, text) -> Grid:
    return Grid(get("orientation"), get("width", int), get("height", int))


def new_group(ctx, stack, get, text) -> objects.Group:
    return objects.Group(
        name=get("name"),
        opacity=get("opacity", float, 1.0),
        visible=get("visible", convert_to_bool, True),
        tintcolor=get("tintcolor"),
        offsetx=get("offsetx", int),
        offsety=get("offsety", int),
    )


def new_image(ctx, stack, get, text) -> objects.Image:
    return objects.Image(
        source=get("source"),
        width=get("width", int),
        height=get("height", int),
        trans=get("trans"),
    )


def new_imagelayer(ctx, stack, get, text) -> objects.ImageLayer:
    return objects.ImageLayer(
        get("name"), get("visible", convert_to_bool, True), get("image")
    )


def new_map(ctx, stack, get, text) -> objects.Map:
    return objects.Map(
        version=get("version"),
        orientation=get("orientation"),
        renderorder=get("renderorder"),
        # compressionlevel=get("compressionlevel"),
        width=get("width", int),
        height=get("height", int),
        tilewidth=get("tilewidth", int),
        tileheight=get("tileheight", int),
        hexsidelength=get("hexsidelength", int),
        staggeraxis=get("staggeraxis", int),
        staggerindex=get("staggerindex", int),
        background_color=get("backgroundcolor"),
        infinite=get("infinite", convert_to_bool, False),
        filename=ctx.path,
    )


def new_object(ctx, stack, get, text) -> objects.Object:
    return objects.Object(
        name=get("name"),
        type=get("type"),
        x=get("x", float),
        y=get("y", float),
        width=get("width", float),
        height=get("height", float),
        rotation=get("rotation", float),
        gid=get("gid", int, 0),
        visible=get("visible", convert_to_bool, True),
    )


def new_objectgroup(ctx, stack, get, text) -> objects.ObjectGroup:
    return objects.ObjectGroup(
        name=get("name"),
        color=get("color"),
        opacity=get("opacity", float, 1.0),
        visible=get("visible", convert_to_bool, True),
        tintcolor=get("tintcolor"),
        offsetx=get("offsetx", float),
        offsety=get("offsety", float),
        draworder=get("draworder"),
    )


def new_point(ctx, stack, get, text) -> objects.Point:
    return objects.Point(get("x", float), get("y", float))


def new_polygon(ctx, stack, get, text) -> objects.Polygon:
    points = parse_points(get("points"))
    return objects.Polygon(points=points)


def new_polyline(ctx, stack, get, text) -> objects.Polyline:
    points = parse_points(get("points"))
    return objects.Polyline(points=points)


def new_properties(ctx, stack, get, text) -> Properties:
    return Properties(dict())


def new_property(ctx, stack, get, text) -> objects.Property:
    return objects.Property(get("name"), get("type"), get("value"))


def new_text(ctx, stack, get, text) -> objects.Text:
    return objects.Text(
        bold=get("bold"),
        color=get("color"),
        fontfamily=get("fontfamily"),
        halign=get("halign"),
        italic=get("italic"),
        kerning=get("kerning"),
        pixelsize=get("pixelsize"),
        strikeout=get("strikeout"),
        text=text,
        underline=get("underline"),
        valign=get("valign"),
        wrap=get("wrap"),
    )


def new_tile(ctx, stack, get, text) -> objects.Tile:
    return objects.Tile(
        id=get("id", int, None),
        gid=get("gid", int, None),
        type=get("type"),
        terrain=get("terrain"),
        image=get("image"),
    )


def new_tilelayer(ctx, stack, get, text) -> objects.TileLayer:
    return objects.TileLayer(
        data=get("data"),
        name=get("name"),
        offsetx=get("offsetx", float),
        offsety=get("offsety", float),
        opacity=get("opacity", float, 1.0),
        tintcolor=get("tintcolor"),
        visible=get("visible", convert_to_bool, True),
    )


def new_tileset(ctx, stack, get, text) -> objects.Tileset:
    source = get("source")
    firstgid = get("firstgid", int)
    if firstgid:
        ctx.firstgid = firstgid
    if source:
        path = os.path.join(ctx.folder, source)
        tileset = parse_for_parent_node_only(ctx, path)
        return tileset
    return objects.Tileset(
        columns=get("columns", int),
        firstgid=get("firstgid", int, 0),
        margin=get("margin", int, 0),
        name=get("name"),
        objectalignment=get("objectalignment"),
        source=get("source"),
        spacing=get("spacing", int, 0),
        tilecount=get("tilecount", int),
        tileheight=get("tileheight", int),
        tilewidth=get("tilewidth", int),
    )


# operations


def add_animation_frame(ctx, stack, parent, child: objects.AnimationFrame):
    parent.frames.append(child)


def add_layer(ctx, stack, map: objects.Map, layer):
    map.layers.append(layer)


def add_object(ctx, stack, parent: objects.ObjectGroup, child: objects.Object):
    if child.gid:
        child.image = ctx.tiles[child.gid].image
    parent.objects.append(child)


def add_objectgroup_to_tile(
    ctx, stack, parent: objects.Tile, child: objects.ObjectGroup
):
    parent.collider_group = child


def add_shape(ctx, stack, parent, child):
    pass


def add_tile_to_tileset(ctx, stack, parent: objects.Tileset, child: objects.Tile):
    if not parent.firstgid:
        parent.firstgid = ctx.firstgid
    ctx.tiles[parent.firstgid + child.id] = child


def add_to_group(ctx, stack, parent: objects.Group, child):
    parent.layers.append(child)


def copy_attribute(name):
    def copy(ctx, stack, parent, child):
        setattr(parent, name, getattr(child, name))

    return copy


def exception(message):
    def raise_exception(*args):
        raise MasonException(message)

    return raise_exception


def finalize_map(ctx, stack, parent: None, child: objects.Map):
    child.tiles = ctx.tiles
    # for tile in ctx.tiles.values():
    #     if tile:
    #         tile.calc_blit_offset(child.tileheight)


def load_tileset(ctx, stack, parent: objects.Tileset, child: objects.Image):
    path = os.path.join(ctx.folder, child.source)
    tilewidth = parent.tilewidth
    tileheight = parent.tileheight
    p = iter_image_tiles(
        child.width, child.height, tilewidth, tileheight, parent.margin, parent.spacing,
    )
    tileset_image = Reference(child, "object", 0, None)
    for gid, rect in enumerate(p, parent.firstgid):
        x, y, w, h = rect
        image = SubImage(source=child, x=x, y=y, width=tilewidth, height=tileheight)
        ctx.ref2.append(Reference(image, "object", 0, image))
        tile = objects.Tile(gid=gid, image=image)
        ctx.tiles[gid] = tile


def noop(*args):
    pass


def set_animation(ctx, stack, parent, child: objects.Animation):
    parent.animation = child


def set_image(ctx, stack, parent, child: objects.Image):
    path = os.path.join(ctx.folder, child.source)
    # image = ctx.image_loader(path)()
    parent.image = ImagePlaceholder(
        source=path, x=0, y=0, width=child.width, height=child.height,
    )
    ref = Reference(parent, "image", None)
    # ctx.gid_refs[gid] = ref


def set_layer_data(ctx, stack, parent: objects.Map, child: Data):
    data = list()
    for raw_gid in unpack_gids(child.text, child.encoding, child.compression):
        if raw_gid:
            tile = ctx.tiles[raw_gid]
            if raw_gid > GID_TRANS_ROT:
                gid, h, v, d = decode_gid(raw_gid)
                tile = replace(tile, flipped_h=h, flipped_v=v, flipped_d=d,)
                ctx.tiles[raw_gid] = tile
            data.append(tile)
        else:
            data.append(None)
    map = search(stack, "Map")
    parent.data = reshape_data(data, map.width)


def set_properties(ctx, stack, parent, child: Properties):
    parent.properties = child.value


def set_property(ctx, stack, parent: Properties, child: objects.Property):
    parent.value[child.name] = child.value


factory = {
    "Animation": new_animation,
    "Data": new_data,
    "Ellipse": new_ellipse,
    "Frame": new_frame,
    "Grid": new_grid,
    "Group": new_group,
    "Image": new_image,
    "Imagelayer": new_imagelayer,
    "Layer": new_tilelayer,
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
    (Data, objects.Tile): exception(
        "Map using XML objects.Tile elements not supported"
    ),
    (objects.Animation, objects.AnimationFrame): add_animation_frame,
    (objects.Group, objects.ObjectGroup): add_layer,
    (objects.Group, objects.TileLayer): add_layer,
    (objects.ImageLayer, objects.Image): set_image,
    (objects.Map, objects.Group): add_layer,
    (objects.Map, objects.ImageLayer): add_layer,
    (objects.Map, objects.ObjectGroup): add_layer,
    (objects.Map, objects.TileLayer): add_layer,
    (objects.Map, objects.Tileset): noop,
    (objects.Map, Properties): set_properties,
    (objects.Map,): finalize_map,
    (objects.Object, objects.Circle): add_shape,
    (objects.Object, objects.Point): add_shape,
    (objects.Object, objects.Polygon): add_shape,
    (objects.Object, objects.Polyline): add_shape,
    (objects.Object, objects.Text): add_shape,
    (objects.Object, Properties): set_properties,
    (objects.ObjectGroup, objects.Object): add_object,
    (objects.ObjectGroup, Properties): set_properties,
    (objects.Tile, objects.Animation): set_animation,
    (objects.Tile, objects.Image): set_image,
    (objects.Tile, objects.ObjectGroup): add_objectgroup_to_tile,
    (objects.Tile, Properties): set_properties,
    (objects.TileLayer, Data): set_layer_data,
    (objects.TileLayer, Properties): set_properties,
    (objects.Tileset, Grid): copy_attribute("orientation"),
    (objects.Tileset, objects.Image): load_tileset,
    (objects.Tileset, objects.Tile): add_tile_to_tileset,
    (objects.Tileset, Properties): set_properties,
    (objects.Tileset,): noop,
    (Properties, objects.Property): set_property,
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


def parse_for_parent_node_only(ctx, path):
    node = None
    for node in parse_all_nodes(ctx, path):
        pass
    return node


def parse_all_nodes(ctx: Context, path: str) -> Iterator[Token]:
    stack = list()
    root = ElementTree.iterparse(path, events=("start", "end"))
    for event, element in root:
        name = element.tag.title()
        attrib = element.attrib
        text = element.text
        if event == "start":
            obj = factory[name](ctx, stack, getdefault(attrib), text)
            token = Token(name, attrib, text, obj)
            stack.append(token)
        elif event == "end":
            token = stack.pop()
            path = [type(token.obj)]
            parent = peek(stack)
            if parent.obj:
                path.insert(0, type(parent.obj))
            operation = operations[tuple(path)]
            operation(ctx, stack, parent.obj, token.obj)
            element.clear()
            yield token.obj


def worker(queue: Queue, ctx, loaders):
    """

    each thread should not pull in a new tileset...this requires
    loading and evac a huge surface in and out of memory each time...
    a thread should work on tiles from a specific image

    :param queue:
    :param ctx:
    :param loaders:
    :return:
    """
    while True:
        item = queue.get()
        if item is None:
            queue.task_done()
            break
        else:
            gid, params = item
            image, rect, flags = params
            loader = None
            path = image.source
            while loader is None:
                if path in loaders:
                    loader = loaders[path]
                else:
                    lock = ctx.locks[path]
                    if lock.acquire(blocking=False):
                        loader = pygame_image_loader(path)
                        loaders[path] = loader
                        lock.release()
            image = loader(rect)
            ctx.gidmap[gid] = image
            queue.task_done()


def load_tmxmap(path, image_loader=default_image_loader) -> objects.Map:
    """

    * build the context
    * scan the xml, iterate intermediate mason objects
    * no external resources are loaded during scanning
    * after scanning in complete, search the object stream for placeholders
    * batch the placeholders and load them
    * replace placeholder objects with loaded resources
    * set additional attributes on objects for the platform
    
    """
    start = time.time_ns()
    image_queue = Queue()
    threads = 1

    invert_y = False
    ctx = Context()
    ctx.path = path
    ctx.folder = os.path.dirname(path)
    ctx.image_loader = image_loader
    ctx.invert_y = invert_y
    ctx.tiles = {0: None}
    ctx.gid_refs = defaultdict(set)
    ctx.gidmap = dict()
    ctx.references = dict()
    ctx.names = dict()
    ctx.ref2 = list()
    ctx.locks = defaultdict(threading.Lock)

    # loaders = dict()
    # for i in range(threads):
    #     thread = threading.Thread(
    #         target=worker, args=(image_queue, ctx, loaders), daemon=True
    #     )
    #     thread.start()

    mason_map = parse_for_parent_node_only(ctx, path)

    for ref in ctx.ref2:
        target = ref.target
        if isinstance(target, SubImage):
            print(target.source)

    # for i in range(threads):
    #     image_queue.put(None)
    # image_queue.join()

    # convert must be done must be done by the main thread; this is a pygame limitation
    for surface in ctx.gidmap.values():
        surface.convert()

    duration = (time.time_ns() - start) / 1000 / 1000
    print(duration)

    return mason_map
