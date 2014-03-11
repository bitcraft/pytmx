"""
This is tested on pygame 1.9 and python 3.3.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the TMXLoader.

Typically this is run to verify that any code changes do do break the loader.

untested:
    image layers
"""
import os.path
import glob
import pygame
from pygame.locals import *
from pytmx import *


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """
    def __init__(self, filename):
        self.tiledmap = tmxloader.load_pygame(filename, pixelalpha=True)

    def render(self, surface):
        # not going for efficiency here
        # for demonstration purposes only

        tw = self.tiledmap.tilewidth
        th = self.tiledmap.tileheight
        gt = self.tiledmap.get_tile_image

        # fill the background color
        if self.tiledmap.background_color:
            surface.fill(self.tiledmap.background_color)

        # draw map tiles
        for layer in self.tiledmap.visible_layers:
            if isinstance(layer, TiledTileLayer):
                for x, y, gid in layer:
                    tile = gt(x, y, layer)
                    if tile:
                        surface.blit(tile, (x * tw, y * th))

            elif isinstance(layer, TiledObjectGroup):
                pass

            elif isinstance(layer, TiledImageLayer):
                image = self.tiledmap.get_tile_image_by_gid(layer.gid)
                if image:
                    surface.blit(image, (0, 0))

        # draw polygon and poly line objects
        for o in self.tiledmap.objects:
            if hasattr(o, 'points'):
                points = [(i[0] + o.x, i[1] + o.y) for i in o.points]
                pygame.draw.lines(surface, (255, 128, 128), o.closed, points, 2)
            elif hasattr(o, 'gid'):
                tile = self.tiledmap.get_tile_image_by_gid(o.gid)
                if tile:
                    surface.blit(tile, (o.x, o.y))


def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def simple_test(filename):
    print("Testing", filename)

    def draw():
        sw, sh = screen.get_size()
        screen_buf = pygame.Surface((sw/2, sh/2))
        formosa.render(screen_buf)
        pygame.transform.scale(screen_buf, screen.get_size(), screen)
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render(filename, 1, (180, 180, 0))
        screen.blit(i, (0, 0))
        pygame.display.flip()

    formosa = TiledRenderer(filename)
    draw()

    print("Objects in map:")
    for o in formosa.tiledmap.objects:
        print(o)
        for k, v in o.__dict__.items():
            print("  ", k, v)

    print("GID (tile) properties:")
    for k, v in formosa.tiledmap.tile_properties.items():
        print("  ", k, v)

    run = True
    while run:
        try:
            event = pygame.event.wait()

            if event.type == QUIT:
                run = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    run = False

                break

            elif event.type == MOUSEBUTTONDOWN:
                break

            elif event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                draw()

        except KeyboardInterrupt:
            run = False

    return run

pygame.init()
pygame.font.init()
screen = init_screen(600, 600)
pygame.display.set_caption('TMXLoader Test')

for filename in glob.glob(os.path.join('0.9.1', '*.tmx')):
    if not simple_test(filename):
        break

pygame.quit()
