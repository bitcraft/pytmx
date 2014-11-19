"""
This is tested on pysdl2 1.2 and python 2.7.
Leif Theden "bitcraft", 2012-2014

Rendering demo for the TMXLoader.

This should be considered --alpha-- quality.  I'm including it as a
proof-of-concept for now and will improve on it in the future.

Notice: slow!  no transparency!
"""
import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

from pytmx import *
from pytmx.util_pysdl2 import load_pysdl2
from sdl2 import *
import sdl2.ext
from ctypes import byref


class TiledRenderer(object):
    """
    Super simple way to render a tiled map with pyglet

    no shape drawing yet
    """
    def __init__(self, filename, window):
        tm = load_pysdl2(filename)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

        # the loader just loads software surface by default, we change them
        # to textures that will stay in video memory now
        def transform(surface):
            if surface is 0:
                return 0
            texture = SDL_CreateTextureFromSurface(self.renderer.renderer,
                                                   surface)
            SDL_FreeSurface(surface)
            return texture

        self.renderer = sdl2.ext.Renderer(window)
        tm.images = [transform(i) for i in tm.images]

    def draw_rect(self, color, rect, width):
        pass

    def draw_lines(self, color, closed, points, width):
        pass

    def clear(self):
        self.renderer.clear()

    def draw(self):
        # not going for efficiency here
        # for demonstration purposes only

        # deref these heavily used references for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        sdl_renderer = self.renderer.renderer

        for layer in self.tmx_data.visible_layers:

            # draw map tile layers
            if isinstance(layer, TiledTileLayer):

                # iterate over the tiles in the layer
                for x, y, texture in layer.tiles():
                    flags = Uint32()
                    access = c_int()
                    w = c_int()
                    h = c_int()
                    ret = render.SDL_QueryTexture(texture, byref(flags),
                                      byref(access), byref(w), byref(h))

                    r = SDL_Rect(int(x * tw), int(y * th), w, h)
                    if SDL_RenderCopy(sdl_renderer, texture, None, r) == -1:
                        raise SDL_Error()

            # draw object layers
            elif isinstance(layer, TiledObjectGroup):

                # iterate over all the objects in the layer
                for obj in layer:
                    logger.info(obj)

        SDL_RenderPresent(sdl_renderer)

class SimpleTest(object):
    def __init__(self, filename, window):
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.renderer = TiledRenderer(filename, window)

        logger.info("Objects in map:")
        for obj in self.renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self):
        self.renderer.clear()
        self.renderer.draw()

    def run(self, window):
        """Starts an event loop without actually processing any event."""
        import ctypes
        event = events.SDL_Event()
        self.running = True
        self.exit_status = 1
        while self.running:
            ret = events.SDL_PollEvent(ctypes.byref(event), 1)
            if ret == 1:
                if event.type == SDL_QUIT:
                    self.exit_status = 0
                    self.running = False
                elif event.type == SDL_KEYDOWN:
                    self.running = False
            self.draw()
            window.refresh()
            timer.SDL_Delay(10)

        return self.exit_status


def all_filenames():
    import os.path
    import glob
    return glob.glob(os.path.join('data', '0.9.1', '*.tmx'))


if __name__ == '__main__':
    window = sdl2.ext.Window("pytmx + psdl2 = ???", size=(640, 480))
    window.show()

    try:
        for filename in all_filenames():
            logger.info("Testing %s", filename)
            if not SimpleTest(filename, window).run(window):
                break
    except:
        raise
