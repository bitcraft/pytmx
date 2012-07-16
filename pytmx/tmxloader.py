"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v.15 - for python 2.6 and 2.7

If you have any problems or suggestions, please contact me via email.
Tested with Tiled 0.8.1 for Mac.

released under the LGPL v3

===============================================================================

This map loader can be used to load maps created in the Tiled map editor.  It
provides a simple way to get tiles and associated metadata so that you can draw
a map onto the screen.  It does not force you to draw your map in any
particular way.

This module doesn't require you to use the classes exposed here.  If you wish,
you can load the map with this module, extract the data from it using the
methods in the TiledMap class, and use your own game engine.

This is *not* a rendering engine.  It will load the data that is necessary to
render a map onto the screen and extract the metadata for object.  For Pygame,
all tile images will be loaded into in memory and available to blit onto the
screen.


Design Goals:
    Simple api
    Memory efficient and fast

Features:
    Loads data and "properties" metadata from Tile's TMX format
    "Properties" for: maps, tilesets, layers, objectgroups, objects, and tiles
    Point data for polygon and polyline objects
    Automatic flipping and rotation of tiles
    Supports base64, csv, gzip, zlib and uncompressed XML
    Image loading with pygame

New in .15:
    loader: new getTileLayerByName(name) method
    loader: python 2.6 support
    loader: fixed issue where objects with tile gid did not load properties
    loader: polygon and polyline objects
    loader: new lookup methods use iterators
    loader: loading function moved into classes
    loader: data/images can be reloaded on the fly
    loader: uses etree for faster xml parsing

New in .14:
    loader: Fixed gid lookup for "buildDistributionRects"
    loader: Added useful output to a few classes "__repr__"
    loader: Fixed a gid mapping issue that broke rotated tiles
    pygame: fixed colorkey handling
    pygame: correctly handles margins and spacing between tiles in tilesets
    pygame: b/c of changes, now correctly renders tiled's example maps
    added scrolling demo

New in .13:
    loader: Renamed "get_tile_image" to "getTileImage"
    loader: Removed duplicates returned from getTilePropertiesByLayer
    loader: Modified confusing messages for GID errors
    loader: Fixed bug where transformed tile properties are not available
    loader: No longer loads metadata for tiles that are not used
    loader: Reduced tile cache to 256 unique tiles
    loader: Removed 'visible' from list of reserved words
    loader: Added 'buildDistributionRects' and maputils module
    loader: Added some misc. functions for retrieving properties
    pygame: Smarter tile management made tile loading cache useless; removed it
    pygame: pygame.RLEACCEL flag added when appropriate

New in .12:
    loader: Fixed bug where tile properties could contain reserved words
    loader: Reduced size of image index by only allocating space for used tiles

New in .11:
    loader: Added support for tileset properties
    loader: Now checks for property names that are reserved for internal use
    loader: Added support for rotated tiles
    pygame: Only the tiles that are used in the map will be loaded into memory
    pygame: Added support for rotated tiles
    pygame: Added option to force a bitsize (depth) for surfaces
    pygame: Added option to convert alpha transparency to colorkey transparency
    pygame: Tilesets no longer load with per-pixel alphas by default
    pygame: Colorkey transparency should be correctly handled now


I have been intentionally not including a module rendering utility since
rendering a map will have different requirements for every situation.  However,
I can appreciate that some people won't understand how it works unless they see
it, so I am including a sample map and viewer.  It includes a scrolling/zooming
renderer.  They are for demonstration purposes, and may not be suitable for all
projects.  Use at your own risk.

I've also included a copy of this loader that may work with python 3.x.  I
personally do not think that python 3.x should be used with pygame, yet (and I
am not the only person).  You can try it if you insist on using pygame with
python 3.x, but I don't update that often.

===============================================================================

Installation:

    There is no install script.  To use PyTMX in your projects, just copy
    the folder into your project directory and follow the guide below.


Basic usage sample:

    >>> from pytmx import tmxloader
    >>> tmxdata = tmxloader.load_pygame("map.tmx")
    >>> tmxdata = tmxloader.load_pygame("map.tmx", pixel_alpha=True)

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


When you want to draw tiles, you simply call "getTileImage":

    >>> image = tmxdata.getTileImage(x, y, layer)
    >>> screen.blit(position, image)


Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tmxdata.tilelayers[0]
    >>> layer = tmxdata.getTileLayerByName("Background")

    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'


Tiles properties are the exception here, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tmxdata.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'


===============================================================================

NOTES:

* The Tiled "properties" have reserved names.

If you use "properties" for any of the following object types, you cannot use
any of these words as a name for your property.  A ValueError will be raised
if there are any conflicts.

As of 0.8.1, these values are:

map:        version, orientation, width, height, tilewidth, tileheight
            properties, tileset, layer, objectgroup

tileset:    firstgid, source, name, tilewidth, tileheight, spacing, margin,
            image, tile, properties

tile:       id, image, properties

layer:      name, x, y, width, height, opacity, properties, data

objectgroup: name, color, x, y, width, height, opacity, object, properties

object:     name, type, x, y, width, height, gid, properties, polygon,
            polyline, image



Please see the TiledMap class for more api information.
"""
from utils import types
from constants import *



def load_tmx(filename, *args, **kwargs):
    # for .14 compatibility
    from pytmx import TiledMap

    tiledmap = TiledMap(filename)
    return tiledmap



def pygame_convert(original, colorkey, force_colorkey, pixelalpha):
    """
    this method does several tests on a surface to determine the optimal
    flags and pixel format for each tile.

    this is done for the best rendering speeds and removes the need to
    convert() the images on your own
    """
    from pygame import Surface, mask, RLEACCEL

    tile_size = original.get_size()

    # count the number of pixels in the tile that are not transparent
    px = mask.from_surface(original).count()

    # there are no transparent pixels in the image
    if px == tile_size[0] * tile_size[1]:
        tile = original.convert()

    # there are transparent pixels, and set to force a colorkey
    elif force_colorkey:
        tile = Surface(tile_size)
        tile.fill(force_colorkey)
        tile.blit(original, (0,0))
        tile.set_colorkey(force_colorkey, RLEACCEL)

    # there are transparent pixels, and tiled set a colorkey
    elif colorkey:
        tile = original.convert()
        tile.set_colorkey(colorkey, RLEACCEL)

    # there are transparent pixels, and set for perpixel alpha
    elif pixelalpha:
        tile = original.convert_alpha()

    # there are transparent pixels, and we won't handle them
    else:
        tile = original.convert()

    return tile


def load_images_pygame(tmxdata, mapping, *args, **kwargs):
    """
    due to the way the tiles are loaded, they will be in the same pixel format
    as the display when it is loaded.  take this into consideration if you
    intend to support different screen pixel formats.

    by default, the images will not have per-pixel alphas.  this can be
    changed by including "pixelalpha=True" in the keywords.  this will result
    in much slower blitting speeds.

    if the tileset's image has colorkey transparency set in Tiled, the loader
    will return images that have their transparency already set.  using a
    tileset with colorkey transparency will greatly increase the speed of
    rendering the map.

    optionally, you can force the loader to strip the alpha channel of the
    tileset image and to fill in the missing areas with a color, then use that
    new color as a colorkey.  the resulting tiles will render much faster, but
    will not preserve the transparency of the tile if it uses partial
    transparency (which you shouldn't be doing anyway, this is SDL).


    TL;DR:
    Don't attempt to convert() or convert_alpha() the individual tiles.  It is
    already done for you.

    """
    from itertools import product
    from pygame import Surface
    import pygame, os


    def handle_transformation(tile, flags):
        if flags:
            fx = flags & TRANS_FLIPX == TRANS_FLIPX
            fy = flags & TRANS_FLIPY == TRANS_FLIPY
            r  = flags & TRANS_ROT == TRANS_ROT

            if r:
                # not sure why the flip is required...but it is.
                newtile = pygame.transform.rotate(tile, 270)
                newtile = pygame.transform.flip(newtile, 1, 0)

                if fx or fy:
                    newtile = pygame.transform.flip(newtile, fx, fy)

            elif fx or fy:
                newtile = pygame.transform.flip(tile, fx, fy)

            # preserve any flags that may have been lost after the transformation
            return newtile.convert(tile)

        else:
            return tile


    pixelalpha     = kwargs.get("pixelalpha", False)
    force_colorkey = kwargs.get("force_colorkey", False)
    force_bitdepth = kwargs.get("depth", False)

    if force_colorkey:
        try:
            force_colorkey = pygame.Color(*force_colorkey)
        except:
            msg = "Cannot understand color: {0}"
            raise Exception, msg.format(force_colorkey)

    tmxdata.images = [0] * tmxdata.maxgid

    for firstgid, t in sorted((t.firstgid, t) for t in tmxdata.tilesets):
        path = os.path.join(os.path.dirname(tmxdata.filename), t.source)

        image = pygame.image.load(path)

        w, h = image.get_size()
        tile_size = (t.tilewidth, t.tileheight)
        real_gid = t.firstgid - 1

        colorkey = None
        if t.trans:
            colorkey = pygame.Color("#{0}".format(t.trans))

        # i dont agree with margins and spacing, but i'll support it anyway
        # such is life.  okay.jpg
        tilewidth = t.tilewidth + t.spacing
        tileheight = t.tileheight + t.spacing

        # some tileset images may be slightly larger than the tile area
        # ie: may include a banner, copyright, ect.  this compensates for that
        width = ((int((w-t.margin*2) + t.spacing) / tilewidth) * tilewidth) - t.spacing
        height = ((int((h-t.margin*2) + t.spacing) / tileheight) * tileheight) - t.spacing

        # using product avoids the overhead of nested loops
        p = product(xrange(t.margin, height+t.margin, tileheight),
                    xrange(t.margin, width+t.margin, tilewidth))

        for (y, x) in p:
            real_gid += 1
            gids = tmxdata.mapGID(real_gid)
            if gids == []: continue

            original = image.subsurface(((x,y), tile_size))

            for gid, flags in gids:
                tile = handle_transformation(original, flags)
                tile = pygame_convert(tile, colorkey, force_colorkey, pixelalpha)
                tmxdata.images[gid] = tile


def load_pygame(filename, *args, **kwargs):
    tmxdata = load_tmx(filename, *args, **kwargs)
    load_images_pygame(tmxdata, None, *args, **kwargs)

    return tmxdata



