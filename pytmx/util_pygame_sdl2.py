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

import dataclasses
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, Optional

from pygame.rect import Rect

import pytmx
from pytmx.pytmx import ColorLike, PointLike, TileFlags

logger = logging.getLogger(__name__)

try:
    import pygame
    from pygame._sdl2 import Renderer, Texture
except ImportError:
    logger.error("cannot import pygame (is it installed?)")
    raise


@dataclass(order=True)
class PygameSDL2Tile:
    texture: Texture
    srcrect: Rect
    size: PointLike
    angle: float = 0.0
    center: Optional[PointLike] = None
    flipx: bool = False
    flipy: bool = False


def handle_flags(flags: Optional[TileFlags]) -> tuple[float, bool, bool]:
    """
    Return angle and flip values for the SDL2 renderer
    """
    if flags is None:
        return 0.0, False, False

    if flags.flipped_diagonally:
        if flags.flipped_vertically:
            return 270.0, False, False
        else:
            return 90.0, False, False
    else:
        return 0.0, flags.flipped_horizontally, flags.flipped_vertically


def pygame_sd2_image_loader(
    renderer: Renderer,
    filename: str,
    colorkey: Optional[ColorLike] = None,
    **kwargs: Any,
) -> Callable[
    [Optional[Rect], Optional[TileFlags], Optional[PointLike]], PygameSDL2Tile
]:
    """
    pytmx image loader for pygame
    """
    image = pygame.image.load(filename)

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

    parent_rect: Rect = image.get_rect()
    texture: Texture = Texture.from_surface(renderer, image)

    def load_image(
        rect: Optional[Rect] = None,
        flags: Optional[TileFlags] = None,
        center: Optional[PointLike] = None,
    ) -> PygameSDL2Tile:
        if rect:
            assert parent_rect.contains(rect), "Tile rect must be within image bounds"
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
            center=center,
            flipx=flipx,
            flipy=flipy,
        )

    return load_image


def load_pygame_sdl2(
    renderer: Renderer, filename: str, *args: Any, **kwargs: Any
) -> pytmx.TiledMap:
    """
    Load a TMX file, images, and return a TiledMap class
    """
    kwargs["image_loader"] = partial(pygame_sd2_image_loader, renderer)
    return pytmx.TiledMap(filename, *args, **kwargs)
