"""
This is tested on pysdl2 1.2 and python 2.7.
Leif Theden "bitcraft", 2012-2024

Rendering demo for the TMXLoader.

This should be considered --alpha-- quality.  I'm including it as a
proof-of-concept for now and will improve on it in the future.

For Windows users, you will need to download SDL2 runtime and
place it where pysdl2 can find it.  Please check the pysdl2 docs
for information on that process.

Notice: slow!  no transparency!  no tile rotation!
"""
import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

# QUICK SDL2 HACK FOR WINDOWS
# 1. download and move SDL2.dll to apps folder
# 2. uncomment the two lines of code below
# 3. profit!
import os

os.environ["PYSDL2_DLL_PATH"] = os.path.dirname(__file__)

import sdl2.ext
from sdl2 import *

from pytmx import *
from pytmx.util_pysdl2 import load_pysdl2


class TiledRenderer:
    """
    Super simple way to render a tiled map with pyglet

    no shape drawing yet
    """

    def __init__(self, filename, renderer) -> None:
        tm = load_pysdl2(renderer, filename)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm
        self.renderer = renderer

    def render_tile_layer(self, layer) -> None:
        """Render the tile layer

        DOES NOT CHECK FOR DRAWING TILES OFF THE SCREEN
        """
        # deref these heavily used references for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        renderer = self.renderer.renderer
        dest = sdl2.rect.SDL_Rect(0, 0, tw, th)
        rce = sdl2.SDL_RenderCopyEx

        # iterate over the tiles in the layer
        for x, y, tile in layer.tiles():
            texture, src, flip = tile
            dest.x = x * tw
            dest.y = y * th
            angle = 90 if (flip & 4) else 0
            rce(renderer, texture, src, dest, angle, None, flip)

    def render_map(self) -> None:
        """Render the entire map

        Only tile layer drawing is implemented
        """
        for layer in self.tmx_data.visible_layers:

            # draw map tile layers
            if isinstance(layer, TiledTileLayer):
                self.render_tile_layer(layer)


class SimpleTest:
    def __init__(self, filename, window) -> None:
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.sdl_renderer = window.renderer
        self.map_renderer = TiledRenderer(filename, self.sdl_renderer)

        logger.info("Objects in map:")
        for obj in self.map_renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.map_renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self) -> None:
        self.sdl_renderer.clear()
        self.map_renderer.render_map()
        self.sdl_renderer.present()

    def run(self, window) -> int:
        """
        Starts an event loop without actually processing any event.

        Returns:
            Int: 0 means no error, 1 is an error
        """
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


def all_filenames() -> list[str]:
    import glob
    import os.path

    return glob.glob(os.path.join("data", "*.tmx"))


if __name__ == "__main__":
    window = sdl2.ext.Window("pytmx + psdl2 = awesome???", size=(600, 600))
    window.renderer = sdl2.ext.Renderer(window)
    window.renderer.blendmode = SDL_BLENDMODE_BLEND
    window.renderer.color = 0, 0, 0, 0
    window.show()

    try:
        for filename in all_filenames():
            logger.info("Testing %s", filename)
            if not SimpleTest(filename, window).run(window):
                break
    except:
        raise
