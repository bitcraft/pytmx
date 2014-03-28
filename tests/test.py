"""
This is tested on pygame 1.9 and python 2.7.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader.

Typically this is run to verify that any code changes do do break the loader.
Tests all Tiled features -except- terrains.
"""

import pygame
from pygame.locals import *
from pytmx import *


def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """
    def __init__(self, filename):
        tm = load_pygame(filename, pixelalpha=True)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

    def render(self, surface):
        # not going for efficiency here
        # for demonstration purposes only

        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        gt = self.tmx_data.getTileImageByGid

        # fill the background color
        if self.tmx_data.background_color:
            surface.fill(self.tmx_data.background_color)

        # draw map tiles
        for layer in self.tmx_data.visibleLayers:
            if isinstance(layer, TiledLayer):
                for x, y, gid in layer:
                    tile = gt(gid)
                    if tile:
                        surface.blit(tile, (x * tw, y * th))

            elif isinstance(layer, TiledObjectGroup):
                pass

            elif isinstance(layer, TiledImageLayer):
                image = gt(layer.gid)
                if image:
                    surface.blit(image, (0, 0))

        # draw polygon and poly line objects
        for o in self.tmx_data.getObjects():
            if hasattr(o, 'points'):
                pygame.draw.lines(surface, (255, 128, 128), o.closed, o.points, 2)
            elif o.gid:
                tile = self.tmx_data.getTileImageByGid(o.gid)
                if tile:
                    surface.blit(tile, (o.x, o.y))
            else:
                pygame.draw.rect(surface, (255, 128, 128), (o.x, o.y, o.width, o.height), 2)


class SimpleTest(object):
    def __init__(self, filename):
        self.renderer = None
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.load_map(filename)

    def load_map(self, filename):
        self.renderer = TiledRenderer(filename)

        print "Objects in map:"
        for o in self.renderer.tmx_data.getObjects():
            print o
            for k, v in o.__dict__ .items():
                print "  ", k, v

        print "GID (tile) properties:"
        for k, v in self.renderer.tmx_data.tile_properties.items():
            print "  ", k, v

    def draw(self, surface):
        temp = pygame.Surface(self.renderer.size)
        self.renderer.render(temp)
        pygame.transform.smoothscale(temp, surface.get_size(), surface)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press any key for next map or ESC to quit', 1, (180, 180, 0))
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

            #elif event.type == MOUSEBUTTONDOWN:
            #    self.running = False

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
            print "Testing", filename
            if not SimpleTest(filename).run():
                break

        for filename in glob.glob(os.path.join('data', 'legacy', '*.tmx')):
            print "Testing", filename
            if not SimpleTest(filename).run():
                break
    except:
        pygame.quit()
        raise