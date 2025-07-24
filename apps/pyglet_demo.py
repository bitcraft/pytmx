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

from collections.abc import Iterator
from pathlib import Path
from typing import Optional

import pyglet
from pyglet.sprite import Sprite

from pytmx import *
from pytmx.pytmx import ColorLike, PointLike
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

    def draw_rect(
        self, color: ColorLike, rect: tuple[int, int, int, int], width: int
    ) -> None:
        x, y, w, h = rect
        y = self.size[1] - y - h  # Adjust Y if needed for pixel origin
        rect_shape = pyglet.shapes.Rectangle(x, y, w, h, color=color, batch=self.batch)
        rect_shape.opacity = 128  # optional: make it semi-transparent
        if width > 0:
            border_color = (
                max(0, color[0] - 50),
                max(0, color[1] - 50),
                max(0, color[2] - 50),
            )
            pyglet.shapes.Line(
                x, y, x + w, y, thickness=width, color=border_color, batch=self.batch
            )  # bottom
            pyglet.shapes.Line(
                x,
                y + h,
                x + w,
                y + h,
                thickness=width,
                color=border_color,
                batch=self.batch,
            )  # top
            pyglet.shapes.Line(
                x, y, x, y + h, thickness=width, color=border_color, batch=self.batch
            )  # left
            pyglet.shapes.Line(
                x + w,
                y,
                x + w,
                y + h,
                thickness=width,
                color=border_color,
                batch=self.batch,
            )  # right

    def draw_lines(
        self, color: ColorLike, closed: bool, points: list[PointLike], width: int
    ) -> None:
        # Flip Y-axis if necessary
        flipped_points = [(x, self.size[1] - y) for x, y in points]

        if closed:
            polygon = pyglet.shapes.Polygon(
                *flipped_points, color=color, batch=self.batch
            )
            polygon.opacity = 128
        else:
            for (x1, y1), (x2, y2) in zip(flipped_points, flipped_points[1:]):
                line = pyglet.shapes.Line(
                    x1, y1, x2, y2, thickness=width, color=color, batch=self.batch
                )

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
        self.renderer: TiledRenderer
        self.running: bool = False
        self.dirty: bool = False
        self.exit_status: int = 0
        self.load_map(filename)

    def load_map(self, filename: str) -> None:
        self.renderer = TiledRenderer(filename)

        logger.info("Objects in map:")
        for obj in self.renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self) -> None:
        self.renderer.draw()


def all_filenames() -> Iterator[str]:
    data_dir = Path("apps/data")
    for path in sorted(data_dir.glob("*.tmx")):
        yield str(path)
    pyglet.app.exit()


class TestWindow(pyglet.window.Window):
    def __init__(self, width: int, height: int, vsync: bool) -> None:
        super().__init__(width=width, height=height, vsync=vsync)
        self.fps_display: pyglet.window.FPSDisplay = pyglet.window.FPSDisplay(
            self, color=(50, 255, 50, 255)
        )
        self.filenames: Iterator[str] = all_filenames()
        self.contents: Optional[SimpleTest] = None
        self.next_map()

    def on_draw(self) -> None:
        self.clear()
        if self.contents:
            self.contents.draw()
        self.fps_display.draw()

    def next_map(self) -> None:
        try:
            filename = next(self.filenames)
            self.contents = SimpleTest(filename)
        except StopIteration:
            pyglet.app.exit()

    def on_key_press(self, symbol: int, mod: int) -> None:
        if symbol == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
        else:
            self.next_map()


if __name__ == "__main__":
    window = TestWindow(600, 600, vsync=False)
    pyglet.clock.schedule_interval(window.draw, 1 / 120)
    pyglet.app.run(None)
