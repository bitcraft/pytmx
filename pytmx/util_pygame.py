# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2017, Leif Theden <leif.theden@gmail.com>

This file is part of pytmx.

pytmx is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pytmx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pytmx.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools
import logging

import pytmx

logger = logging.getLogger(__name__)

try:
    from pygame.transform import flip, rotate
    import pygame
except ImportError:
    logger.error('cannot import pygame (is it installed?)')
    raise

__all__ = ['load_pygame', 'pygame_image_loader', 'simplify', 'build_rects']


def handle_transformation(tile, flags):
    if flags.flipped_diagonally:
        tile = flip(rotate(tile, 270), 1, 0)
    if flags.flipped_horizontally or flags.flipped_vertically:
        tile = flip(tile, flags.flipped_horizontally, flags.flipped_vertically)
    return tile


def smart_convert(original, colorkey, pixelalpha):
    """
    this method does several tests on a surface to determine the optimal
    flags and pixel format for each tile surface.

    this is done for the best rendering speeds and removes the need to
    convert() the images on your own
    """
    tile_size = original.get_size()
    threshold = 127  # the default

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

    # there are transparent pixels, and tiled set a colorkey
    elif colorkey:
        tile = original.convert()
        tile.set_colorkey(colorkey, pygame.RLEACCEL)

    # there are transparent pixels, and set for perpixel alpha
    elif pixelalpha:
        tile = original.convert_alpha()

    # there are transparent pixels, and we won't handle them
    else:
        tile = original.convert()

    return tile


def pygame_image_loader(filename, colorkey, **kwargs):
    """ pytmx image loader for pygame

    :param filename:
    :param colorkey:
    :param kwargs:
    :return:
    """
    if colorkey:
        colorkey = pygame.Color('#{0}'.format(colorkey))

    pixelalpha = kwargs.get('pixelalpha', True)
    image = pygame.image.load(filename)

    def load_image(rect=None, flags=None):
        if rect:
            try:
                tile = image.subsurface(rect)
            except ValueError:
                logger.error('Tile bounds outside bounds of tileset image')
                raise
        else:
            tile = image.copy()

        if flags:
            tile = handle_transformation(tile, flags)

        tile = smart_convert(tile, colorkey, pixelalpha)
        return tile

    return load_image


def load_pygame(filename, *args, **kwargs):
    """ Load a TMX file, images, and return a TiledMap class

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
    """
    kwargs['image_loader'] = pygame_image_loader
    return pytmx.TiledMap(filename, *args, **kwargs)


def build_rects(tmxmap, layer, tileset=None, real_gid=None):
    """generate a set of non-overlapping rects that represents the distribution
       of the specified gid.

    useful for generating rects for use in collision detection

    Use at your own risk: this is experimental...will change in future

    GID Note: You will need to add 1 to the GID reported by Tiled.

    :param tmxmap: TiledMap object
    :param layer: int or string name of layer
    :param tileset: int or string name of tileset
    :param real_gid: Tiled GID of the tile + 1 (see note)
    :return: List of pygame Rect objects
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
            msg = "Tileset \"{0}\" not found in map {1}."
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
            msg = "Layer \"{0}\" not found in map {1}."
            logger.debug(msg.format(layer, tmxmap))
            raise ValueError

    p = itertools.product(range(tmxmap.width), range(tmxmap.height))
    if gid:
        points = [(x, y) for (x, y) in p if layer_data[y][x] == gid]
    else:
        points = [(x, y) for (x, y) in p if layer_data[y][x]]

    rects = simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects


def simplify(all_points, tilewidth, tileheight):
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
                    if x <= ex: y -= 1
                    break

        c_rect = pygame.Rect(ox * tilewidth, oy * tileheight,
                             (ex - ox + 1) * tilewidth,
                             (y - oy + 1) * tileheight)

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
