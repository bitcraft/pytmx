"""
This is tested on pygame 1.9 and python 2.7 and 3.3+.
Leif Thedem "bitcraft", 2012-2014

Rendering demo for the TMXLoader.

Typically this is run to verify that any code changes do do break the loader.
Tests all Tiled features -except- terrains and object rotation.

Missing tests:
- object rotation
"""
import logging

from pytmx import *
#from pytmx import load_pygame
import pygame
from pygame.locals import *

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)


def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """
    def __init__(self, filename):
        tm = load_pygame(filename)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

    def render(self, surface):
        # not going for efficiency here
        # for demonstration purposes only

        # deref these heavily used references for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        surface_blit = surface.blit
        draw_rect = pygame.draw.rect
        draw_lines = pygame.draw.lines

        rect_color = (255, 0, 0)
        poly_color = (0, 255, 0)

        # fill the background color
        if self.tmx_data.background_color:
            surface.fill(pygame.Color(self.tmx_data.background_color))

        # iterate over all the visible layers, then draw them
        # according to the type of layer they are.
        for layer in self.tmx_data.visible_layers:

            # draw map tile layers
            if isinstance(layer, TiledTileLayer):

                # iterate over the tiles in the layer
                for x, y, image in layer.tiles():
                    surface_blit(image, (x * tw, y * th))

            # draw object layers
            elif isinstance(layer, TiledObjectGroup):

                # iterate over all the objects in the layer
                for obj in layer:
                    logger.info(obj)

                    # objects with points are polygons or lines
                    if hasattr(obj, 'points'):
                        draw_lines(surface, poly_color,
                                   obj.closed, obj.points, 3)

                    # some object have an image
                    elif obj.image:
                        surface_blit(obj.image, (obj.x, obj.y))

                    # draw a rect for everything else
                    else:
                        draw_rect(surface, rect_color,
                                  (obj.x, obj.y, obj.width, obj.height), 3)

            # draw image layers
            elif isinstance(layer, TiledImageLayer):
                if layer.image:
                    surface.blit(layer.image, (0, 0))


class SimpleTest(object):
    def __init__(self, filename):
        self.renderer = None
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.load_map(filename)

    def load_map(self, filename):
        self.renderer = TiledRenderer(filename)

        logger.info("Objects in map:")
        for obj in self.renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self, surface):
        temp = pygame.Surface(self.renderer.size)
        self.renderer.render(temp)
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
        self.dirty = True
        self.running = True
        self.exit_status = 1
        while self.running:
            self.handle_input()
            if self.dirty:
                self.draw(screen)
                self.dirty = False
                pygame.display.flip()

        return self.exit_status

if __name__ == '__main__':
    import os.path
    import glob

    pygame.init()
    pygame.font.init()
    screen = init_screen(600, 600)
    pygame.display.set_caption('PyTMX Map Viewer')

    try:
        for filename in glob.glob(os.path.join('data', '0.9.1', '*.tmx')):
            logger.info("Testing %s", filename)
            if not SimpleTest(filename).run():
                break
    except:
        pygame.quit()
        raise
