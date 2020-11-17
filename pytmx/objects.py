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
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import chain
from math import sin, radians, cos
from typing import Union, Iterator, List, Dict

TileImageType = Union[None, str]


def rotate(points, origin, angle):
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


@dataclass
class Tile:
    gid: int
    id: int = None
    type: str = None
    terrain: str = None
    # mason
    collider_group: ObjectGroup = None
    image: TileImageType = None  # this will be the image/surface
    properties: dict = field(default_factory=dict)
    animation: Animation = None
    offsety: int = 0
    flipped_h: bool = False
    flipped_v: bool = False
    flipped_d: bool = False

    def calc_blit_offset(self, tileheight):
        self.offsety = tileheight - self.image.get_height()


@dataclass
class Chunk:
    x: int
    y: int
    width: int
    height: int


@dataclass
class TileLayer:
    name: str
    opacity: float
    visible: bool
    tintcolor: str
    offsetx: int
    offsety: int
    data: list

    def __iter__(self):
        yield from self.tiles()

    def tiles(self):
        for y, row in enumerate(self.data):
            for x, tile in enumerate(row):
                if tile:
                    yield x, y, tile

    def get_tile(self, x, y):
        try:
            return self.data[y][x]
        except IndexError:
            raise ValueError(f"Tile coordinates ({x},{y} are invalid")


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

    def __iter__(self):
        for layer in self.layers:
            yield from layer

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
                f"Tile coordinates must be non-negative, were ({x}, {y}), layer={layer}"
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

    def get_tile_locations_by_tile(self, tile: Tile) -> Iterator[MapCoordinates]:
        """Search map for tile locations by the tile

        Note: Not a fast operation.  Cache results if used often.
        """
        for l in self.tile_layers():
            for x, y, _tile in [t for t in l.tiles() if t == tile]:
                yield MapCoordinates(x, y, _tile)

    @property
    def objectgroups(self):
        """Return iterator of all object groups
        """
        return (layer for layer in self.layers if isinstance(layer, ObjectGroup))

    @property
    def objects(self):
        """Return iterator of all the objects associated with this map
        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """Return iterator of Layer objects that are set 'visible'

        :rtype: Iterator
        """
        return (l for l in self.layers if l.visible)

    def tile_layers(self, include_invisible=False):
        """Return iterator of layers"""
        layers = (layer for layer in self.layers if isinstance(layer, TileLayer))
        if include_invisible:
            return layers
        else:
            return (layer for layer in layers if layer.visible)

    def object_groups(self, include_invisible=False):
        """Return iterator of object groups"""
        layers = (layer for layer in self.layers if isinstance(layer, TileLayer))
        if include_invisible:
            return layers
        else:
            return (layer for layer in layers if layer.visible)

    def tile_properties(self):
        """Return iterator of tiles which have properties assigned to them"""
        for tile in self.tiles:
            if tile.properties:
                yield tile


@dataclass
class MapCoordinates:
    x: int
    y: int
    layer: TileLayer


@dataclass
class Point:
    x: int
    y: int

    def __getitem__(self, index):
        return (self.x, self.y)[index]


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
        yield from self.objects


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

    def __iter__(self):
        for layer in self.layers:
            yield from layer


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

    def render(self):
        """Return all points for object, taking in account rotation"""
        return rotate(self.as_points, self, self.rotation)

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

    def __iter__(self):
        yield self.image
