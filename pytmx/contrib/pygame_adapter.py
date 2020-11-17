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
import math

import pygame
from pygame.transform import flip, rotate


def handle_transformation(tile: pygame.Surface, flags) -> pygame.Surface:
    if flags.diagonal:
        tile = flip(rotate(tile, 270), 1, 0)
    if flags.horizontal or flags.vertical:
        tile = flip(tile, flags.horizontal, flags.vertical)
    return tile


def smart_convert(
    surface: pygame.Surface, colorkey: str, pixelalpha: bool
) -> pygame.Surface:
    """Return new surface optimized for blitting"""
    if colorkey:
        # TODO: if there is a colorkey, count the colorkey pixels to determine if RLEACCEL should be used
        tile = surface.convert()
        tile.set_colorkey(colorkey, pygame.RLEACCEL)
        return tile
    else:
        if pixelalpha:
            filled_pixels = pygame.mask.from_surface(surface).count()
            total_pixels = math.prod(surface.get_size())
            if filled_pixels != total_pixels:
                return surface.convert_alpha()
        return surface.convert()


def pygame_image_loader(filename: str, colorkey: str = None, pixelalpha=True):
    def load_image(rect=None, flags=None):
        if rect:
            tile = image.subsurface(rect)
        else:
            tile = image.copy()
        if flags:
            tile = handle_transformation(tile, flags)
        return smart_convert(tile, colorkey, pixelalpha)

    # TODO: turn off pixel alpha if source image doesn't have alpha channel
    image = pygame.image.load(filename)
    if colorkey:
        colorkey = pygame.Color("#{0}".format(colorkey))
    return load_image


class PygameAdapter:
    pass
