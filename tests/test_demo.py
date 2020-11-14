"""
Leif Theden "bitcraft", 2012-2020
"""

import logging
from math import sin, cos
from math import radians

import pygame
from pygame import math
from pygame.locals import *

from pytmx.dc import Map, TileLayer, ObjectGroup, ImageLayer
from pytmx.mason import load_tmxmap, MasonException
from util_pygame import pygame_image_loader

logger = logging.getLogger(__name__)


def load_pygame(path) -> Map:
    map = load_tmxmap(path, pygame_image_loader)
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
        self.count = 0

    def render_map(self, surface):
        self.count += 1
        if self.tmx_data.background_color:
            surface.fill(pygame.Color(self.tmx_data.background_color))
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, TileLayer):
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
            x = x * tw
            y = y * th + tile.offsety
            surface_blit(tile.image, (x, y))

    @staticmethod
    def rotate(points, origin, angle):
        sinT = sin(radians(angle))
        cosT = cos(radians(angle))
        new_points = list()
        # clockwise, per tmx spec
        for point in points:
            p = (origin.x + (cosT * (point.x - origin.x) - sinT * (point.y - origin.y)),
                 origin.y + (sinT * (point.x - origin.x) + cosT * (point.y - origin.y)))
            new_points.append(p)
        return new_points

    def render_object_layer(self, surface, layer):
        draw_rect = pygame.draw.rect
        draw_lines = pygame.draw.lines
        surface_blit = surface.blit
        rect_color = (128, 128, 128)
        poly_color = (128, 128, 128)
        for obj in layer:
            logger.info(obj)
            # if hasattr(obj, 'points'):
            #     draw_lines(surface, poly_color, obj.closed, obj.points, 3)
            # tiled will invert the y axis if there is an image
            if obj.image:
                if obj.rotation:
                    r = obj.rotation
                    # r = (self.count / 2) + obj.rotation
                    print(obj, obj.as_points)
                    print(self.rotate(obj.as_points, obj, r))
                    points = self.rotate(obj.as_points, obj, r)
                    # clockwise -> counterclockwise
                    image = pygame.transform.rotate(obj.image, 360 - r)
                    position = sorted(points)[0]
                    surface_blit(image, (position[0], position[1]))
                else:
                    image = obj.image
                    position = obj.x, obj.y - obj.height
                    surface_blit(image, position)
            # elif obj.shapes:
            #     for shape in obj.shapes:
            #         logger.info(shape)
            # else:
            #     points = obj.points
            #     if len(points) > 1:
            #         draw_lines(surface, poly_color, True, obj.points, 1)

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
        pygame.transform.scale(temp, surface.get_size(), surface)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press any key for next map or ESC to quit',
                     1, (180, 180, 0))
        surface.blit(i, (0, 0))

    def handle_input(self):
        for event in pygame.event.get():
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

    def run(self):
        """ This is our app main loop
        """
        self.dirty = True
        self.running = True
        clock = pygame.time.Clock()

        while self.running:
            self.handle_input()
            self.draw(screen)
            pygame.display.flip()
            clock.tick(165)

        return self.exit_status


screen = None


def main():
    import os.path
    import glob
    global screen

    pygame.init()
    pygame.font.init()
    screen = init_screen(800, 800)
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
