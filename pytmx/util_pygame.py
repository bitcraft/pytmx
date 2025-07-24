# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2025, Leif Theden <leif.theden@gmail.com>

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
from collections.abc import Callable
from typing import Any, Optional, Union

import pytmx
from pytmx.pytmx import ColorLike, PointLike, TileFlags

logger = logging.getLogger(__name__)

try:
    import pygame
    from pygame.transform import flip, rotate
except ImportError:
    logger.error("cannot import pygame (is it installed?)")
    raise

__all__ = ["load_pygame", "pygame_image_loader", "simplify", "build_rects"]


def handle_transformation(
    tile: pygame.Surface, flags: pytmx.TileFlags
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
        if tile.get_width() != tile.get_height():
            raise ValueError(
                f"Cannot flip tile {tile.get_size()} diagonally if it is not a square"
            )
        tile = flip(rotate(tile, 270), True, False)
    if flags.flipped_horizontally or flags.flipped_vertically:
        tile = flip(tile, flags.flipped_horizontally, flags.flipped_vertically)
    return tile


def count_colorkey_pixels(surface: pygame.Surface, colorkey: ColorLike) -> int:
    """Efficiently count pixels matching the colorkey."""
    try:
        import pygame.surfarray

        pixel_array = pygame.surfarray.pixels3d(surface)
        r, g, b = colorkey[:3]
        return (
            (pixel_array[:, :, 0] == r)
            & (pixel_array[:, :, 1] == g)
            & (pixel_array[:, :, 2] == b)
        ).sum()
    except ImportError:
        # Slow fallback method
        width, height = surface.get_size()
        return sum(
            1
            for x in range(width)
            for y in range(height)
            if surface.get_at((x, y))[:3] == colorkey[:3]
        )


def has_transparency(surface: pygame.Surface, threshold: int = 254) -> bool:
    """Detects transparency via mask."""
    try:
        mask = pygame.mask.from_surface(surface, threshold)
        return mask.count() < surface.get_width() * surface.get_height()
    except Exception:
        return True  # Assume transparency if mask fails


def log_surface_properties(surface: pygame.Surface, label: str = "Surface") -> None:
    """Print diagnostic info (optional for debugging)."""
    size = surface.get_size()
    flags = surface.get_flags()
    bitsize = surface.get_bitsize()
    alpha = surface.get_alpha()
    logger.info(
        f"[{label}] Size: {size}, Flags: {flags}, Bitsize: {bitsize}, Alpha: {alpha}"
    )


def smart_convert(
    original: pygame.Surface,
    colorkey: Optional[ColorLike],
    pixelalpha: bool,
    preserve_alpha_flag: bool = False,
) -> pygame.Surface:
    """
    Return new pygame Surface with optimal pixel/data format

    This method does several interactive tests on a surface to determine the optimal
    flags and pixel format for each tile surface.

    Parameters:
        original: tile surface to inspect
        colorkey: optional colorkey for the tileset image
        pixelalpha: if true, prefer per-pixel alpha surfaces
        preserve_alpha_flag: if True, retain SRCALPHA format even if transparency isn't detected

    Returns:
        new tile surface
    """
    width, height = original.get_size()
    tile = None

    def force_alpha():
        return original.convert_alpha()

    if colorkey:
        colorkey_pixels = count_colorkey_pixels(original, colorkey)
        ratio = colorkey_pixels / (width * height)

        if ratio > 0.5:
            tile = original.convert()
            tile.set_colorkey(colorkey, pygame.RLEACCEL)
        else:
            tile = force_alpha() if pixelalpha else original.convert()
            tile.set_colorkey(colorkey)
    else:
        if has_transparency(original):
            tile = force_alpha()
        elif preserve_alpha_flag and original.get_flags() & pygame.SRCALPHA:
            tile = force_alpha()
        else:
            tile = original.convert()

    # Optional: log_surface_properties(tile, label="Converted Tile")
    return tile


def pygame_image_loader(
    filename: str, colorkey: Optional[ColorLike], **kwargs: Any
) -> Callable[[Optional[pygame.Rect], Optional[TileFlags]], pygame.Surface]:
    """
    pytmx image loader for pygame

    Parameters:
        filename: filename, including path, to load
        colorkey: colorkey for the image

    Returns:
        function to load tile images
    """
    if colorkey:
        if isinstance(colorkey, str):
            if not colorkey.startswith("#") and len(colorkey) in (6, 8):
                colorkey = pygame.Color(f"#{colorkey}")
            else:
                colorkey = pygame.Color(colorkey)
        elif isinstance(colorkey, tuple) and 3 <= len(colorkey) <= 4:
            colorkey = pygame.Color(colorkey)
        else:
            logger.error("Invalid colorkey")
            raise ValueError("Invalid colorkey")

    pixelalpha = kwargs.get("pixelalpha", True)
    image = pygame.image.load(filename)

    def load_image(
        rect: Optional[pygame.Rect] = None, flags: Optional[TileFlags] = None
    ) -> pygame.Surface:
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


def load_pygame(filename: str, *args: Any, **kwargs: Any) -> pytmx.TiledMap:
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
) -> list[pygame.Rect]:
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
            tileset_obj = tmxmap.tilesets[tileset]
        except IndexError:
            msg = f"Tileset #{tileset} not found in map {tmxmap}."
            logger.debug(msg)
            raise IndexError(msg)

    elif isinstance(tileset, str):
        try:
            # Find the tileset with the matching name
            tileset_obj = next((t for t in tmxmap.tilesets if t.name == tileset), None)
            if tileset_obj is None:
                msg = f'Tileset "{tileset}" not found in map {tmxmap}.'
                logger.debug(msg)
                raise ValueError(msg)
        except Exception as e:
            msg = f"Error finding tileset: {e}"
            logger.debug(msg)
            raise ValueError(msg)

    gid = None
    if real_gid:
        try:
            # Get the map GID and flags
            map_gid = tmxmap.map_gid(real_gid)
            if map_gid:
                gid, flags = map_gid[0]
        except IndexError:
            msg = f"GID #{real_gid} not found"
            logger.debug(msg)
            raise ValueError(msg)

    if isinstance(layer, int):
        layer_data = tmxmap.get_layer_data(layer)
    elif isinstance(layer, str):
        try:
            # Find the layer with the matching name
            layer_obj = next(
                (l for l in tmxmap.layers if l.name and l.name == layer), None
            )
            if layer_obj is None:
                msg = f'Layer "{layer}" not found in map {tmxmap}.'
                logger.debug(msg)
                raise ValueError(msg)
            layer_data = layer_obj.data
        except Exception as e:
            msg = f"Error finding layer: {e}"
            logger.debug(msg)
            raise ValueError(msg)

    points = []
    for x, y in itertools.product(range(tmxmap.width), range(tmxmap.height)):
        tile_gid = layer_data[y][x]
        if (gid is None and tile_gid) or (gid == tile_gid):
            points.append((x, y))

    rects = simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects


def simplify(
    all_points: list[PointLike],
    tilewidth: int,
    tileheight: int,
) -> list[pygame.Rect]:
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

    if not all_points:
        return []

    point_set = set(all_points)

    rect_list: list[pygame.Rect] = []

    def pick_rect(points: set[PointLike], rects: list[pygame.Rect]) -> None:
        """
        Recursively pick a rect from the points and add it to the rects list.
        """
        if not points:
            return

        ox, oy = min(points, key=lambda p: (p[0], p[1]))
        x = ox
        y = oy
        ex = None

        while True:
            x += 1
            if (x, y) not in points:
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
        points.difference_update({p for p in points if rect.collidepoint(p)})

        pick_rect(points, rects)

    pick_rect(point_set, rect_list)

    return rect_list
