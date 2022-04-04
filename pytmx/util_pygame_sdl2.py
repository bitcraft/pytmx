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
License along with pytmx.  If not, see <http://www.gnu.org/licenses/>.
"""
import dataclasses
import logging
from functools import partial
from typing import Tuple

from pygame.rect import Rect

import pytmx

logger = logging.getLogger(__name__)

try:
    from pygame._sdl2 import Texture, Image, Renderer, Window
    import pygame
except ImportError:
    logger.error("cannot import pygame (is it installed?)")
    raise


@dataclasses.dataclass(order=True)
class PygameSDL2Tile:
    texture: Texture
    srcrect: Rect
    size: Tuple[int, int]
    angle: float = 0.0
    center: None = None
    flipx: bool = False
    flipy: bool = False


def handle_flags(flags: pytmx.TileFlags):
    """
    Return angle and flip values for the SDL2 renderer

    """
    if flags is None:
        return 0.0, False, False

    if flags.flipped_diagonally:
        if flags.flipped_vertically:
            return 270, False, False
        else:
            return 90, False, False
    else:
        return 0.0, flags.flipped_horizontally, flags.flipped_vertically


def pygame_sd2_image_loader(renderer: Renderer, filename: str, colorkey, **kwargs):
    """
    pytmx image loader for pygame

    """
    image = pygame.image.load(filename)
    parent_rect = image.get_rect()
    texture = Texture.from_surface(renderer, image)

    def load_image(rect=None, flags=None) -> PygameSDL2Tile:
        if rect:
            assert parent_rect.contains(rect)
        else:
            rect = parent_rect

        angle, flipx, flipy = handle_flags(flags)
        rect = Rect(*rect)
        size = rect.size
        return PygameSDL2Tile(
            texture=texture,
            srcrect=rect,
            size=size,
            angle=angle,
            center=None,
            flipx=flipx,
            flipy=flipy,
        )

    return load_image


def load_pygame_sdl2(renderer: Renderer, filename: str, *args, **kwargs):
    """
    Load a TMX file, images, and return a TiledMap class

    """
    kwargs["image_loader"] = partial(pygame_sd2_image_loader, renderer)
    return pytmx.TiledMap(filename, *args, **kwargs)
