"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v2.16.1 - for python 2.6 and 2.7

Tested with Tiled 0.9.1 for Mac.

released under the LGPL v3

===============================================================================

New in 2.16.1:
      core: renamed mapGID => map_gid  //  registerGID => register_gid (pep8)
      core: 'visible' added to list of illegal object properties
    loader: removed legacy load_tmx function: just call TiledMap() instead
    loader: added test to correct tilesheets that include non-tile graphics
     pytmx: objects with 'points' (polyline, etc) now return world coords.
     pytmx: added getTileByGID method for TiledMap
     pytmx: attempting to reach a tile outside the map raises ValueError
     pytmx: support Tiled Image Layers
     pytmx: added iterator protocol for Tile Layers
      test: correctly displays objects and image layers
      test: reorganized the directory structure
      test: renders whole map, window is resizable
      test: correctly displays map's background color
   general: new version number to reflect supported python version
   general: python 3 support in new library (see python3 branch)

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

===============================================================================

## Installation:

    python.py setup.py install

    or

    pip install pytmx (for python 2 only!)

## Basic usage sample:

    >>> from pytmx import load_pygame
    >>> tmxdata = load_pygame("map.tmx")


## Alpha Channel Support:

    >>> tmxdata = load_pygame("map.tmx", pixelalpha=True)

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


## Getting the Tile Surface

    >>> image = tmxdata.getTileImage(x, y, layer)
    >>> screen.blit(image, position)


## Getting Object Metadata ("Properties")

Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tmxdata.tilelayers[0]
    >>> layer = tmxdata.getTileLayerByName("Background")

    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'


## EXCEPTIONS

Tile properties are the exception here, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tmxdata.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'


===================================================================================
IMPORTANT FOR PYGAME USERS!!
The loader will correctly convert() or convert_alpha() each tile image, so you
shouldn't attempt to circumvent the loading mechanisms.  If you are experiencing
problems with images and transparency, pass "pixelalpha=True" while loading.

ALSO FOR PYGAME USERS:  Load your map after initializing your display.
===================================================================================

NOTES:

* The Tiled "properties" have reserved names.

If you use "properties" for any of the following object types, you cannot use
any of these words as a name for your property.  A ValueError will be raised
if a Tile Object attempts to use a reserved name.

In summary: don't use the following names when adding metadata in Tiled.

As of 0.8.1, these values are:

map:         visible,  version, orientation, width, height, tilewidth, tileheight
             properties, tileset, layer, objectgroup

tileset:     visible, firstgid, source, name, tilewidth, tileheight, spacing, margin,
             image, tile, properties

tile:        id, image, properties

layer:       visible, name, x, y, width, height, opacity, properties, data

objectgroup: visible, name, color, x, y, width, height, opacity, object, properties

object:      visible, name, type, x, y, width, height, gid, properties, polygon,
             polyline, image

***   Please see the TiledMap class for more api information.   ***
"""