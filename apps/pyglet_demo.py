"""
This is tested on pyglet 1.2 and python 2.7.
Leif Theden "bitcraft", 2012-2024

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

import pyglet
from pyglet.sprite import Sprite

from pytmx import *
from pytmx.util_pyglet import load_pyglet


class TiledRenderer:
    """
    Super simple way to render a tiled map with pyglet

    no shape drawing yet
    """

    def __init__(self, filename: str) -> None:
        tm = load_pyglet(filename)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm
        self.batch = pyglet.graphics.Batch()
        self.sprites = []  # container for tiles
        self.generate_sprites()

    def draw_rect(self, color, rect, width) -> None:
        # TODO: use pyglet.shapes
        pass

    def draw_lines(self, color, closed, points, width) -> None:
        # TODO: use pyglet.shapes
        pass

    def generate_sprites(self) -> None:
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        mw = self.tmx_data.width
        mh = self.tmx_data.height - 1
        pixel_height = (mh + 1) * th
        draw_rect = self.draw_rect
        draw_lines = self.draw_lines

        rect_color = (255, 0, 0)
        poly_color = (0, 255, 0)

        for i, layer in enumerate(self.tmx_data.visible_layers):
            # Use Groups to seperate layers inside the Batch:
            group = pyglet.graphics.Group(order=i)

            # draw map tile layers
            if isinstance(layer, TiledTileLayer):
                # iterate over the tiles in the layer
                for x, y, image in layer.tiles():
                    y = mh - y
                    x = x * tw
                    y = y * th
                    sprite = Sprite(image, x, y, batch=self.batch, group=group)
                    self.sprites.append(sprite)

            # draw object layers
            elif isinstance(layer, TiledObjectGroup):
                # iterate over all the objects in the layer
                for obj in layer:
                    logger.info(obj)

                    # objects with points are polygons or lines
                    if hasattr(obj, "points"):
                        draw_lines(poly_color, obj.closed, obj.points, 3)

                    # some object have an image
                    elif obj.image:
                        obj.image.blit(obj.x, pixel_height - obj.y)

                    # draw a rect for everything else
                    else:
                        draw_rect(rect_color, (obj.x, obj.y, obj.width, obj.height), 3)

            # draw image layers
            elif isinstance(layer, TiledImageLayer):
                if layer.image:
                    x = mw // 2  # centers image
                    y = mh // 2
                    sprite = Sprite(layer.image, x, y, batch=self.batch)
                    self.sprites.append(sprite)

    def draw(self) -> None:
        self.batch.draw()


class SimpleTest:
    def __init__(self, filename: str) -> None:
        self.renderer = None
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.load_map(filename)

    def load_map(self, filename: str) -> None:
        self.renderer = TiledRenderer(filename)
        assert self.renderer

        logger.info("Objects in map:")
        for obj in self.renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self) -> None:
        assert self.renderer
        self.renderer.draw()


def all_filenames():
    import glob
    import os.path

    _list = glob.glob(os.path.join("data", "*.tmx"))
    try:
        while _list:
            yield _list.pop(0)
    except IndexError:
        pyglet.app.exit()


class TestWindow(pyglet.window.Window):
    def __init__(self, width: int, height: int, vsync: bool):
        super().__init__(width=width, height=height, vsync=vsync)
        self.fps_display = pyglet.window.FPSDisplay(self, color=(50, 255, 50, 255))
        self.filenames = all_filenames()
        self.next_map()

    def on_draw(self) -> None:
        self.clear()
        self.contents.draw()
        self.fps_display.draw()

    def next_map(self) -> None:
        try:
            self.contents = SimpleTest(next(self.filenames))
        except StopIteration:
            pyglet.app.exit()

    def on_key_press(self, symbol, mod):
        if symbol == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
        else:
            self.next_map()


if __name__ == "__main__":
    window = TestWindow(600, 600, vsync=False)
    pyglet.clock.schedule_interval(window.draw, 1 / 120)
    pyglet.app.run(None)
