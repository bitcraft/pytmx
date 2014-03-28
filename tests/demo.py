"""
This is tested on pygame 1.9 and python 2.7.
This will not work on python 3.  Don't ask either.  I will say 'no'.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader.  This simply shows that the loader works.
If you need a rendering library that will handle large maps and scrolling, you
can check out my lib2d project at pygame.org.  Have fun!

In this demo, I am accessing the layer and map data directly.  It is perfectly
fine to develop a data structure that works for you.


Known bugs:
    Tile Objects are not handled by any renderer.


"""

class TiledRenderer(object):
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

        for l in xrange(0, len(self.tiledmap.tilelayers)):
            for y in xrange(0, self.tiledmap.height):
                for x in xrange(0, self.tiledmap.width):
                    tile = gt(x, y, l)
                    if tile: surface.blit(tile, (x*tw, y*th))


class ScrollingRenderer(TiledRenderer):
    """
    Simple way for rendering a scrolling map that is larger than the display.

                 !!!SUPER IMPORTANT NOTE - YOU MUST READ!!!

    THIS IS NOT THE CORRECT WAY TO DO SCROLLING GAMES IN PYGAME!  THE
    UNDERLYING LIBRARY, SDL, IS NOT SUITED FOR REAL-TIME SCROLLING GAMES.  THIS
    IS ONLY A DEMONSTRATION ON SCROLLING A MAP USING THIS LIBRARY AND IS IN NO
    WAY IMPLIED TO BE THE BEST OR CORRECT WAY.
    """

    def __init__(self, filename):
        super(ScrollingRenderer, self).__init__(filename)
        self.width = self.tiledmap.width * self.tiledmap.tilewidth
        self.height = self.tiledmap.height * self.tiledmap.tileheight

        self.mapwidth = self.tiledmap.width
        self.mapheight = self.tiledmap.height

        self.halfwidth = self.tiledmap.width / 2
        self.halfheight = self.tiledmap.height / 2 + 1


    def render(self, surface, (cx, cy)):
        sw, sh = surface.get_size()
        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.getTileImage

        stw = int(math.ceil(float(sw) / tw)) + 1
        sth = int(math.ceil(float(sh) / th)) + 1

        txf, pxf = divmod((cx-sw/2), tw)
        tyf, pyf = divmod((cy-sh/2), th)

        if stw + txf > self.mapwidth: stw -= 1
        if sth + tyf > self.mapheight: sth -= 1

        p = product(xrange(stw), xrange(sth),
                    xrange(len(self.tiledmap.tilelayers)))

        for x, y, l in p:
            tile = gt(x+txf, y+tyf, l)
            if tile: surface.blit(tile, (x*tw-pxf, y*th-pyf))



import pygame
from pygame.locals import *
import math
from itertools import product


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
    i = f.render("simple demo. press any key to continue", 1, (180,180,0))
    screen.blit(i, (0,0))
    pygame.display.flip()

    run = True
    while run:
        try:
            event = pygame.event.wait()
            if (event.type == QUIT) or (event.type == KEYDOWN): run = False

        except KeyboardInterrupt:
            run = False


def scrollTest(filename):
    buf_dim = [screen.get_width() / 2, screen.get_height() / 2]
    center = [buf_dim[0]/2, buf_dim[1]/2]
    movt = [0, 0, 0]

    clock = pygame.time.Clock()
    screen_buf = pygame.Surface(buf_dim)
    formosa = ScrollingRenderer(filename)
    mw = formosa.tiledmap.width * formosa.tiledmap.tilewidth
    mh = formosa.tiledmap.height * formosa.tiledmap.tileheight

    f = pygame.font.Font(pygame.font.get_default_font(), 20)
    t = ["scroll demo. press escape to quit",
         "arrow keys move",
         "z and x will zoom the map"]

    text = [ f.render(i, 1, (180, 180, 0)) for i in t ]

    def draw():
        bw, bh = screen_buf.get_size()
        sw, sh = screen.get_size()

        if (sw >= bw) and (sh >= bh):
            y = 0
            screen_buf.fill((0,128,255))
            formosa.render(screen_buf, center)
            pygame.transform.smoothscale(screen_buf, (sw, sh), screen)
            for i in text:
                screen.blit(i, (0,y))
                y += i.get_height()
        else:
            pass


    draw()
    run = True
    while run:
        try:
            clock.tick(30)
            event = pygame.event.poll()

            if event.type == QUIT: run = False
            elif event.type == KEYDOWN:
                if event.key == K_z:
                    movt[2] -= 2
                if event.key == K_x:
                    movt[2] += 2
                elif event.key == K_UP:
                    movt[1] -= 1
                elif event.key == K_DOWN:
                    movt[1] += 1
                elif event.key == K_LEFT:
                    movt[0] -= 1
                elif event.key == K_RIGHT:
                    movt[0] += 1
                elif event.key == K_ESCAPE:
                    run = False

            center[0] += movt[0]
            center[1] += movt[1]
            if not movt[2] == 0:
                buf_dim[0] += movt[2]
                buf_dim[1] += movt[2]
                if (buf_dim[0] < 1) or (buf_dim[1] < 0):
                    buf_dim[0] += 1 - buf_dim[0]
                    buf_dim[1] += 1 - buf_dim[1]
                if buf_dim[0] > screen.get_width() / 2:
                    buf_dim = [screen.get_width() / 2, screen.get_height() / 2]
                    movt[2] = 0
                screen_buf = pygame.Surface(buf_dim)

            sw, sh = screen_buf.get_size()
            hsw = sw / 2
            hsh = sh / 2

            if formosa.width > sw:
                if center[0] < hsw:
                    center[0] = hsw
                    movt[0] = 0
                elif center[0] > mw - hsw-1:
                    center[0] = mw - hsw-1
                    movt[0] = 0
            else:
                center[0] = formosa.width / 2

            if formosa.height > sh:
                if center[1] < hsh:
                    center[1] = hsh
                    movt[1] = 0
                elif center[1] > mh - hsh - 1:
                    center[1] = mh - hsh - 1
                    movt[1] = 0
            else:
                center[1] = formosa.height / 2

            draw()
            pygame.display.flip()


        except KeyboardInterrupt:
            run = False


if __name__ == "__main__":
    import sys
    import os

    try:
        filename = sys.argv[1]
    except:
        print "no TMX map specified, using default"
        filename = os.path.join('data', 'legacy', 'formosa-base64-gzip.tmx')

    simpleTest(filename)
    scrollTest(filename)

    pygame.quit()
