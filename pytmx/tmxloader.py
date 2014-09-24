import itertools
import os
import pygame
import pytmx
import logging
from pygame.transform import flip, rotate
from .constants import *

__all__ = ['load_pygame']


logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)


def handle_transformation(tile, flags):
    if flags:
        fx = flags & TRANS_FLIPX == TRANS_FLIPX
        fy = flags & TRANS_FLIPY == TRANS_FLIPY
        r = flags & TRANS_ROT == TRANS_ROT

        newtile = None
        if r:
            # not sure why the flip is required...but it is.
            newtile = rotate(tile, 270)
            newtile = flip(newtile, 1, 0)

            if fx or fy:
                newtile = flip(newtile, fx, fy)

        elif fx or fy:
            newtile = flip(tile, fx, fy)

        return newtile

    else:
        return tile


def smart_convert(original, colorkey, pixelalpha):
    """
    this method does several tests on a surface to determine the optimal
    flags and pixel format for each tile surface.

    this is done for the best rendering speeds and removes the need to
    convert() the images on your own
    """
    tile_size = original.get_size()

    # TODO: test how the 'threshold' value effects transparent pixel detection
    threshold = 127   # the default

    # count the number of pixels in the tile that are not transparent
    px = pygame.mask.from_surface(original, threshold).count()

    # there are no transparent pixels in the image
    if px == tile_size[0] * tile_size[1]:
        tile = original.convert()

    # there are transparent pixels, and tiled set a colorkey
    elif colorkey:
        tile = original.convert()
        tile.set_colorkey(colorkey, pygame.RLEACCEL)

    # there are transparent pixels, and set for perpixel alpha
    elif pixelalpha:
        tile = original.convert_alpha()

    # there are transparent pixels, and we won't handle them
    else:
        tile = original.convert()

    return tile


def _load_images_pygame(tmxdata, mapping, *args, **kwargs):
    """  Utility function to load images.  Used internally!
    """

    # optional keyword arguments checked here
    pixelalpha = kwargs.get('pixelalpha', True)
    optional_gids = kwargs.get('optional_gids', None)
    load_all_tiles = kwargs.get('load_all', False)

    if tmxdata.background_color:
        tmxdata.background_color = pygame.Color(tmxdata.background_color)

    tmxdata.images = [None] * tmxdata.maxgid

    # load tileset image
    for ts in tmxdata.tilesets:
        if ts.source is None:
            continue

        path = os.path.join(os.path.dirname(tmxdata.filename), ts.source)
        image = pygame.image.load(path)
        w, h = image.get_size()

        tilewidth = ts.tilewidth + ts.spacing
        tileheight = ts.tileheight + ts.spacing
        tile_size = ts.tilewidth, ts.tileheight

        # some tileset images may be slightly larger than the tile area
        # ie: may include a banner, copyright, ect.  this compensates for that
        width = int((((w - ts.margin * 2 + ts.spacing) // tilewidth) * tilewidth) - ts.spacing)
        height = int((((h - ts.margin * 2 + ts.spacing) // tileheight) * tileheight) - ts.spacing)

        # trim off any pixels on the right side that isn't a tile.
        # this happens if extra stuff is included on the left, like a logo or
        # credits, not actually part of the tileset.
        width -= (w - ts.margin) % tilewidth

        # using product avoids the overhead of nested loops
        p = itertools.product(range(ts.margin, height + ts.margin, tileheight),
                              range(ts.margin, width + ts.margin, tilewidth))

        colorkey = getattr(ts, 'trans', None)
        if colorkey:
            colorkey = pygame.Color('#{0}'.format(colorkey))

        for real_gid, (y, x) in enumerate(p, ts.firstgid):
            if x + ts.tilewidth-ts.spacing > width:
                continue

            gids = tmxdata.map_gid(real_gid)
            if gids is None:
                if load_all_tiles or real_gid in optional_gids:
                    # TODO: handle flags? - might never be an issue, though
                    gids = [tmxdata.register_gid(real_gid, flags=0)]

            if gids:
                try:
                    original = image.subsurface(((x, y), tile_size))
                except ValueError:
                    logger.error('Tile bounds outside bounds of tileset image')
                    raise

                for gid, flags in gids:
                    tile = handle_transformation(original, flags)
                    tile = smart_convert(tile, colorkey, pixelalpha)
                    tmxdata.images[gid] = tile

    # load image layer images
    for layer in tmxdata.layers:
        if isinstance(layer, pytmx.TiledImageLayer):
            colorkey = getattr(layer, 'trans', None)
            if colorkey:
                colorkey = pygame.Color("#{0}".format(colorkey))

            source = getattr(layer, 'source', None)
            if source:
                real_gid = len(tmxdata.images)
                gid = tmxdata.register_gid(real_gid)
                layer.gid = gid
                path = os.path.join(os.path.dirname(tmxdata.filename), source)
                image = pygame.image.load(path)
                image = smart_convert(image, colorkey, pixelalpha)
                tmxdata.images.append(image)

    # load images in tiles.
    # instead of making a new gid, replace the reference to the tile that was
    # loaded from the tileset
    for real_gid, props in tmxdata.tile_properties.items():
        source = props.get('source', None)
        if source:
            colorkey = props.get('trans', None)
            path = os.path.join(os.path.dirname(tmxdata.filename), source)
            image = pygame.image.load(path)
            image = smart_convert(image, colorkey, pixelalpha)
            tmxdata.images[real_gid] = image


def load_pygame(filename, *args, **kwargs):
    """
    PYGAME USERS: Use me.

    Load a TMX file, load the images, and return a TiledMap class that is
    ready to use.

    this utility has 'smart' tile loading.  by default any tile without
    transparent pixels will be loaded for quick blitting.  if the tile has
    transparent pixels, then it will be loaded with per-pixel alpha.  this is
    a per-tile, per-image check.

    if a color key is specified as an argument, or in the tmx data, the
    per-pixel alpha will not be used at all. if the tileset's image has colorkey
    transparency set in Tiled, the loader will return images that have their
    transparency already set.

    TL;DR:
    Don't attempt to convert() or convert_alpha() the individual tiles.  It is
    already done for you.
    """
    tmxdata = pytmx.TiledMap(filename)
    _load_images_pygame(tmxdata, None, *args, **kwargs)
    return tmxdata
