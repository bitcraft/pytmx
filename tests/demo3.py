"""
This is tested on pygame 1.9 and python 3.3.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader3.

Known bugs:
    Tile Objects are not handled by any renderer.
"""
import math
import pygame
from pygame.locals import *
from itertools import product


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """
    def __init__(self, filename):
        from pytmx3 import tmxloader
        self.tiledmap = tmxloader.load_pygame(filename, pixelalpha=True)

    def render(self, surface):
        # not going for efficiency here
        # for demonstration purposes only

        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.get_tile_image

        for l in range(0, len(self.tiledmap.tilelayers)):
            for y in range(0, self.tiledmap.height):
                for x in range(0, self.tiledmap.width):
                    tile = gt(x, y, l)
                    if tile: surface.blit(tile, (x * tw, y * th))


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

    def render(self, surface, center):
        cx, cy = center
        sw, sh = surface.get_size()
        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.get_tile_image

        stw = int(math.ceil(float(sw) / tw)) + 1
        sth = int(math.ceil(float(sh) / th)) + 1

        txf, pxf = divmod((cx - sw / 2), tw)
        tyf, pyf = divmod((cy - sh / 2), th)

        if stw + txf > self.mapwidth: stw -= 1
        if sth + tyf > self.mapheight: sth -= 1

        p = product(range(stw), range(sth),
                    range(len(self.tiledmap.tilelayers)))

        for x, y, l in p:
            tile = gt(x + txf, y + tyf, l)
            if tile:
                surface.blit(tile, (x * tw - pxf, y * th - pyf))


def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def simple_test(filename):
    def draw():
        tw = formosa.tiledmap.width * formosa.tiledmap.tilewidth
        th = formosa.tiledmap.height * formosa.tiledmap.tileheight
        map_buffer = pygame.Surface((tw, th))
        map_buffer.fill((0, 128, 255))
        formosa.render(map_buffer)
        pygame.transform.scale(map_buffer, screen.get_size(), screen)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render("simple demo. press any key to continue", 1, (180, 180, 0))
        screen.blit(i, (0, 0))
        pygame.display.flip()

    formosa = TiledRenderer(filename)
    draw()
    run = True
    while run:
        try:
            event = pygame.event.poll()
            if (event.type == QUIT) or (event.type == KEYDOWN):
                run = False
            if event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                draw()
        except KeyboardInterrupt:
            run = False


def scroll_test(filename):
    def init_buffer(size):
        if size[0] > mw: size[0] = mw
        if size[1] > mh: size[1] = mh
        s = pygame.Surface(size)
        b = list(map(int, size))
        return s, b

    def draw():
        bw, bh = map_buffer.get_size()
        sw, sh = screen.get_size()

        if (sw >= bw) and (sh >= bh):
            y = 0
            map_buffer.fill((0, 128, 255))
            formosa.render(map_buffer, center)
            pygame.transform.smoothscale(map_buffer, (sw, sh), screen)
            for i in text:
                screen.blit(i, (0, y))
                y += i.get_height()
        else:
            pass

    clock = pygame.time.Clock()
    formosa = ScrollingRenderer(filename)
    mw = formosa.tiledmap.width * formosa.tiledmap.tilewidth
    mh = formosa.tiledmap.height * formosa.tiledmap.tileheight

    f = pygame.font.Font(pygame.font.get_default_font(), 20)
    t = ["scroll demo. press escape to quit",
         "arrow keys move",
         "z and x will zoom the map"]

    text = [f.render(i, 1, (180, 180, 0)) for i in t]

    map_buffer, map_buffer_size = init_buffer([screen.get_width() / 2, screen.get_height() / 2])
    center = [int(map_buffer.get_width() / 2), int(map_buffer.get_height() / 2)]
    movt = [0, 0, 0]

    draw()
    run = True
    while run:
        try:
            clock.tick(60)
            event = pygame.event.poll()

            if event.type == QUIT:
                run = False
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

            elif event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                map_buffer, map_buffer_size = init_buffer([screen.get_width() / 2, screen.get_height() / 2])

            center[0] += movt[0]
            center[1] += movt[1]
            if not movt[2] == 0:
                map_buffer_size[0] += movt[2]
                map_buffer_size[1] += movt[2]
                if (map_buffer_size[0] < 1) or (map_buffer_size[1] < 0):
                    map_buffer_size[0] += 1 - map_buffer_size[0]
                    map_buffer_size[1] += 1 - map_buffer_size[1]
                if map_buffer_size[0] > screen.get_width() / 2:
                    map_buffer_size = [screen.get_width() / 2, screen.get_height() / 2]
                    movt[2] = 0
                map_buffer, map_buffer_size = init_buffer(map_buffer_size)

            sw, sh = map_buffer.get_size()
            hsw = sw / 2
            hsh = sh / 2

            if formosa.width > sw:
                if center[0] < hsw:
                    center[0] = hsw
                    movt[0] = 0
                elif center[0] > mw - hsw - 1:
                    center[0] = mw - hsw - 1
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


import sys
sys.path.append('..')

pygame.init()
pygame.font.init()
screen = init_screen(200, 200)
pygame.display.set_caption('TMXLoader Test')

try:
    filename = sys.argv[1]
except IndexError:
    print("no TMX map specified, using default")
    filename = "formosa-base64-gzip.tmx"

simple_test(filename)
scroll_test(filename)

pygame.quit()
