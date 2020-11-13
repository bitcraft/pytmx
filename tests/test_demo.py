"""
This is tested on pygame 1.9 and python 2.7 and 3.3+.
Leif Theden "bitcraft", 2012-2017

Rendering demo for the TMXLoader.

Typically this is run to verify that any code changes do do break the loader.
Tests all Tiled features -except- terrains and object rotation.

If you are not familiar with python classes, you might want to check the
'tutorial' app.

Missing interactive_tests:
- object rotation
- terrains
"""

import logging

import pygame
from pygame.locals import *

from pytmx.dc import Map, TileLayer, ObjectGroup, ImageLayer
from pytmx.mason import load_tmx, MasonException
from util_pygame import pygame_image_loader

logger = logging.getLogger(__name__)


def load_pygame(path) -> Map:
    map = load_tmx(path, pygame_image_loader)
    return map


def init_screen(width, height):
    """ Set the screen mode
    This function is used to handle window resize events
    """
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """

    def __init__(self, filename):
        tm = load_pygame(filename)
        self.pixel_size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm
        print(self.pixel_size)

    def render_map(self, surface):
        if self.tmx_data.background_color:
            surface.fill(pygame.Color(self.tmx_data.background_color))
        for layer in self.tmx_data.visible_layers:
            if type(layer) == TileLayer:
                self.render_tile_layer(surface, layer)
            elif isinstance(layer, ObjectGroup):
                self.render_object_layer(surface, layer)
            elif isinstance(layer, ImageLayer):
                self.render_image_layer(surface, layer)

    def render_tile_layer(self, surface, layer):
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        surface_blit = surface.blit
        for x, y, tile in layer.tiles():
            surface_blit(tile.image, (x * tw, y * th))

    def render_object_layer(self, surface, layer):
        draw_rect = pygame.draw.rect
        draw_lines = pygame.draw.lines
        surface_blit = surface.blit
        rect_color = (255, 0, 0)
        poly_color = (0, 255, 0)
        for obj in layer:
            logger.info(obj)
            if hasattr(obj, 'points'):
                draw_lines(surface, poly_color, obj.closed, obj.points, 3)
            elif obj.image:
                surface_blit(obj.image, (obj.x, obj.y))
            elif obj.shapes:
                for shape in obj.shapes:
                    logger.info(shape)
            else:
                if obj.width and obj.height:
                    draw_rect(surface, rect_color,
                              (obj.x, obj.y, obj.width, obj.height), 3)

    def render_image_layer(self, surface, layer):
        if layer.image:
            surface.blit(layer.image, (0, 0))


class SimpleTest(object):
    """ Basic app to display a rendered Tiled map
    """

    def __init__(self, filename):
        self.renderer = None
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.load_map(filename)
        self.screen = None

    def load_map(self, filename):
        """ Create a renderer, load data, and print some debug info
        """
        self.renderer = TiledRenderer(filename)

        logger.info("Objects in map:")
        # for obj in self.renderer.tmx_data.objects:
        #     logger.info(obj)
        #     for k, v in obj.properties.items():
        #         logger.info("%s\t%s", k, v)

        # logger.info("GID (tile) properties:")
        # for tile, properties in self.renderer.tmx_data.tile_properties():
        #     logger.info("%s\t%s", k, v)

    def draw(self, surface):
        """ Draw our map to some surface (probably the display)
        """
        temp = pygame.Surface(self.renderer.pixel_size)
        self.renderer.render_map(temp)
        pygame.transform.smoothscale(temp, surface.get_size(), surface)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press any key for next map or ESC to quit',
                     1, (180, 180, 0))
        surface.blit(i, (0, 0))

    def handle_input(self):
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

            elif event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                self.dirty = True

        except KeyboardInterrupt:
            self.exit_status = 0
            self.running = False

    def run(self):
        """ This is our app main loop
        """
        self.dirty = True
        self.running = True
        self.exit_status = 1

        while self.running:
            self.handle_input()

            # we don't want to constantly draw on the display, as that is way
            # inefficient.  so, this 'dirty' values is used.  If dirty is True,
            # then re-render the map, display it, then mark 'dirty' False.
            if self.dirty:
                self.draw(screen)
                self.dirty = False
                pygame.display.flip()

        return self.exit_status
screen = None

def main():
    import os.path
    import glob
    global screen

    pygame.init()
    pygame.font.init()
    screen = init_screen(800, 600)
    pygame.display.set_caption('PyTMX Map Viewer')
    logging.basicConfig(level=logging.DEBUG)

    # logger.info(pytmx.__version__)

    # loop through a bunch of maps in the maps folder
    try:
        for filename in glob.glob(os.path.join("apps", 'data', '*.tmx')):
            logger.info("Testing %s", filename)
            try:
                if not SimpleTest(filename).run():
                    break
            except MasonException:
                pass
    except:
        pygame.quit()
        raise


import unittest

class Test(unittest.TestCase):
    def test_main(self):
        main()