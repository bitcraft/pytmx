"""
This is tested on pygame 2.0.1 and python 3.9.6.
Leif Theden "bitcraft", 2012-2025

Rendering demo for the TMXLoader.

"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame
from pygame._sdl2 import Renderer, Window
from pygame.locals import *

import pytmx
from pytmx import TiledTileLayer
from pytmx.util_pygame_sdl2 import load_pygame_sdl2

logger = logging.getLogger(__name__)


@dataclass
class GameContext:
    window: Window
    renderer: Renderer


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """

    def __init__(self, ctx: GameContext, filename: str) -> None:
        self.ctx = ctx
        self.tmx_data = tm = load_pygame_sdl2(ctx.renderer, filename)
        self.pixel_size = tm.width * tm.tilewidth, tm.height * tm.tileheight

    def render_map(self) -> None:
        """
        Render our map to a pygame surface

        Feel free to use this as a starting point for your pygame app.

        Scrolling is a often requested feature, but pytmx is a map
        loader, not a renderer!  If you'd like to have a scrolling map
        renderer, please see my pyscroll project.
        """
        # iterate over all the visible layers, then draw them
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, TiledTileLayer):
                self.render_tile_layer(layer)

    def render_tile_layer(self, layer: TiledTileLayer) -> None:
        """
        Render all TiledTiles in this layer
        """
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight

        # iterate over the tiles in the layer, and draw them
        for x, y, image in layer.tiles():
            x *= tw
            y *= th
            image.texture.draw(
                image.srcrect,
                (x, y, tw, th),
                image.angle,
                image.center,
                image.flipx,
                image.flipy,
            )


class SimpleTest:
    """
    Basic app to display a rendered Tiled map
    """

    def __init__(self, ctx: GameContext, filename: Path) -> None:
        self.ctx = ctx
        self.map_renderer: Optional[TiledRenderer] = None
        self.running: bool = False
        self.exit_status: int = 0
        self.load_map(filename)

    def load_map(self, filename: Path) -> None:
        """
        Create a renderer, load data, and print some debug info
        """
        self.map_renderer = TiledRenderer(self.ctx, filename.as_posix())

        logger.info("Objects in map:")
        for obj in self.map_renderer.tmx_data.objects:
            logger.info("Object: %s", obj)
            logger.debug("Properties: %s", vars(obj))

        logger.info("GID (tile) properties:")
        for k, v in self.map_renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

        logger.info("Tile colliders:")
        for k, v in self.map_renderer.tmx_data.get_tile_colliders():
            logger.info("%s\t%s", k, list(v))

    def draw(self) -> None:
        """
        Draw our map to some surface (probably the display)
        """
        if self.map_renderer:
            self.map_renderer.render_map()
            self.ctx.renderer.present()

    def handle_input(self) -> None:
        try:
            event = pygame.event.wait()

            if event.type == QUIT:
                self.exit_status = 0
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.exit_status = 0
                    self.running = False
                else:
                    self.running = False

        except KeyboardInterrupt:
            self.exit_status = 0
            self.running = False

    def run(self) -> int:
        """
        Main loop of the app.

        Returns:
            int: Exit status (0 = success, 1 = error)
        """
        self.running = True
        self.exit_status = 1

        while self.running:
            self.handle_input()
            self.draw()

        return self.exit_status


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    window = Window("pytmx map viewer", size=(600, 600))
    renderer = Renderer(window, vsync=True)

    ctx = GameContext(window, renderer)

    logging.basicConfig(level=logging.DEBUG)
    logger.info(pytmx.__version__)

    # loop through a bunch of maps in the maps folder
    try:
        for filename in Path("apps/data").glob("*.tmx"):
            logger.info("Testing %s", filename)
            renderer.clear()
            if not SimpleTest(ctx, filename).run():
                break
    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        pygame.quit()
        raise
