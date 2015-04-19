import logging
from functools import partial

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

try:
    import sdl2.ext
except ImportError:
    logger.error('cannot import pysdl2 (is it installed?)')
    raise

import pytmx

__all__ = ['load_pysdl2', 'pysdl2_image_loader', ]
flag_names = (
    'flipped_horizontally',
    'flipped_vertically',
    'flipped_diagonally',)


def pysdl2_image_loader(renderer, filename, colorkey, **kwargs):
    def convert(surface):
        texture_ = sdl2.SDL_CreateTextureFromSurface(renderer.renderer, surface)
        sdl2.SDL_SetTextureBlendMode(texture_, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_FreeSurface(surface)
        return texture_

    def load_image(rect=None, flags=None):
        if rect:
            try:
                flip = 0
                if flags.flipped_horizontally:
                    flip |= sdl2.SDL_FLIP_HORIZONTAL
                if flags.flipped_vertically:
                    flip |= sdl2.SDL_FLIP_VERTICAL
                if flags.flipped_diagonally:
                    flip |= 4

                rect = sdl2.rect.SDL_Rect(*rect)
                return texture, rect, flip

            except ValueError:
                logger.error('Tile bounds outside bounds of tileset image')
                raise
        else:
            return texture, None, 0

    image = sdl2.ext.load_image(filename)

    if colorkey:
        colorkey = sdl2.ext.string_to_color('#' + colorkey)
        key = sdl2.SDL_MapRGB(image.format, *colorkey[:3])
        sdl2.SDL_SetColorKey(image, sdl2.SDL_TRUE, key)

    texture = convert(image)

    return load_image


def load_pysdl2(renderer, filename, *args, **kwargs):
    loader = partial(pysdl2_image_loader, renderer)
    return pytmx.TiledMap(filename, image_loader=loader)
