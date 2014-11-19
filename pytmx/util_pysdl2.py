import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

try:
    from sdl2 import *
    import sdl2.ext
except ImportError:
    logger.error('cannot import pysdl2 (is it installed?)')
    raise

import pytmx

__all__ = ['load_pysdl2', 'pysdl2_image_loader',]


def pysdl2_image_loader(filename, colorkey, **kwargs):
    factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    image = sdl2.ext.load_image(filename)

    def load_image(rect=None, flags=None):
        if rect:
            try:
                return sdl2.ext.subsurface(image, rect)
            except ValueError:
                logger.error('Tile bounds outside bounds of tileset image')
                raise
        else:
            return image

    return load_image


def load_pysdl2(filename, *args, **kwargs):
    return pytmx.TiledMap(filename, image_loader=pysdl2_image_loader)
