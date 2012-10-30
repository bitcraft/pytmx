"""
This is tested on pygame 1.9 and python 2.6 and 2.7.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader.  Typically this is run to verify that any
code changes do do break the loader.
"""

class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """

    def __init__(self, filename):
        from pytmx import tmxloader
        self.tiledmap = tmxloader.load_pygame(filename, pixelalpha=True)


    def render(self, surface):
        # not going for efficiency here
        # for demonstration purposes only

        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.getTileImage

        # draw map tiles
        for l in xrange(0, len(self.tiledmap.tilelayers)):
            for y in xrange(0, self.tiledmap.height):
                for x in xrange(0, self.tiledmap.width):
                    tile = gt(x, y, l)
                    if tile: surface.blit(tile, (x*tw, y*th))

        # draw polygon and poly line objects
        for og in self.tiledmap.objectgroups:
            for o in og:
                if hasattr(o, 'points'):
                    points = [ (i[0]+o.x, i[1]+o.y) for i in o.points ]
                    pygame.draw.lines(surface, (255,128,128), o.closed, points, 2)
                else:
                    pygame.draw.rect(surface, (255,128,128),
                                    (o.x, o.y, o.width, o.height), 2)

import pygame
from pygame.locals import *
import math, glob


pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((480, 480))
pygame.display.set_caption('TMXLoader Test')


def simpleTest(filename):
    screen_buf = pygame.Surface((240, 240))
    screen_buf.fill((0,128,255))
    formosa = TiledRenderer(filename)
    formosa.render(screen_buf)
    pygame.transform.scale(screen_buf, screen.get_size(), screen)
    f = pygame.font.Font(pygame.font.get_default_font(), 20)
    i = f.render(filename, 1, (180,180,0))
    screen.blit(i, (0,0))
    pygame.display.flip()

    print "Objects in map:"
    for o in formosa.tiledmap.getObjects():
        print o
        for k, v in o.__dict__.items():
            print "  ", k, v

    print "GID (tile) properties:"
    for k, v in formosa.tiledmap.tile_properties.items():
        print "  ", k, v

    run = True
    while run:
        try:
            event = pygame.event.wait()
            if (event.type == QUIT) or (event.type == KEYDOWN): run = False

        except KeyboardInterrupt:
            run = False


for filename in glob.glob('*.tmx'):
    print "testing", filename
    simpleTest(filename)

pygame.quit()
