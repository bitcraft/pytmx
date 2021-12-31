# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2017, Leif Theden <leif.theden@gmail.com>

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
import itertools
import logging
from typing import Optional, Union, List

import pytmx
from pytmx.pytmx import ColorLike, PointLike

logger = logging.getLogger(__name__)

try:
    from pygame.transform import flip, rotate
    import pygame
except ImportError:
    logger.error("cannot import pygame (is it installed?)")
    raise

__all__ = ["load_pygame", "pygame_image_loader", "simplify", "build_rects"]


def handle_transformation(
    tile: pygame.Surface,
    flags: pytmx.TileFlags,
) -> pygame.Surface:
    """
    Transform tile according to the flags and return a new one

    Parameters:
        tile: tile surface to transform
        flags: TileFlags object

    Returns:
        new tile surface

    """
    if flags.flipped_diagonally:
        tile = flip(rotate(tile, 270), True, False)
    if flags.flipped_horizontally or flags.flipped_vertically:
        tile = flip(tile, flags.flipped_horizontally, flags.flipped_vertically)
    return tile


def smart_convert(
    original: pygame.Surface,
    colorkey: Optional[ColorLike],
    pixelalpha: bool,
) -> pygame.Surface:
    """
    Return new pygame Surface with optimal pixel/data format

    This method does several interactive_tests on a surface to determine the optimal
    flags and pixel format for each tile surface.

    Parameters:
        original: tile surface to inspect
        colorkey: optional colorkey for the tileset image
        pixelalpha: if true, prefer per-pixel alpha surfaces

    Returns:
        new tile surface

    """
    # tiled set a colorkey
    if colorkey:
        tile = original.convert()
        tile.set_colorkey(colorkey, pygame.RLEACCEL)
        # TODO: if there is a colorkey, count the colorkey pixels to determine if RLEACCEL should be used

    # no colorkey, so use a mask to determine if there are transparent pixels
    else:
        tile_size = original.get_size()
        threshold = 254  # the default

        try:
            # count the number of pixels in the tile that are not transparent
            px = pygame.mask.from_surface(original, threshold).count()
        except:
            # pygame_sdl2 will fail because the mask module is not included
            # in this case, just convert_alpha and return it
            return original.convert_alpha()

        # there are no transparent pixels in the image
        if px == tile_size[0] * tile_size[1]:
            tile = original.convert()

        # there are transparent pixels, and set for perpixel alpha
        elif pixelalpha:
            tile = original.convert_alpha()

        # there are transparent pixels, and we won't handle them
        else:
            tile = original.convert()

    return tile


def pygame_image_loader(filename: str, colorkey: Optional[ColorLike], **kwargs):
    """
    pytmx image loader for pygame

    Parameters:
        filename: filename, including path, to load
        colorkey: colorkey for the image

    Returns:
        function to load tile images

    """
    if colorkey:
        colorkey = pygame.Color("#{0}".format(colorkey))

    pixelalpha = kwargs.get("pixelalpha", True)
    image = pygame.image.load(filename)

    def load_image(rect=None, flags=None):
        if rect:
            try:
                tile = image.subsurface(rect)
            except ValueError:
                logger.error("Tile bounds outside bounds of tileset image")
                raise
        else:
            tile = image.copy()

        if flags:
            tile = handle_transformation(tile, flags)

        tile = smart_convert(tile, colorkey, pixelalpha)
        return tile

    return load_image


def load_pygame(
    filename: str,
    *args,
    **kwargs,
) -> pytmx.TiledMap:
    """Load a TMX file, images, and return a TiledMap class

    PYGAME USERS: Use me.

    this utility has 'smart' tile loading.  by default any tile without
    transparent pixels will be loaded for quick blitting.  if the tile has
    transparent pixels, then it will be loaded with per-pixel alpha.  this is
    a per-tile, per-image check.

    if a color key is specified as an argument, or in the tmx data, the
    per-pixel alpha will not be used at all. if the tileset's image has colorkey
    transparency set in Tiled, the util_pygam will return images that have their
    transparency already set.

    TL;DR:
    Don't attempt to convert() or convert_alpha() the individual tiles.  It is
    already done for you.

    Parameters:
        filename: filename to load

    Returns:
        new pytmx.TiledMap object

    """
    kwargs["image_loader"] = pygame_image_loader
    return pytmx.TiledMap(filename, *args, **kwargs)


def build_rects(
    tmxmap: pytmx.TiledMap,
    layer: Union[int, str],
    tileset: Optional[Union[int, str]],
    real_gid: Optional[int],
) -> List[pygame.Rect]:
    """
    Generate a set of non-overlapping rects that represents the distribution of the specified gid.

    Useful for generating rects for use in collision detection

    GID Note: You will need to add 1 to the GID reported by Tiled.

    Parameters:
        tmxmap: TiledMap object
        layer: int or string name of layer
        tileset: int or string name of tileset
        real_gid: Tiled GID of the tile + 1 (see note)

    Returns:
        list of pygame Rect objects

    """
    if isinstance(tileset, int):
        try:
            tileset = tmxmap.tilesets[tileset]
        except IndexError:
            msg = "Tileset #{0} not found in map {1}."
            logger.debug(msg.format(tileset, tmxmap))
            raise IndexError

    elif isinstance(tileset, str):
        try:
            tileset = [t for t in tmxmap.tilesets if t.name == tileset].pop()
        except IndexError:
            msg = 'Tileset "{0}" not found in map {1}.'
            logger.debug(msg.format(tileset, tmxmap))
            raise ValueError

    elif tileset:
        msg = "Tileset must be either a int or string. got: {0}"
        logger.debug(msg.format(type(tileset)))
        raise TypeError

    gid = None
    if real_gid:
        try:
            gid, flags = tmxmap.map_gid(real_gid)[0]
        except IndexError:
            msg = "GID #{0} not found"
            logger.debug(msg.format(real_gid))
            raise ValueError

    if isinstance(layer, int):
        layer_data = tmxmap.get_layer_data(layer)
    elif isinstance(layer, str):
        try:
            layer = [l for l in tmxmap.layers if l.name == layer].pop()
            layer_data = layer.data
        except IndexError:
            msg = 'Layer "{0}" not found in map {1}.'
            logger.debug(msg.format(layer, tmxmap))
            raise ValueError

    p = itertools.product(range(tmxmap.width), range(tmxmap.height))
    if gid:
        points = [(x, y) for (x, y) in p if layer_data[y][x] == gid]
    else:
        points = [(x, y) for (x, y) in p if layer_data[y][x]]

    rects = simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects


def simplify(
    all_points: List[PointLike],
    tilewidth: int,
    tileheight: int,
) -> List[pygame.Rect]:
    """Given a list of points, return list of rects that represent them
    kludge:

    "A kludge (or kluge) is a workaround, a quick-and-dirty solution,
    a clumsy or inelegant, yet effective, solution to a problem, typically
    using parts that are cobbled together."

    -- wikipedia

    turn a list of points into a rects
    adjacent rects will be combined.

    plain english:
        the input list must be a list of tuples that represent
        the areas to be combined into rects
        the rects will be blended together over solid groups

        so if data is something like:

        0 1 1 1 0 0 0
        0 1 1 0 0 0 0
        0 0 0 0 0 4 0
        0 0 0 0 0 4 0
        0 0 0 0 0 0 0
        0 0 1 1 1 1 1

        you'll have the 4 rects that mask the area like this:

        ..######......
        ..####........
        ..........##..
        ..........##..
        ..............
        ....##########

        pretty cool, right?

    there may be cases where the number of rectangles is not as low as possible,
    but I haven't found that it is excessively bad.  certainly much better than
    making a list of rects, one for each tile on the map!
    """

    def pick_rect(points, rects):
        ox, oy = sorted([(sum(p), p) for p in points])[0][1]
        x = ox
        y = oy
        ex = None

        while 1:
            x += 1
            if not (x, y) in points:
                if ex is None:
                    ex = x - 1

                if (ox, y + 1) in points:
                    if x == ex + 1:
                        y += 1
                        x = ox

                    else:
                        y -= 1
                        break
                else:
                    if x <= ex:
                        y -= 1
                    break

        c_rect = pygame.Rect(
            ox * tilewidth,
            oy * tileheight,
            (ex - ox + 1) * tilewidth,
            (y - oy + 1) * tileheight,
        )

        rects.append(c_rect)

        rect = pygame.Rect(ox, oy, ex - ox + 1, y - oy + 1)
        kill = [p for p in points if rect.collidepoint(p)]
        [points.remove(i) for i in kill]

        if points:
            pick_rect(points, rects)

    rect_list = []
    while all_points:
        pick_rect(all_points, rect_list)

    return rect_list
