""" Test / Demo / Tutorial of pyscroll and PyTMX

This file is heavily commented to provide useful examples and information how
to build your own game with python, pygame, pyscroll, and pytmx.

- Tested with pygame 1.9 and python 2.7 & 3.3.
- bitcraft (leif dot theden at gmail.com)
"""

import math
import itertools
import pygame
from pygame.locals import *
import pytmx
import logging

# pyscroll is a python 2.7/3.3 project
# using the logging module simplifies "print" statements and has nice output.
# the following sets the logger up for this app.
# NOTE: it is not necessary for your app to do this, but it is a good practice.
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

ZOOM_SPEED = 100
MOVE_SPEED = 100


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class ScrollingRenderer:
    """
    Simple way for rendering a scrolling map that is larger than the display.

                 !!!SUPER IMPORTANT NOTE - YOU MUST READ!!!

    THIS IS NOT THE CORRECT WAY TO DO SCROLLING GAMES IN PYGAME!  THE
    UNDERLYING LIBRARY, SDL, IS NOT SUITED FOR REAL-TIME SCROLLING GAMES.  THIS
    IS ONLY A DEMONSTRATION ON SCROLLING A MAP USING THIS LIBRARY AND IS IN NO
    WAY IMPLIED TO BE THE BEST OR CORRECT WAY.

    DEMONSTRATION IS WRITTEN FOR CLARITY, NOT SPEED

    USE ANOTHER LIBRARY SUCH AS PYSCROLL FOR A BETTER WAY.
    """

    def __init__(self, filename):
        tm = load_pygame(filename, pixelalpha=True)
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

        self.width = self.tmx_data.width * self.tmx_data.tilewidth
        self.height = self.tmx_data.height * self.tmx_data.tileheight

        self.mapwidth = self.tmx_data.width
        self.mapheight = self.tmx_data.height

        self.halfwidth = self.tmx_data.width / 2
        self.halfheight = self.tmx_data.height / 2 + 1

    def render(self, surface, center):
        # TODO: correctly handle imagelayers

        cx, cy = center
        sw, sh = surface.get_size()
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        gt = self.tmx_data.get_tile_image

        stw = int(math.ceil(float(sw) / tw)) + 1
        sth = int(math.ceil(float(sh) / th)) + 1

        txf, pxf = map(int, (divmod((cx - sw / 2), tw)))
        tyf, pyf = map(int, (divmod((cy - sh / 2), th)))

        if stw + txf > self.mapwidth: stw -= 1
        if sth + tyf > self.mapheight: sth -= 1

        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, TiledTileLayer):
                for x, y, in itertools.product(range(stw), range(sth)):
                    tile = gt(x + txf, y + tyf, layer)
                    if tile:
                        surface.blit(tile, (x * tw - pxf, y * th - pyf))

            elif isinstance(layer, TiledObjectGroup):
                pass

            elif isinstance(layer, TiledImageLayer):
                image = self.tmx_data.get_tile_image_by_gid(layer.gid)
                if image:
                    surface.blit(image, (0, 0))


class ScrollingDemo:
    def __init__(self, filename):
        self.running = False
        self.dirty = False
        self.buffer = None
        self.exit_value = 0
        self.camera_vector = [0, 0, 0]
        self.camera_point = [0, 0]
        self.renderer = ScrollingRenderer(filename)
        self.map_pixel_size = (self.renderer.tmx_data.width * self.renderer.tmx_data.tilewidth,
                               self.renderer.tmx_data.height * self.renderer.tmx_data.tileheight)

        self.buffer_size = None
        self._old_buffer_size = None
        self.resize_buffer((self.map_pixel_size[0] / 2, self.map_pixel_size[1] / 2))

    def resize_buffer(self, size):
        def evenify(x):
            even = x % 2
            if self._old_buffer_size:
                more = self._old_buffer_size[0] > size[0]
            else:
                more = True

            if more and even:
                return x + 1
            elif even:
                return x - 1
            else:
                return x

        def non_zero(x):
            return x if x else 1

        self._old_buffer_size = self.buffer_size
        if size[0] > self.map_pixel_size[0]: size[0] = self.map_pixel_size[0]
        if size[1] > self.map_pixel_size[1]: size[1] = self.map_pixel_size[1]
        size = [non_zero(i) for i in size]

        correct_size = [non_zero(evenify(round(i, 0))) for i in size]

        self.buffer = pygame.Surface(correct_size)
        self.buffer_size = list(size)

    def draw_map(self, surface):
        bw, bh = self.buffer.get_size()
        mw, mh = self.map_pixel_size

        if mw >= bw and mw >= bh:
            self.buffer.fill((0, 128, 255))
            self.renderer.render(self.buffer, self.camera_point)
            pygame.transform.scale(self.buffer, surface.get_size(), surface)

    def draw_text(self, surface):
        y = 0
        for i in self.text:
            surface.blit(i, (0, y))
            y += i.get_height()

    def run(self):
        self.exit_value = 0
        self.running = True
        self.dirty = True

        clock = pygame.time.Clock()

        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        t = ["scroll demo. press escape to quit",
             "arrow keys move",
             "z and x will zoom the map"]

        self.text = [f.render(i, 1, (180, 180, 0)) for i in t]

        self.camera_point = [self.buffer.get_width() / 2, self.buffer.get_height() / 2]

        try:
            while self.running:
                dt = clock.tick(60) / 1000.0
                self.handle_input()
                self.update(dt)
                self.draw_map(screen)
                self.draw_text(screen)
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False

    def handle_input(self):
        event = pygame.event.poll()

        if event.type == QUIT:
            self.exit_value = 0
            self.running = False

        elif event.type == KEYDOWN:
            if event.key == K_z:
                self.camera_vector[2] -= ZOOM_SPEED
            if event.key == K_x:
                self.camera_vector[2] += ZOOM_SPEED
            elif event.key == K_UP:
                self.camera_vector[1] -= MOVE_SPEED
            elif event.key == K_DOWN:
                self.camera_vector[1] += MOVE_SPEED
            elif event.key == K_LEFT:
                self.camera_vector[0] -= MOVE_SPEED
            elif event.key == K_RIGHT:
                self.camera_vector[0] += MOVE_SPEED
            elif event.key == K_ESCAPE:
                self.running = False

        elif event.type == KEYUP:
            if event.key == K_z:
                self.camera_vector[2] = 0
            if event.key == K_x:
                self.camera_vector[2] = 0
            elif event.key == K_UP:
                self.camera_vector[1] = 0
            elif event.key == K_DOWN:
                self.camera_vector[1] = 0
            elif event.key == K_LEFT:
                self.camera_vector[0] = 0
            elif event.key == K_RIGHT:
                self.camera_vector[0] = 0

        elif event.type == VIDEORESIZE:
            init_screen(event.w, event.h)
            self.resize_buffer([screen.get_width() / 2, screen.get_height() / 2])

    def update(self, dt):
        self.camera_point[0] += self.camera_vector[0] * dt
        self.camera_point[1] += self.camera_vector[1] * dt

        if not self.camera_vector[2] == 0:
            self.buffer_size[0] += self.camera_vector[2] * dt
            self.buffer_size[1] += self.camera_vector[2] * dt

            if (self.buffer_size[0] < 1) or (self.buffer_size[1] < 0):
                self.buffer_size[0] += 1 - self.buffer_size[0]
                self.buffer_size[1] += 1 - self.buffer_size[1]

            if self.buffer_size[0] > screen.get_width() / 2:
                self.buffer_size = [screen.get_width() / 2, screen.get_height() / 2]
                self.camera_vector[2] = 0

            self.resize_buffer(self.buffer_size)

        sw, sh = self.buffer.get_size()
        mw, mh = self.map_pixel_size
        hsw = sw / 2
        hsh = sh / 2

        if self.renderer.width > sw:
            if self.camera_point[0] < hsw:
                self.camera_point[0] = hsw
                self.camera_vector[0] = 0
            elif self.camera_point[0] > mw - hsw - 1:
                self.camera_point[0] = mw - hsw - 1
                self.camera_vector[0] = 0
        else:
            self.camera_point[0] = self.renderer.width / 2

        if self.renderer.height > sh:
            if self.camera_point[1] < hsh:
                self.camera_point[1] = hsh
                self.camera_vector[1] = 0
            elif self.camera_point[1] > mh - hsh - 1:
                self.camera_point[1] = mh - hsh - 1
                self.camera_vector[1] = 0
        else:
            self.camera_point[1] = self.renderer.height / 2

if __name__ == '__main__':
    import os
    import sys

    pygame.init()
    pygame.font.init()
    screen = init_screen(600, 600)
    pygame.display.set_caption('PyTMX Advanced Rendering Demo')

    try:
        filename = sys.argv[1]
    except IndexError:
        print('no TMX map specified, using default')
        filename = os.path.join('data', 'legacy', 'formosa-base64-gzip.tmx')

    try:
        demo = ScrollingDemo(filename)
        demo.run()
    except:
        pygame.quit()
        raise