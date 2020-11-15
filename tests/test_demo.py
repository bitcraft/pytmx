"""
Leif Theden "bitcraft", 2012-2020
"""

import glob
import logging
import os.path
from math import radians
from math import sin, cos

import pygame
from pygame.locals import *

from pytmx.dc import TileLayer, ObjectGroup, ImageLayer
from pytmx.mason import load_tmxmap, MasonException
from pytmx.util_pygame import pygame_image_loader

logger = logging.getLogger(__name__)


class BasicRenderer(object):
    """
    Debug rendering of map
    """

    def __init__(self, filename):
        tm = load_tmxmap(filename, pygame_image_loader)
        self.pixel_size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

    def render_map(self, surface):
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
        sin_t = sin(radians(angle))
        cos_t = cos(radians(angle))
        new_points = list()
        for point in points:
            p = (origin.x + (cos_t * (point.x - origin.x) - sin_t * (point.y - origin.y)),
                 origin.y + (sin_t * (point.x - origin.x) + cos_t * (point.y - origin.y)))
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
                    print(obj, obj.as_points)
                    print(self.rotate(obj.as_points, obj, r))
                    points = self.rotate(obj.as_points, obj, r)
                    # clockwise -> counterclockwise
                    image = pygame.transform.rotate(obj.image, 360 - r)
                    position = sorted(points)[0]
                    surface_blit(image, (position[0], position[1]))
                elif obj.width and obj.height:
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

    def __init__(self):
        self.renderer = None
        self.running = False
        self.dirty = False
        self.screen = None

    def setup(self):
        width, height = 800, 800
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.font.init()
        pygame.display.set_caption('pytmx map viewer')
        logging.basicConfig(level=logging.DEBUG)

    def load_map(self, filename):
        """ Create a renderer, load data, and print some debug info
        """
        self.renderer = BasicRenderer(filename)

        logger.info("Objects in map:")
        # for obj in self.renderer.tmx_data.objects:
        #     logger.info(obj)
        #     for k, v in obj.properties.items():
        #         logger.info("%s\t%s", k, v)

        # logger.info("GID (tile) properties:")
        # for tile, properties in self.renderer.tmx_data.tile_properties():
        #     logger.info("%s\t%s", k, v)

    def draw(self):
        """ Draw our map to some surface (probably the display)
        """
        temp = pygame.Surface(self.renderer.pixel_size)
        self.renderer.render_map(temp)
        pygame.transform.scale(temp, self.screen.get_size(), self.screen)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press any key for next map or ESC to quit',
                     True, (180, 180, 0))
        self.screen.blit(i, (0, 0))

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                else:
                    self.running = False
            elif event.type == VIDEORESIZE:
                # self.init_screen(event.w, event.h)
                self.dirty = True

    def run(self):
        """ This is our app main loop
        """
        self.dirty = True
        self.running = True
        clock = pygame.time.Clock()

        while self.running:
            self.handle_input()
            if self.dirty:
                self.draw()
            pygame.display.flip()
            clock.tick(60)


if __name__ == "__main__":
    viewer = SimpleTest()
    try:
        for filename in glob.glob(os.path.join("apps", 'data', '*.tmx')):
            logger.info("Testing %s", filename)
            try:
                if not SimpleTest.load_map(filename):
                    break
            except MasonException:
                pass
    except:
        pygame.quit()
        raise
    viewer.run()
