from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import chain
from typing import Union, Iterator, List, Dict

logger = logging.getLogger(__file__)

TileImageType = Union[None, str]


@dataclass
class Tile:
    gid: int
    id: int = None
    type: str = None
    terrain: str = None
    # mason
    image: TileImageType = None  # this will be the image/surface
    properties: dict = field(default_factory=dict)
    animation: Animation = None
    offsety: int = 0

    def calc_blit_offset(self, tileheight):
        self.offsety = tileheight - self.image.get_height()


@dataclass
class TileLayer:
    name: str
    opacity: float
    visible: bool
    tintcolor: str
    offsetx: int
    offsety: int
    data: list

    def tiles(self):
        for y, row in enumerate(self.data):
            for x, tile in enumerate(row):
                if tile:
                    yield x, y, tile


@dataclass
class Map:
    version: str
    orientation: str
    renderorder: str
    compressionlevel: str
    width: int
    height: int
    tilewidth: int
    tileheight: int
    hexsidelength: int
    staggeraxis: str
    staggerindex: str
    background_color: str
    infinite: bool
    filename: str = None
    layers: List = field(default_factory=list)
    images: List = field(default_factory=list)
    properties: Dict = field(default_factory=dict)
    tiles: Dict = field(default_factory=dict)

    def get_layer_by_name(self, name):
        """Return a layer by name"""
        for layer in self.layers:
            if layer.name == name:
                return layer
        raise ValueError(f'Layer "{name}" not found')

    def get_object_by_name(self, name):
        """Find an object by name"""
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise ValueError(f'Object "{name}" not found')

    def get_tile(self, x, y, layer) -> int:
        """Return the tile for this location"""
        try:
            assert x >= 0 and y >= 0 and layer >= 0
        except (AssertionError, ValueError, TypeError):
            raise ValueError(
                f"Tile coordinates and layers must be non-negative, were ({x}, {y}), layer={layer}"
            )
        try:
            layer = self.layers[layer]
        except IndexError:
            raise ValueError(f"Layer not found: {layer}")
        try:
            return layer.data[y][x]
        except IndexError:
            raise ValueError(f"Tile coordinates ({x},{y}) in layer {layer} are invalid")

    def get_tile_by_gid(self, gid: int) -> TileImageType:
        """Return the tile by gid"""
        try:
            return self.tiles[gid]
        except TypeError:
            raise TypeError(f"GIDs must be expressed as a number.  Got: {gid}")
        except IndexError:
            raise ValueError(f"GID not found: {gid}")

    def get_tile_locations_by_gid(self, gid: int) -> Iterator[MapCoordinates]:
        """Search map for tile locations by the GID

        Note: Not a fast operation.  Cache results if used often.
        """
        for l in self.tile_layers():
            for x, y, _gid in [i for i in self.layers[l].iter_data() if i[2] == gid]:
                yield MapCoordinates(x, y, l)

    @property
    def objectgroups(self):
        """Return iterator of all object groups

        :rtype: Iterator
        """
        return (layer for layer in self.layers if isinstance(layer, ObjectGroup))

    @property
    def objects(self):
        """Return iterator of all the objects associated with this map

        :rtype: Iterator
        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """Return iterator of Layer objects that are set 'visible'

        :rtype: Iterator
        """
        return (l for l in self.layers if l.visible)

    def tile_layers(self, include_invisible=False):
        layers = (layer for layer in self.layers if isinstance(layer, TileLayer))
        if include_invisible:
            return layers
        else:
            return (layer for layer in layers if layer.visible)

    @property
    def visible_object_groups(self):
        """Return iterator of object group indexes that are set 'visible'

        :rtype: Iterator
        """
        return (
            i
            for (i, l) in enumerate(self.layers)
            if l.visible and isinstance(l, TiledObjectGroup)
        )

    def tile_properties(self):
        for layer in self.tile_layers:
            for tile in layer.tiles:
                if tile.properties:
                    yield tile, tile.properties

@dataclass
class MapCoordinates:
    x: int
    y: int
    layer: TileLayer


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Text:
    fontfamily: str
    pixelsize: int
    wrap: bool
    color: str
    bold: bool
    italic: bool
    underline: bool
    strikeout: bool
    kerning: bool
    halign: str
    valign: str


@dataclass
class Animation:
    frames: List[AnimationFrame]


@dataclass
class AnimationFrame:
    tile: Tile
    duration: int


# Ellipse is a reserved python word, renaming to circle
@dataclass
class Circle:
    pass


@dataclass
class Image:
    source: str
    width: int
    height: int
    trans: str


@dataclass
class ObjectGroup:
    name: str
    color: str
    opacity: float
    visible: bool
    tintcolor: str
    offsetx: int
    offsety: int
    draworder: int
    # mason
    objects: List = field(default_factory=list)

    def __iter__(self):
        return iter(self.objects)


@dataclass
class Group:
    name: str
    opacity: float
    visible: bool
    tintcolor: str
    offsetx: int
    offsety: int
    # mason
    layers: List = field(default_factory=list)


@dataclass
class Tileset:
    firstgid: int
    source: str
    name: str
    tilewidth: int
    tileheight: int
    spacing: int
    margin: int
    tilecount: int
    columns: int
    objectalignment: str
    # mason
    orientation: str = None
    images: List = field(default_factory=list)
    tiles: List = field(default_factory=list)


@dataclass
class Polygon:
    points: List


@dataclass
class Polyline:
    points: List


@dataclass
class Object:
    name: str
    type: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    gid: int
    visible: bool
    # mason
    image: Image = None
    shapes: list = field(default_factory=list)

    @property
    def as_points(self):
        return [
            Point(*i)
            for i in [
                (self.x, self.y),
                (self.x, self.y - self.height),
                (self.x + self.width, self.y - self.height),
                (self.x + self.width, self.y),
            ]
        ]

    @property
    def points(self):
        if self.width and self.height:
            if self.image:
                return [
                    (self.x, self.y - self.height),
                    (self.x + self.width, self.y - self.height),
                    (self.x + self.width, self.y),
                    (self.x, self.y),
                ]
            else:
                return [
                    (self.x, self.y),
                    (self.x + self.width, self.y),
                    (self.x + self.width, self.y + self.height),
                    (self.x, self.y + self.height),
                ]
        else:
            return [(self.x, self.y)]


@dataclass
class Property:
    name: str
    type: str
    value: str


@dataclass
class ImageLayer:
    name: str
    visible: bool
    image: Image
