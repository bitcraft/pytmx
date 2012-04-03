"""
This is tested on pygame 1.9 and python 2.7.
This will not work on python 3.  Don't ask either.  I will say 'no'.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader.  This simply shows that the loader works.
If you need a rendering library that will handle large maps and scrolling, you
can check out my lib2d project at pygame.org.  Have fun!
"""

class TiledRenderer():
    """
    Super simple way to render a tiled map
    """

    def __init__(self, filename):
        from pytmx import tmxloader
        self.tiledmap = tmxloader.load_pygame(filename, pixelalpha=True)
   
 
    def render(self, surface):
        # not going for effeciency here
        # for demonstration purposes only

        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.getTileImage

        for l in xrange(0, len(self.tiledmap.layers)):
            for y in xrange(0, self.tiledmap.height):
                for x in xrange(0, self.tiledmap.width):
                    tile = gt(x, y, l)
                    if not tile == 0: surface.blit(tile, (x*tw, y*th))

import pygame
from pygame.locals import *

pygame.init()
screen = pygame.display.set_mode((480, 480))
pygame.display.set_caption('TMXLoader Test')

screen_buf = pygame.Surface((240, 240))
screen_buf.fill((0,128,255))
formosa = TiledRenderer("formosa.tmx")
formosa.render(screen_buf)
pygame.transform.scale2x(screen_buf, screen)
pygame.display.flip()

run = True

while run:
    try:
        event = pygame.event.wait()
        if (event.type == QUIT) or (event.type == KEYDOWN): run = False

    except KeyboardInterrupt:
        run = False

pygame.quit()
