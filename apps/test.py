""" Test of the PyTMX loader and example rendering function with app

Typically this is run to verify that any code changes do do break the loader.
Tests all Tiled features -except- terrains, which are unsupported.

This file is heavily commented to provide useful examples and information how
to build your own game with python, pygame, and pytmx.

- Tested with pygame 1.9 and python 2.7 & 3.3.
- bitcraft (leif dot theden at gmail.com)
"""

import pygame
from pygame.locals import *
import pytmx
import logging

# pytmx is a python 2.7/3.3 project
# using the logging module simplifies "print" statements and has nice output.
# the following sets the logger up for this app.
# NOTE: it is not necessary for your app to do this, but it is a good practice.
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)


# this is used to make sure the screen is resizable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class TiledRenderer(object):
    """ Super simple way to render a tiled map onto a surface
    """
    def __init__(self, filename):

        # load the data from pytmx
        # pixelalpha is True so that the loader will correctly use transparency
        # if your tileset doesn't use transparent tiles, you can remove
        # pixel alpha=True and you will have slightly better performance
        # depending on the tileset.
        tmx = pytmx.load_pygame(filename, pixelalpha=True)

        # size is the size of the entire map in pixels
        self.size = tmx.width * tmx.tilewidth, tmx.height * tmx.tileheight

        # save a reference in this instance
        self.tmx_data = tmx

    def render(self, surface):
        """ Render the map to a surface

        This function will render the entire map to a surface.  The surface
        must be the same size as the map's pixel size (see __init__).

        This is meant to be a guide to building your own game, but you don't
        have to follow it exactly.
        """

        # deref these heavily used variables for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        gt = self.tmx_data.get_tile_image_by_gid

        # fill the background color
        if self.tmx_data.background_color:
            surface.fill(self.tmx_data.background_color)

        # visible_layers is a generator of all the layers that are visible
        # we are going to go through each one and draw them
        for layer in self.tmx_data.visible_layers:

            # if this layer is a tile layer
            if isinstance(layer, pytmx.TiledTileLayer):

                # using this loop, it is easy to get the tiles in the layer
                # this iterator returns the GID of each tile
                # the GID is a unique number that specifies a tile image
                for x, y, gid in layer:

                    # get the image for the GID
                    tile = gt(gid)

                    # get_tile_image_by_gid may return 0, which means there is
                    # no tile for that x, y coordinate
                    if tile:

                        # finally, blit the tile to the surface
                        # x, y is in tile coordinates
                        # you need to multiply by the tile height and tile width
                        # to get the position on the screen
                        surface.blit(tile, (x * tw, y * th))

            # if this layer is an object layer
            elif isinstance(layer, pytmx.TiledObjectGroup):

                # using this iterator, you can access the objects in a layer
                for o in layer:

                    # some objects have points
                    # the points are used to define a polygon or line
                    if hasattr(o, 'points'):

                        # if o.closed is true, then the object is a polygon
                        # o.points is a list of (x,y) points
                        # this list is in pixel coordinates, so we just pass it
                        # to pygame.draw.lines, and it handles it for us
                        pygame.draw.lines(surface, (255, 128, 128), o.closed, o.points, 2)

                    # Tiled and pytmx support "tile objects"
                    # tile objects are objects, but they use a tile image from
                    # a tileset and have a set size.  if there is a gid, then
                    # the object is a tile object.
                    elif o.gid:

                        # just like drawing a layer, get the image
                        tile = self.tmx_data.get_tile_image_by_gid(o.gid)
                        if tile:
                            surface.blit(tile, (o.x, o.y))
                    else:

                        # this will handle boxes, rectangles and ellipses
                        pygame.draw.rect(surface, (255, 128, 128), (o.x, o.y, o.width, o.height), 2)

            # if this layer is an image layer
            # image layers simply have an image associated with them
            # pytmx stores the image with a gid, which we retrieve here
            elif isinstance(layer, pytmx.TiledImageLayer):

                # this is the same method as getting tile images
                image = gt(layer.gid)
                if image:
                    surface.blit(image, (0, 0))


class SimpleTest(object):
    """ Test and demo of the loading functions of PyTMX.

    PyTMX doesn't include any way to render a map.  Using this class as a guide,
    you can build a rending system that works for you and your game or app.
    """
    def __init__(self, filename):
        self.renderer = None     # deligate rendering to another class
        self.running = False     # true when the test is running
        self.dirty = False       # true when the screen needs to be drawn again
        self.exit_status = 0     # n/a

        self.load_map(filename)

    def load_map(self, filename):

        # use the renderer that is defined above
        self.renderer = TiledRenderer(filename)

        # use our logger to write some interesting info to the console
        # this is information about the objects
        logger.info("Objects in map:")
        for o in self.renderer.tmx_data.objects:
            logger.info(o)
            for k, v in o.properties.items():
                logger.info("  %s %s", k, v)

        # this is information about the tiles with properties
        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("  %s %s", k, v)

    def draw(self, surface):
        """ Draw the map to a surface
        """
        # create a temporary surface that is the same size as the entire map
        temp = pygame.Surface(self.renderer.size)

        # draw (render) the entire map to the temporary surface
        self.renderer.render(temp)

        # shrink the temporary surface to match the surface size
        pygame.transform.smoothscale(temp, surface.get_size(), surface)

        # create new font, render a message
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press any key for next map or ESC to quit', 1, (180, 180, 0))

        # blit the message on the surface
        surface.blit(i, (0, 0))

    def handle_input(self):
        """ Simply handle pygame input events
        """
        try:
            # using wait() since this app only responds to input
            # it is more efficient than polling for input over and over
            # for apps that only change when there is input
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

            # this will be handled if the window is resized
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