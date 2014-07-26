"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v3.17 - for python 3.3

If you have any problems or suggestions, please contact me via email.
Tested with Tiled 0.8.1 for Mac.

released under the LGPL v3

===============================================================================

New in 3.19:
      core: new iterator for tiledmap
      core: objects/shapes load the rotation value
      core: polygon/polyline and all other shapes return coordinates as float
      core: pytmx respects tiles that specify external image: stored in metadata
      core: tileoffsets are loaded stored in tileset.offset: tuple: (x, y)
    pygame: tilesets can be loaded even if they don't specify an image
    pygame: loading of tiles that specify an external image is supported
    pygame: new optional arguments for load_pygame():
            load_all: bool (False is default), load al tiles, even unused ones
            optional_gids: list/tuple, also load the gids in this list
            === 'gid' refers to the gid found in tiled

New in 3.18:
    pygame: removed option for force a colorkey for a tileset
    pygame: pixelalpha is now enabled by default
     pytmx: Maps can now be loaded from pytmx.TiledMap.fromstring(xml_string)
     pytmx: pygame is no longer a required dependency (to be tested!)
      core: Sphinx documentation created

New in 3.17:
    loader: removed legacy load_tmx function: just call TiledMap() instead
    loader: added test to correct tilesheets that include non-tile graphics
     pytmx: polygon objects now return absolute coordinates in points
     pytmx: tiled properties are now available through dictionary "properties"
      core: tested with the mana world maps...it works!
      demo: simplified the demo/test for easier readability
      test: maps now render and are scaled inside the window to show entire map


New in 3.16:
    ***    jumped to version 3.x to reflect new python 3.3 compatibility    ***

       all: python 3 support
      pep8: changed method/function names to lowercase with underscore spacing
      pep8: modified various style infractions
      core: simplified file structure
      core: added __all__ to some modules for less clutter
      demo: added ability to resize preview window
      test: mouse clicks now advance the test
      test: added ability to resize preview window
      test: tile objects are drawn (previously supported, but not shown in test)
     utils: renamed buildDistributionRects to build_rects
     pytmx: bumped up gid limit from 255 to 65535 (16-bit)
     pytmx: removed get_objects(), replaces with objects property
     pytmx: removed get_draw_order(), replaced with visible_layers property
    loader: added ImageLayer support
    loader: minor documentation fixes
    loader: small optimizations
    loader: possible [ultra minor] optimization: using iterator on etree to load

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


Includes a scrolling/zooming renderer.  They are for demonstration purposes,
and may not be suitable for all projects.  Use at your own risk.

===============================================================================

Installation:

    There is no install script.  To use PyTMX in your projects, just copy
    the folder into your project directory and follow the guide below.


Basic usage sample:

    >>> from pytmx import tmxloader
    >>> tmxdata = tmxloader.load_pygame("map.tmx")
    >>> tmxdata = tmxloader.load_pygame("map.tmx", pixelalpha=False)


When you want to draw tiles, you simply call "getTileImage":

    >>> image = tmxdata.get_tile_image(x, y, layer)
    >>> screen.blit(image, position)

Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tmxdata.tilelayers[0]
    >>> layer = tmxdata.get_layer_by_name("Background")

    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'

Tiles properties are the exception here*, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tmxdata.get_tile_properties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'

* this is compromise in the API delivers great memory saving

================================================================================
IMPORTANT FOR PYGAME USERS!!
The loader will correctly convert() or convert_alpha() each tile image, so you
shouldn't attempt to circumvent the loading mechanisms.  If you are experiencing
performance issues, you can pass "pixelalpha=False" while loading.

ALSO FOR PYGAME USERS:  Load your map after initializing your display.
================================================================================

NOTES:

* The Tiled "properties" have reserved names.

If you use "properties" for any of the following object types, you cannot use
any of these words as a name for your property.  A ValueError will be raised
if a Tile Object attempts to use a reserved name.

In summary: don't use the following names when adding metadata in Tiled.

As of 0.8.1, these values are:

map:         version, orientation, width, height, tilewidth, tileheight
             properties, tileset, layer, objectgroup

tileset:     firstgid, source, name, tilewidth, tileheight, spacing, margin,
             image, tile, properties

tile:        id, image, properties

layer:       name, x, y, width, height, opacity, properties, data

objectgroup: name, color, x, y, width, height, opacity, object, properties

object:      name, type, x, y, width, height, gid, properties, polygon,
             polyline, image

***   Please see the TiledMap class for more api information.   ***

================================================================================

Version Numbering:

X.Y.Z

X: 2 for python 2, 3 for python 3 and 2
Y: major release. for new features or api change
Z: minor release.  for bug fixes related to last release
"""
import itertools
import os
import pygame
import pytmx
from pygame.transform import flip, rotate
from .constants import *

__all__ = ['load_pygame']


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

    # change background color into something nice
    if tmxdata.background_color:
        tmxdata.background_color = pygame.Color(tmxdata.background_color)

    # initialize the array of images
    tmxdata.images = [0] * tmxdata.maxgid

    # load tileset image
    for ts in tmxdata.tilesets:
        # skip the tileset if it doesn't include a source image
        if ts.source is None:
            continue

        path = os.path.join(os.path.dirname(tmxdata.filename), ts.source)
        image = pygame.image.load(path)
        w, h = image.get_size()

        # margins and spacing
        tilewidth = ts.tilewidth + ts.spacing
        tileheight = ts.tileheight + ts.spacing
        tile_size = ts.tilewidth, ts.tileheight

        # some tileset images may be slightly larger than the tile area
        # ie: may include a banner, copyright, ect.  this compensates for that
        width = int((((w - ts.margin * 2 + ts.spacing) / tilewidth) * tilewidth) - ts.spacing)
        height = int((((h - ts.margin * 2 + ts.spacing) / tileheight) * tileheight) - ts.spacing)

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

            # map_gid returns a list of internal pytmx gids to load
            gids = tmxdata.map_gid(real_gid)

            # user may specify to load all gids, or to load a specific one
            if gids is None:
                if load_all_tiles or real_gid in optional_gids:
                    # TODO: handle flags? - might never be an issue, though
                    gids = [tmxdata.register_gid(real_gid, flags=0)]

            if gids:
                original = image.subsurface(((x, y), tile_size))

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

