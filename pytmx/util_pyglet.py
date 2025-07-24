# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2024, Leif Theden <leif.theden@gmail.com>

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
import logging

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any, Optional

try:
    import pyglet
except ImportError:
    logger.error("cannot import pyglet (is it installed?)")
    raise

import pytmx
from pytmx.pytmx import ColorLike, TileFlags


def pyglet_image_loader(
    filename: str, colorkey: Optional[ColorLike] = None, **kwargs: Any
):
    """basic image loading with pyglet

    returns pyglet Images, not textures

    This is a basic proof-of-concept and is likely to fail in some situations.

    Missing:
        Transparency
        Tile Rotation

    This is slow as well.
    """
    if colorkey:
        logger.debug("colorkey not implemented")

    image_path = Path(filename)
    pyglet.resource.path = [str(image_path.parent.resolve())]
    pyglet.resource.reindex()

    image = pyglet.resource.image(image_path.name)

    def load_image(
        rect: Optional[tuple[int, int, int, int]] = None,
        flags: Optional[TileFlags] = None,
    ):
        try:
            if rect:
                x, y, w, h = rect
                y = image.height - y - h
                tile = image.get_region(x, y, w, h)
            else:
                tile = image

            angle, flip_x, flip_y = handle_flags(flags)
            tile = tile.get_transform(flip_x=flip_x, flip_y=flip_y, rotate=int(angle))

            return tile

        except Exception as e:
            logger.error(
                "Error extracting or transforming tile %s: %s", rect, e, exc_info=True
            )
            raise

    return load_image


def handle_flags(flags: Optional[TileFlags]) -> tuple[float, bool, bool]:
    """
    Convert Tiled tile flip flags into SDL2 rendering parameters.
    """
    if not flags:
        return 0.0, False, False

    flipped_h = flags.flipped_horizontally
    flipped_v = flags.flipped_vertically
    flipped_d = flags.flipped_diagonally

    if flipped_d:
        # Diagonal flip overrides horizontal/vertical flips for rotation
        if flipped_v:
            return 270.0, False, False
        else:
            return 90.0, False, False

    return 0.0, flipped_h, flipped_v


def load_pyglet(filename: str, *args: Any, **kwargs: Any) -> pytmx.TiledMap:
    kwargs["image_loader"] = pyglet_image_loader
    kwargs["invert_y"] = True
    return pytmx.TiledMap(filename, *args, **kwargs)
