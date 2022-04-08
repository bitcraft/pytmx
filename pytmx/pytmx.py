"""
Copyright (C) 2012-2022, Leif Theden <leif.theden@gmail.com>

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
License along with pytmx.  If not, see <https://www.gnu.org/licenses/>.

"""
from __future__ import annotations


import gzip
import logging
import os
import struct
import zlib
from base64 import b64decode
from collections import defaultdict, namedtuple
from itertools import chain, product
from math import cos, radians, sin
from operator import attrgetter
from typing import List, Tuple, Optional, Sequence, Union, Dict, Iterable
from xml.etree import ElementTree

# for type hinting
try:
    import pygame
except ImportError:
    pygame = None

__all__ = (
    "TileFlags",
    "TiledElement",
    "TiledImageLayer",
    "TiledMap",
    "TiledObject",
    "TiledObjectGroup",
    "TiledTileLayer",
    "TiledTileset",
    "convert_to_bool",
    "parse_properties",
)

logger = logging.getLogger(__name__)

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29
GID_MASK = GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT


# error message format strings go here
duplicate_name_fmt = (
    'Cannot set user {} property on {} "{}"; Tiled property already exists.'
)

flag_names = ("flipped_horizontally", "flipped_vertically", "flipped_diagonally")

AnimationFrame = namedtuple("AnimationFrame", ["gid", "duration"])
Point = namedtuple("Point", ["x", "y"])
TileFlags = namedtuple("TileFlags", flag_names)
empty_flags = TileFlags(False, False, False)
ColorLike = Union[Tuple[int, int, int, int], Tuple[int, int, int], int, str]
MapPoint = Tuple[int, int, int]

# need a more graceful way to handle annotations for optional dependencies
if pygame:
    PointLike = Union[Tuple[int, int], pygame.Vector2, Point]
else:
    PointLike = Union[Tuple[int, int], Point]


def default_image_loader(filename: str, flags, **kwargs):
    """
    This default image loader just returns filename, rect, and any flags

    Suitable for loading a map without the images

    """
    def load(rect=None, flags=None):
        return filename, rect, flags

    return load


def decode_gid(raw_gid: int) -> Tuple[int, TileFlags]:
    """
    Decode a GID from TMX data

    Args:
        raw_gid: GID, as reported by Tiled

    Returns:
        Tuple of the GID after rotation flags, and TileFlags object

    """
    if raw_gid < GID_TRANS_ROT:
        return raw_gid, empty_flags
    return (
        raw_gid & ~GID_MASK,
        # TODO: cache all combinations of flags
        TileFlags(
            raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
            raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
            raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
        ),
    )


def reshape_data(
    gids: List[int],
    width: int,
) -> List[List[int]]:
    """
    Change 1d list to 2d list

    Args:
        gids: list of gid ints
        width: width of each row

    Returns:
        2d nested list object

    """
    return [gids[i : i + width] for i in range(0, len(gids), width)]


def unpack_gids(
    text: str,
    encoding: Optional[str] = None,
    compression: Optional[str] = None,
) -> List[int]:
    """
    Return all gids from encoded/compressed layer data

    Args:
        text: layer data in text format
        encoding: encoding used
        compression: compression used

    Returns:
        list of all the GIDs in the layer

    """
    if encoding == "base64":
        data = b64decode(text)
        if compression == "gzip":
            data = gzip.decompress(data)
        elif compression == "zlib":
            data = zlib.decompress(data)
        elif compression:
            raise ValueError(f"layer compression {compression} is not supported.")
        fmt = "<%dL" % (len(data) // 4)
        return list(struct.unpack(fmt, data))
    elif encoding == "csv":
        return [int(i) for i in text.split(",")]
    elif encoding:
        raise ValueError(f"layer encoding {encoding} is not supported.")


def convert_to_bool(value: str) -> bool:
    """
    Convert a few common variations of "true" and "false" to boolean

    Args:
        value: string to test

    Raises:
        ValueError: if `value` cannot be converted to a bool
    """
    value = str(value).strip()
    if value:
        value = value.lower()[0]
        if value in ("1", "y", "t"):
            return True
        if value in ("-", "0", "n", "f"):
            return False
    else:
        return False
    raise ValueError('cannot parse "{}" as bool'.format(value))


def rotate(
    points: Sequence[Point],
    origin: Point,
    angle: Union[int, float],
) -> List[Point]:
    """
    Rotate a sequence of points around an axis

    Args:
        points: sequence of points
        origin: point where points are rotated around
        angle: angle in degrees

    Returns:
        list of rotated points

    """
    sin_t = sin(radians(angle))
    cos_t = cos(radians(angle))
    new_points = list()
    for point in points:
        p = (
            origin.x + (cos_t * (point.x - origin.x) - sin_t * (point.y - origin.y)),
            origin.y + (sin_t * (point.x - origin.x) + cos_t * (point.y - origin.y)),
        )
        new_points.append(p)
    return new_points


# used to change the unicode string returned from xml to
# proper python variable types.
types = defaultdict(lambda: str)

types.update(
    {
        "backgroundcolor": str,
        "bold": convert_to_bool,
        "color": str,
        "columns": int,
        "compression": str,
        "draworder": str,
        "duration": int,
        "encoding": str,
        "firstgid": int,
        "fontfamily": str,
        "format": str,
        "gid": int,
        "halign": str,
        "height": float,
        "hexsidelength": float,
        "id": int,
        "italic": convert_to_bool,
        "kerning": convert_to_bool,
        "margin": int,
        "name": str,
        "nextobjectid": int,
        "offsetx": int,
        "offsety": int,
        "opacity": float,
        "orientation": str,
        "pixelsize": float,
        "points": str,
        "probability": float,
        "renderorder": str,
        "rotation": float,
        "source": str,
        "spacing": int,
        "staggeraxis": str,
        "staggerindex": str,
        "strikeout": convert_to_bool,
        "terrain": str,
        "tile": int,
        "tilecount": int,
        "tiledversion": str,
        "tileheight": int,
        "tileid": int,
        "tilewidth": int,
        "trans": str,
        "type": str,
        "underline": convert_to_bool,
        "valign": str,
        "value": str,
        "version": str,
        "visible": convert_to_bool,
        "width": float,
        "wrap": convert_to_bool,
        "x": float,
        "y": float,
    }
)

# casting for properties type
prop_type = {
    "bool": convert_to_bool,
    "color": str,
    "file": str,
    "float": float,
    "int": int,
    "object": int,
    "string": str,
}


def parse_properties(node: ElementTree.Element) -> Dict:
    """
    Parse a Tiled xml node and return a dict

    Args:
        node: etree element to inspect

    Returns:
        dict of the properties, as set in the Tiled editor

    """
    d = dict()
    for child in node.findall("properties"):
        for subnode in child.findall("property"):
            cls = None
            try:
                if "type" in subnode.keys():
                    cls = prop_type[subnode.get("type")]
            except AttributeError:
                logger.info(
                    "Type {} Not a built-in type. Defaulting to string-cast.".format(
                        subnode.get("type")
                    )
                )
            d[subnode.get("name")] = subnode.get("value") or subnode.text
            if cls is not None:
                d[subnode.get("name")] = cls(subnode.get("value"))
    return d


class TiledElement:
    """
    Base class for all pytmx types

    """
    allow_duplicate_names = False

    def __init__(self):
        self.properties = dict()

    @classmethod
    def from_xml_string(cls, xml_string: str) -> TiledElement:
        """
        Return a TiledElement object from a xml string

        Args:
            xml_string: string containing xml data

        """
        return cls().parse_xml(ElementTree.fromstring(xml_string))

    def _cast_and_set_attributes_from_node_items(self, items):
        for key, value in items:
            casted_value = types[key](value)
            setattr(self, key, casted_value)

    def _contains_invalid_property_name(self, items) -> bool:
        if self.allow_duplicate_names:
            return False

        for k, v in items:
            # i'm not sure why, but this hasattr causes problems on python 2.7 with unicode
            try:
                # this will be called in py 3+
                _hasattr = hasattr(self, k)
            except UnicodeError:
                # this will be called in py 2.7
                _hasattr = hasattr(self, k.encode("utf-8"))

            if _hasattr:
                msg = duplicate_name_fmt.format(k, self.__class__.__name__, self.name)
                logger.error(msg)
                return True
        return False

    @staticmethod
    def _log_property_error_message():
        msg = "Some name are reserved for {0} objects and cannot be used."
        logger.error(msg)

    def _set_properties(self, node: ElementTree.Element) -> None:
        """
        Set properties from xml data

        Read the xml attributes and tiled "properties" from a xml node and fill
        in the values into the object's dictionary.  Names will be checked to
        make sure that they do not conflict with reserved names.

        Args:
            node: etree element

        """
        self._cast_and_set_attributes_from_node_items(node.items())
        properties = parse_properties(node)
        if not self.allow_duplicate_names and self._contains_invalid_property_name(
            properties.items()
        ):
            self._log_property_error_message()
            raise ValueError(
                "Reserved names and duplicate names are not allowed. Please rename your property inside the .tmx-file"
            )

        self.properties = properties

    def __getattr__(self, item):
        try:
            return self.properties[item]
        except KeyError:
            if self.properties.get("name", None):
                raise AttributeError(
                    "Element '{0}' has no property {1}".format(self.name, item)
                )
            else:
                raise AttributeError("Element has no property {0}".format(item))

    def __repr__(self):
        if hasattr(self, "id"):
            return '<{}[{}]: "{}">'.format(self.__class__.__name__, self.id, self.name)
        else:
            return '<{}: "{}">'.format(self.__class__.__name__, self.name)


class TiledMap(TiledElement):
    """
    Contains the layers, objects, and images from a Tiled TMX map

    """
    def __init__(
        self,
        filename: Optional[str] = None,
        image_loader=default_image_loader,
        **kwargs,
    ) -> None:
        """
        Load new Tiled map from a .tmx file

        Args:
            filename: filename of tiled map to load
            image_loader: function that will load images (see below)
            optional_gids: load specific tile image GID, even if never used
            invert_y: invert the y axis
            load_all_tiles: load all tile images, even if never used
            allow_duplicate_names: allow duplicates in objects' metadata

        """
        TiledElement.__init__(self)
        self.filename = filename
        self.image_loader = image_loader

        # optional keyword arguments checked here
        self.optional_gids = kwargs.get("optional_gids", set())
        self.load_all_tiles = kwargs.get("load_all", True)
        self.invert_y = kwargs.get("invert_y", True)

        # allow duplicate names to be parsed and loaded
        TiledElement.allow_duplicate_names = kwargs.get("allow_duplicate_names", False)

        self.layers = list()  # all layers in proper order
        self.tilesets = list()  # TiledTileset objects
        self.tile_properties = dict()  # tiles that have properties
        self.layernames = dict()
        self.objects_by_id = dict()
        self.objects_by_name = dict()

        # only used tiles are actually loaded, so there will be a difference
        # between the GIDs in the Tiled map data (tmx) and the data in this
        # object and the layers.  This dictionary keeps track of that.
        self.gidmap = defaultdict(list)
        self.imagemap = dict()  # mapping of gid and trans flags to real gids
        self.tiledgidmap = dict()  # mapping of tiledgid to pytmx gid
        self.maxgid = 1

        # should be filled in by a loader function
        self.images = list()

        # defaults from the TMX specification
        self.version = "0.0"
        self.tiledversion = ""
        self.orientation = "orthogonal"
        self.renderorder = "right-down"
        self.width = 0  # width of map in tiles
        self.height = 0  # height of map in tiles
        self.tilewidth = 0  # width of a tile in pixels
        self.tileheight = 0  # height of a tile in pixels
        self.hexsidelength = 0
        self.staggeraxis = None
        self.staggerindex = None
        self.background_color = None
        self.nextobjectid = 0

        # initialize the gid mapping
        self.imagemap[(0, 0)] = 0

        if filename:
            self.parse_xml(ElementTree.parse(self.filename).getroot())

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.filename)

    # iterate over layers and objects in map
    def __iter__(self):
        return chain(self.layers, self.objects)

    def _set_properties(self, node: ElementTree.Element) -> None:
        TiledElement._set_properties(self, node)

        # TODO: make class/layer-specific type casting
        # layer height and width must be int, but TiledElement.set_properties()
        # make a float by default, so recast as int here
        self.height = int(self.height)
        self.width = int(self.width)

    def parse_xml(self, node: ElementTree.Element):
        """
        Parse a map from ElementTree xml node

        Args:
            node: ElementTree xml node to parse

        """
        self._set_properties(node)
        self.background_color = node.get("backgroundcolor", self.background_color)

        # ***         do not change this load order!         *** #
        # ***    gid mapping errors will occur if changed    *** #
        def find_all_visible_nodes(node, node_type):
            """ Recursively find all visible nodes of the specified type

            Recurses though the ElementTree of a TMX file to find visible nodes
            by node type.  The layers can be organized in a tree structure of
            group layers.  This method recurses through any groups to find all
            such layers in the TMX file.

            :param node: ElementTree xml node
            :param node_type: Tag name of elements to find
            :return: Python list of ElementTree xml nodes
            """
            subnodes = []
            for subnode in node:
                if 'visible' in subnode.attrib and not convert_to_bool(subnode.attrib['visible']):
                    continue
                if subnode.tag == node_type:
                    subnodes.append(subnode)
                elif subnode.tag == 'group':
                    subnodes += find_all_visible_nodes(subnode, node_type)
            return subnodes

        for subnode in find_all_visible_nodes(node, 'group'):
            self.add_layer(TiledGroupLayer(self, subnode))

        for subnode in find_all_visible_nodes(node, 'layer'):
            self.add_layer(TiledTileLayer(self, subnode))

        for subnode in find_all_visible_nodes(node, 'imagelayer'):
            self.add_layer(TiledImageLayer(self, subnode))

        # this will only find objectgroup layers, not including tile colliders
        for subnode in find_all_visible_nodes(node, 'objectgroup'):
            objectgroup = TiledObjectGroup(self, subnode)
            self.add_layer(objectgroup)
            for obj in objectgroup:
                self.objects_by_id[obj.id] = obj
                self.objects_by_name[obj.name] = obj

        for subnode in node.findall(".//tileset"):
            self.add_tileset(TiledTileset(self, subnode))

        # "tile objects", objects with a GID, require their attributes to be
        # set after the tileset is loaded, so this step must be performed last
        # also, this step is performed for objects to load their tiles.

        # tiled stores the origin of GID objects by the lower right corner
        # this is different for all other types, so i just adjust it here
        # so all types loaded with pytmx are uniform.

        # iterate through tile objects and handle the image
        for o in [o for o in self.objects if o.gid]:

            # gids might also have properties assigned to them
            # in that case, assign the gid properties to the object as well
            p = self.get_tile_properties_by_gid(o.gid)
            if p:
                for key in p:
                    o.properties.setdefault(key, p[key])

            if self.invert_y:
                o.y -= o.height

        self.reload_images()
        return self

    def reload_images(self) -> None:
        """
        Load or reload the map images from disk

        This method will use the image loader passed in the constructor
        to do the loading or will use a generic default, in which case no
        images will be loaded.

        """
        self.images = [None] * self.maxgid

        # iterate through tilesets to get source images
        for ts in self.tilesets:

            # skip tilesets without a source
            if ts.source is None:
                continue

            path = os.path.join(os.path.dirname(self.filename), ts.source)
            colorkey = getattr(ts, "trans", None)
            loader = self.image_loader(path, colorkey, tileset=ts)

            p = product(
                range(
                    ts.margin,
                    ts.height + ts.margin - ts.tileheight + 1,
                    ts.tileheight + ts.spacing,
                ),
                range(
                    ts.margin,
                    ts.width + ts.margin - ts.tilewidth + 1,
                    ts.tilewidth + ts.spacing,
                ),
            )

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
                # else:
                #     # not used in layer data give another chance to load the tile anyway
                #     if self.load_all_tiles or real_gid in self.optional_gids:
                #         # TODO: handle flags? - might never be an issue, though
                #         self.register_gid(real_gid, flags=0)

        # load image layer images
        for layer in (i for i in self.layers if isinstance(i, TiledImageLayer)):
            source = getattr(layer, "source", None)
            if source:
                colorkey = getattr(layer, "trans", None)
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
            source = props.get("source", None)
            if source:
                colorkey = props.get("trans", None)
                path = os.path.join(os.path.dirname(self.filename), source)
                loader = self.image_loader(path, colorkey)
                image = loader()
                self.images[real_gid] = image

    def get_tile_image(self, x: int, y: int, layer: int):
        """
        Return the tile image for this location

        Args:
            x: x coordinate
            y: y coordinate
            layer: layer number

        Returns:
            the image object type will depend on the loader (ie. pygame surface)

        Raises:
            TypeError: if coordinates are not integers
            ValueError: if the coordinates are out of bounds, or GID not found

        """
        if not (x >= 0 and y >= 0):
            raise ValueError(
                "Tile coordinates must be non-negative, were ({0}, {1})".format(x, y)
            )

        try:
            layer = self.layers[layer]
        except IndexError:
            raise ValueError("Layer not found")

        assert isinstance(layer, TiledTileLayer)

        try:
            gid = layer.data[y][x]
        except (IndexError, ValueError):
            raise ValueError("GID not found")
        except TypeError:
            msg = "Tiles must be specified in integers."
            logger.debug(msg)
            raise TypeError(msg)

        else:
            return self.get_tile_image_by_gid(gid)

    def get_tile_image_by_gid(self, gid: int):
        """
        Return the tile image for this location

        Args:
            gid: GID of image

        Returns:
            the image object type will depend on the loader (ie. pygame surface)

        Raises:
            TypeError: if `gid` is not an integer
            ValueError: if there is no image for this GID

        """
        try:
            assert int(gid) >= 0
            return self.images[gid]
        except TypeError:
            msg = "GIDs must be expressed as a number.  Got: {0}"
            logger.debug(msg.format(gid))
            raise TypeError(msg.format(gid))
        except (AssertionError, IndexError):
            msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
            logger.debug(msg.format(gid))
            raise ValueError(msg.format(gid))

    def get_tile_gid(self, x: int, y: int, layer: int) -> int:
        """
        Return the tile image GID for this location

        Args:
            x: x coordinate
            y: y coordinate
            layer: layer number

        Returns:
            the image object type will depend on the loader (ie. pygame surface)

        Raises:
            ValueError: if coordinates are out of bounds

        """
        if not (x >= 0 and y >= 0 and layer >= 0):
            raise ValueError(
                "Tile coordinates and layers must be non-negative, were ({0}, {1}), layer={2}".format(
                    x, y, layer
                )
            )

        try:
            return self.layers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid"
            logger.debug(msg.format(x, y, layer))
            raise ValueError(msg.format(x, y, layer))

    def get_tile_properties(self, x: int, y: int, layer: int) -> Optional[Dict]:
        """
        Return the tile image GID for this location

        Args:
            x: x coordinate
            y: y coordinate
            layer: layer number

        Returns:
            dict of the properties for tile in this location, or None

        Raises:
            ValueError: if coordinates are out of bounds

        """
        if not (x >= 0 and y >= 0 and layer >= 0):
            raise ValueError(
                "Tile coordinates and layers must be non-negative, were ({0}, {1}), layer={2}".format(
                    x, y, layer
                )
            )

        try:
            gid = self.layers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            logger.debug(msg.format(x, y, layer))
            raise Exception(msg.format(x, y, layer))

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
                logger.debug(msg.format(x, y, layer, gid))
                raise Exception(msg.format(x, y, layer, gid))
            except KeyError:
                return None

    def get_tile_locations_by_gid(self, gid: int) -> Iterable[MapPoint]:
        """
        Search map for tile locations by the GID

        Return (int, int, int) tuples, where the layer is index of
        the visible tile layers.

        Note: Not a fast operation.  Cache results if used often.

        Args:
            gid: GID to be searched for

        """
        for l in self.visible_tile_layers:
            for x, y, _gid in [i for i in self.layers[l].iter_data() if i[2] == gid]:
                yield x, y, l

    def get_tile_properties_by_gid(self, gid: int) -> Optional[Dict]:
        """
        Get the tile properties of a tile GID

        Args:
            gid: GID

        Returns:
            dict of properties for GID, or None

        """
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

    def set_tile_properties(self, gid: int, properties: dict) -> None:
        """
        Set the tile properties of a tile GID

        Args:
            gid: GID
            properties: python dict of properties for GID

        """
        self.tile_properties[gid] = properties

    def get_tile_properties_by_layer(self, layer: int):
        """
        Get the tile properties of each GID in layer

        Args:
            layer: layer number

        """
        try:
            assert int(layer) >= 0
            layer = int(layer)
        except (TypeError, AssertionError):
            msg = "Layer must be a positive integer.  Got {0} instead."
            logger.debug(msg.format(type(layer)))
            raise ValueError

        p = product(range(self.width), range(self.height))
        layergids = set(self.layers[layer].data[y][x] for x, y in p)

        for gid in layergids:
            try:
                yield gid, self.tile_properties[gid]
            except KeyError:
                continue

    def add_layer(
        self,
        layer: Union[
            TiledTileLayer, TiledImageLayer, TiledGroupLayer, TiledObjectGroup
        ],
    ) -> None:
        """
        Add a layer to the map

        """
        assert isinstance(
            layer, (TiledGroupLayer, TiledTileLayer, TiledImageLayer, TiledObjectGroup)
        )

        self.layers.append(layer)
        self.layernames[layer.name] = layer

    def add_tileset(self, tileset: TiledTileset) -> None:
        """
        Add a tileset to the map

        """
        assert isinstance(tileset, TiledTileset)
        self.tilesets.append(tileset)

    def get_layer_by_name(self, name: str):
        """
        Return a layer by name

        Args:
            name: Name of layer.  Case-sensitive.

        Raises:
            ValueError: if layer by name does not exist

        """
        try:
            return self.layernames[name]
        except KeyError:
            msg = 'Layer "{0}" not found.'
            logger.debug(msg.format(name))
            raise ValueError(msg.format(name))

    def get_object_by_id(self, obj_id: int) -> TiledObject:
        """
        Find an object by the object id

        Args:
            obj_id: ID of the object, from Tiled

        """
        return self.objects_by_id[obj_id]

    def get_object_by_name(self, name) -> TiledObject:
        """
        Find an object by name, case-sensitive

        Args:
            name: name of object

        """
        return self.objects_by_name[name]

    def get_tileset_from_gid(self, gid: int) -> TiledTileset:
        """
        Return tileset that owns the gid

        Note: this is a slow operation, so if you are expecting to do this
              often, it would be worthwhile to cache the results of this.

        Args:
            gid: gid of tile image

        Raises:
            ValueError: if the tileset for gid is not found

        """
        try:
            tiled_gid = self.tiledgidmap[gid]
        except KeyError:
            raise ValueError("Tile GID not found")

        for tileset in sorted(self.tilesets, key=attrgetter("firstgid"), reverse=True):
            if tiled_gid >= tileset.firstgid:
                return tileset

        raise ValueError("Tileset not found")

    def get_tile_colliders(self) -> Iterable[Tuple[int, List[Dict]]]:
        """
        Return iterator of (gid, dict) pairs of tiles with colliders

        """
        for gid, props in self.tile_properties.items():
            colliders = props.get("colliders")
            if colliders:
                yield gid, colliders

    @property
    def objectgroups(self) -> Iterable[TiledObjectGroup]:
        """
        Return iterator of all object groups

        """
        return (layer for layer in self.layers if isinstance(layer, TiledObjectGroup))

    @property
    def objects(self) -> Iterable[TiledObject]:
        """
        Return iterator of all the objects associated with this map

        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """
        Return iterator of Layer objects that are set 'visible'

        """
        return (l for l in self.layers if l.visible)

    @property
    def visible_tile_layers(self) -> Iterable[TiledTileLayer]:
        """
        Return iterator of layer indexes that are set 'visible'

        """
        return (
            i
            for (i, l) in enumerate(self.layers)
            if l.visible and isinstance(l, TiledTileLayer)
        )

    @property
    def visible_object_groups(self) -> Iterable[TiledObjectGroup]:
        """
        Return iterator of object group indexes that are set 'visible'

        """
        return (
            i
            for (i, l) in enumerate(self.layers)
            if l.visible and isinstance(l, TiledObjectGroup)
        )

    def register_gid(
        self,
        tiled_gid: int,
        flags: Optional[TileFlags] = None,
    ) -> int:
        """
        Used to manage the mapping of GIDs between the tmx and pytmx

        Args:
            tiled_gid: GID that is found in TMX data
            flags: TileFlags

        Returns:
            New or existing GID for pytmx use

        """
        if flags is None:
            flags = TileFlags(0, 0, 0)

        if tiled_gid:
            try:
                return self.imagemap[(tiled_gid, flags)][0]
            except KeyError:
                gid = self.maxgid
                self.maxgid += 1
                self.imagemap[(tiled_gid, flags)] = (gid, flags)
                self.gidmap[tiled_gid].append((gid, flags))
                self.tiledgidmap[gid] = tiled_gid
                return gid

        else:
            return 0

    def map_gid(self, tiled_gid: int) -> Optional[List[int]]:
        """
        Used to lookup a GID read from a TMX file's data

        Args:
            tiled_gid: GID that is found in TMX data

        """
        try:
            return self.gidmap[int(tiled_gid)]
        except KeyError:
            return None
        except TypeError:
            msg = "GIDs must be an integer"
            logger.debug(msg)
            raise TypeError(msg)

    def map_gid2(self, tiled_gid: int) -> List[Tuple[int, Optional[int]]]:
        """
        WIP.  need to refactor the gid code

        """
        tiled_gid = int(tiled_gid)

        # gidmap is a default dict, so cannot trust to raise KeyError
        if tiled_gid in self.gidmap:
            return self.gidmap[tiled_gid]
        else:
            gid = self.register_gid(tiled_gid)
            return [(gid, None)]


class TiledTileset(TiledElement):
    """
    Represents a Tiled Tileset

    External tilesets are supported.  GID/ID's from Tiled are not
    guaranteed to be the same after loaded.

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent
        self.offset = (0, 0)

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0
        self.tilecount = 0
        self.columns = 0

        # image properties
        self.trans = None
        self.width = 0
        self.height = 0

        self.parse_xml(node)

    def parse_xml(self, node):
        """
        Parse a Tileset from ElementTree xml element

        A bit of mangling is done here so that tilesets that have
        external TSX files appear the same as those that don't.

        Args:
            node: node to parse

        """
        # if true, then node references an external tileset
        source = node.get("source", None)
        if source:
            if source[-4:].lower() == ".tsx":

                # external tilesets don't save this, store it for later
                self.firstgid = int(node.get("firstgid"))

                # we need to mangle the path - tiled stores relative paths
                dirname = os.path.dirname(self.parent.filename)
                path = os.path.abspath(os.path.join(dirname, source))
                if not os.path.exists(path):
                    # raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), path)
                    raise Exception(
                        "Cannot find tileset file {0} from {1}, should be at {2}".format(
                            source, self.parent.filename, path
                        )
                    )

                try:
                    node = ElementTree.parse(path).getroot()
                except IOError as io:
                    msg = "Error loading external tileset: {0}"
                    logger.error(msg.format(path))
                    raise Exception(msg.format(path)) from io
            else:
                msg = "Found external tileset, but cannot handle type: {0}"
                logger.error(msg.format(self.source))
                raise Exception(msg.format(self.source))

        self._set_properties(node)

        # since tile objects [probably] don't have a lot of metadata,
        # we store it separately in the parent (a TiledMap instance)
        register_gid = self.parent.register_gid
        for child in node.iter("tile"):
            tiled_gid = int(child.get("id"))

            p = {k: types[k](v) for k, v in child.items()}
            p.update(parse_properties(child))

            # images are listed as relative to the .tsx file, not the .tmx file:
            if source and "path" in p:
                p["path"] = os.path.join(os.path.dirname(source), p["path"])

            # handle tiles that have their own image
            image = child.find("image")
            if image is None:
                p["width"] = self.tilewidth
                p["height"] = self.tileheight
            else:
                tile_source = image.get("source")
                # images are listed as relative to the .tsx file, not the .tmx file:
                if source and tile_source:
                    tile_source = os.path.join(os.path.dirname(source), tile_source)
                p["source"] = tile_source
                p["trans"] = image.get("trans", None)
                p["width"] = image.get("width", None)
                p["height"] = image.get("height", None)

            # handle tiles with animations
            anim = child.find("animation")
            frames = list()
            p["frames"] = frames
            if anim is not None:
                for frame in anim.findall("frame"):
                    duration = int(frame.get("duration"))
                    gid = register_gid(int(frame.get("tileid")) + self.firstgid)
                    frames.append(AnimationFrame(gid, duration))

            for objgrp_node in child.findall("objectgroup"):
                objectgroup = TiledObjectGroup(self.parent, objgrp_node)
                p["colliders"] = objectgroup

            for gid, flags in self.parent.map_gid2(tiled_gid + self.firstgid):
                self.parent.set_tile_properties(gid, p)

        # handle the optional 'tileoffset' node
        self.offset = node.find("tileoffset")
        if self.offset is None:
            self.offset = (0, 0)
        else:
            self.offset = (self.offset.get("x", 0), self.offset.get("y", 0))

        image_node = node.find("image")
        if image_node is not None:
            self.source = image_node.get("source")

            # When loading from tsx, tileset image path is relative to the tsx file, not the tmx:
            if source:
                self.source = os.path.join(os.path.dirname(source), self.source)

            self.trans = image_node.get("trans", None)
            self.width = int(image_node.get("width"))
            self.height = int(image_node.get("height"))

        return self


class TiledGroupLayer(TiledElement):
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent
        self.name = None
        self.visible = 1
        self.parse_xml(node)

    def parse_xml(self, node):
        """
        Parse a TiledGroup Layer from ElementTree xml node

        Args:
            node: node to parse

        """
        self._set_properties(node)
        self.name = node.get("name", None)
        return self


class TiledTileLayer(TiledElement):
    """
    Represents a TileLayer

    To just get the tile images, use TiledTileLayer.tiles()

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent
        self.data = list()

        # defaults from the specification
        self.name = None
        self.width = 0
        self.height = 0
        self.opacity = 1.0
        self.visible = True
        self.offsetx = 0
        self.offsety = 0

        self.parse_xml(node)

    def __iter__(self):
        return self.iter_data()

    def iter_data(self) -> Iterable[Tuple[int, int, int]]:
        """
        Yields X, Y, GID tuples for each tile in the layer

        Returns:
            Iterator of X, Y, GID tuples for each tile in the layer

        """
        for y, row in enumerate(self.data):
            for x, gid in enumerate(row):
                yield x, y, gid

    def tiles(self):
        """
        Yields X, Y, Image tuples for each tile in the layer

        Returns:
            Iterator of X, Y, Image tuples for each tile in the layer

        """
        images = self.parent.images
        for x, y, gid in [i for i in self.iter_data() if i[2]]:
            yield x, y, images[gid]

    def _set_properties(self, node):
        TiledElement._set_properties(self, node)

        # TODO: make class/layer-specific type casting
        # layer height and width must be int, but TiledElement.set_properties()
        # make a float by default, so recast as int here
        self.height = int(self.height)
        self.width = int(self.width)

    def parse_xml(self, node: ElementTree.Element):
        """
        Parse a Tile Layer from ElementTree xml node

        Args:
            node: node to parse

        """
        self._set_properties(node)
        data_node = node.find("data")
        chunk_nodes = data_node.findall("chunk")
        if chunk_nodes:
            msg = "TMX map size: infinite is not supported."
            logger.error(msg)
            raise Exception

        child = data_node.find("tile")
        if child is not None:
            raise ValueError(
                "XML tile elements are no longer supported. Must use base64 or csv map formats."
            )

        reg = self.parent.register_gid
        temp = list()
        temp_append = temp.append
        for gid in unpack_gids(
            text=data_node.text.strip(),
            encoding=data_node.get("encoding", None),
            compression=data_node.get("compression", None),
        ):
            if gid == 0:
                temp_append(0)
            elif gid < GID_TRANS_ROT:
                gid = reg(gid)
                temp_append(gid)
            else:
                gid, flags = decode_gid(gid)
                gid = reg(gid, flags)
                temp_append(gid)

        self.data = reshape_data(temp, self.width)
        return self


class TiledObjectGroup(TiledElement, list):
    """Represents a Tiled ObjectGroup

    Supports any operation of a normal list.

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent

        # defaults from the specification
        self.name = None
        self.color = None
        self.opacity = 1
        self.visible = 1
        self.offsetx = 0
        self.offsety = 0
        self.draworder = "index"

        self.parse_xml(node)

    def parse_xml(self, node: ElementTree.Element):
        """
        Parse an Object Group from ElementTree xml node

        Args:
            node: node to parse

        """
        self._set_properties(node)
        self.extend(TiledObject(self.parent, child) for child in node.findall("object"))

        return self


class TiledObject(TiledElement):
    """Represents any Tiled Object

    Supported types: Box, Ellipse, Tile Object, Polyline, Polygon

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent

        # defaults from the specification
        self.id = 0
        self.name = None
        self.type = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.rotation = 0
        self.gid = 0
        self.visible = 1
        self.closed = True
        self.template = None

        self.parse_xml(node)

    @property
    def image(self):
        """
        Image for the object, if assigned

        Returns:
            the image object type will depend on the loader (ie. pygame surface)

        """
        if self.gid:
            return self.parent.images[self.gid]
        return None

    def parse_xml(self, node: ElementTree.Element):
        """
        Parse an Object from ElementTree xml node

        Args:
            node: the node to be parsed

        """
        def read_points(text):
            """
            Parse a text string of float tuples and return [(x,...),...]

            """
            return tuple(tuple(map(float, i.split(","))) for i in text.split())

        self._set_properties(node)

        # correctly handle "tile objects" (object with gid set)
        if self.gid:
            self.gid = self.parent.register_gid(self.gid)

        points = None
        polygon = node.find("polygon")
        if polygon is not None:
            points = read_points(polygon.get("points"))
            self.closed = True

        polyline = node.find("polyline")
        if polyline is not None:
            points = read_points(polyline.get("points"))
            self.closed = False

        if points:
            x1 = x2 = y1 = y2 = 0
            for x, y in points:
                if x < x1:
                    x1 = x
                if x > x2:
                    x2 = x
                if y < y1:
                    y1 = y
                if y > y2:
                    y2 = y
            self.width = abs(x1) + abs(x2)
            self.height = abs(y1) + abs(y2)
            self.points = tuple([Point(i[0] + self.x, i[1] + self.y) for i in points])

        return self

    def apply_transformations(self):
        """
        Return all points for object, taking in account rotation

        """
        if hasattr(self, "points"):
            return rotate(self.points, self, self.rotation)
        else:
            return rotate(self.as_points, self, self.rotation)

    @property
    def as_points(self):
        return [
            Point(*i)
            for i in [
                (self.x, self.y),
                (self.x, self.y + self.height),
                (self.x + self.width, self.y + self.height),
                (self.x + self.width, self.y),
            ]
        ]


class TiledImageLayer(TiledElement):
    """
    Represents Tiled Image Layer

    The image associated with this layer will be loaded and assigned a GID.

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent
        self.source = None
        self.trans = None
        self.gid = 0

        # defaults from the specification
        self.name = None
        self.opacity = 1
        self.visible = 1

        self.parse_xml(node)

    @property
    def image(self):
        """
        Image for the object, if assigned

        Returns:
            the image object type will depend on the loader (ie. pygame surface)

        """
        if self.gid:
            return self.parent.images[self.gid]
        return None

    def parse_xml(self, node: ElementTree.Element):
        """
        Parse an Image Layer from ElementTree xml node

        """
        self._set_properties(node)
        self.name = node.get("name", None)
        self.opacity = node.get("opacity", self.opacity)
        self.visible = node.get("visible", self.visible)
        image_node = node.find("image")
        self.source = image_node.get("source", None)
        self.trans = image_node.get("trans", None)
        return self


class TiledProperty(TiledElement):
    """
    Represents Tiled Property

    """
    def __init__(self, parent, node):
        TiledElement.__init__(self)

        # defaults from the specification
        self.name = None
        self.type = None
        self.value = None

        self.parse_xml(node)

    def parse_xml(self, node):
        pass
