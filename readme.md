## PyTMX
##### For Python 2.7 and 3.3+

This is the most up-to-date version of PyTMX available and works with Python 2.7 and 3.3
with no changes to the source code.  Please use this branch for all new PyTMX projects.

If you have any problems or suggestions, please open an issue.
I am also often lurking #pygame on freenode.  Feel free to contact me.

*Released under the LGPL v3*

#### See the "apps" folder for example use.


===============================================================================
## Key Differences from 2.x versions

I've tweaked many small things for a cleaner, more 'pythonic' library.

- Better pep8 compliance
- More use of iterators
- More functions to find layers

Take a look at the wiki for more info on changes
https://github.com/bitcraft/PyTMX/wiki/Migration-to-the-Python-3-branch


Please see tmxloader.py's docstring for version information.


News
===============================================================================

##### 07/26/14 - New python3/2 release.  Check it out in the python3 branch.
##### 05/29/14 - Added support for rotated objects and floating point
##### sometime - Merged six branch into python 3 branch.  Use this for Py3.
##### 04/04/14 - New Six Branch created
##### 02/28/14 - Image layer support, object points changed, new test.py!
##### 02/24/14 - New Python 3 Support: see python3 branch
##### 02/06/14 - Python 3 support coming soon


Introduction
===============================================================================

PyTMX is a map loader for python/pygame designed for games.  It provides smart
tile loading with a fast and efficient storage base.  Not only will does it
correctly handle most Tiled object types, it also will load metadata for
them, so you can modify your maps and objects in Tiled, instead of modifying
your source code.

Because PyTMX was built with games in mind, it differs slightly from Tiled in
a few minor aspects:

- Layers not aligned to the grid are not supported.
- Some object metadata attribute names are not supported (see docstrings)


PyTMX strives to balance performance and flexibility.  Feel free to use the
classes provided in pytmx.py as superclasses for your own maps, or simply
load the data with PyTMX and copy the data into your own classes with the api.

I've included a test suite in the 'tests' folder.  It should work across all
platforms.  test.py demonstrates loading a variety of maps and formats.

Finally, there is no save feature.  Once the map is loaded, it will be up to
you to provide a way to save changes to the map.  I've used the pickle module
with good results.


Documentation
=============

http://pytmx.readthedocs.org/


Design Goals and Features
===============================================================================

* API with many handy functions
* Memory efficient and performant
* Loads data, "properties" metadata, and images from Tiled's TMX format
* Supports base64, csv, gzip, zlib and uncompressed XML
* Properties for all native Tiled object types
* Point data for polygon and polyline objects
* Automatic flipping and rotation of tiles
* Image loading with pygame (will work without images as well)


Why use PyTMX?
===============================================================================

### PyTMX is efficient:
* Only the tiles used on a map are loaded into memory
* Map information is stored as integers (8-16 bit), not python objects (32+kb)
* Extensive use of generators and iterators make it easy on memory
* Code is designed for compact size and readability

### PyTMX is flexible:
* Supports all major Tiled features and object types
* Built-in pygame image loading
* PyTMX data classes can be extended
* Does not force you to render data in any particular way
* Includes many checks to give useful debugging information

### PyTMX is supported:
* GitHub hosting allows for community participation
* I have kept PyTMX current with new versions of Tiled since v.7

### PyTMX is usable:
* Liberal LGPL license means you can use PyTMX for your project


Installation
===============================================================================

You msut manually install it

    python setup.py install


Basic use:
===============================================================================

#### Just data:
    >>> import pytmx
    >>> tmxdata = pytmx.TiledMap("map.tmx")


#### Load with Pygame Images:

    >>> from pytmx import load_pygame
    >>> tmxdata = load_pygame("map.tmx")

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


#### Getting the Tile Surface

    >>> image = tmx_data.get_tile_image(x, y, layer)
    >>> screen.blit(image, position)


Tile and Object Metadata ("Properties")
===============================================================================

Properties are any key/value data added to an object/map/layer in Tiled
through the properties dialog.  Tile properties are accessed through the the
parent map object:

    tmxdata = TiledMap('level1.tmx')
    props = txmdata.get_tile_properties(x, y, layer)
    props = tmxdata.get_tile_properties_by_gid(tile_gid)

All other objects, including the map, layer, objects, etc. are in an
dict attribute called "properties":

    tmxdata = TiledMap('level1.tmx')
    tmxdata.properties['name']
    for layer in tmxdata.visible_layers:
        layer.properties['movement_speed']



Scrolling Demo
===============================================================================

I have another repo with a working demo of a proper scrolling map using Tiled
maps.  Please feel free to test drive it.  It isn't limited to Tiled maps,
you can use any data structure you want, as long as PyGame is used.

https://github.com/bitcraft/pyscroll

*PyScroll is Python 3 project, but has a Python 2 branch.


===============================================================================
## IMPORTANT FOR PYGAME USERS!!

The loader will correctly convert() or convert_alpha() each tile image, so you
shouldn't attempt to circumvent the loading mechanisms.

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

***   Please see the TiledMap class source for more api information.   ***


Version Numbering
================================================================================

X.Y.Z

X: 2 for python 2, 3 for python 3 and 2
Y: major release. for new features or api change
Z: minor release.  for bug fixes related to last release

===============================================================================
The 16x16 overworld tiles were created by MrBeast at opengameart.org. CC-BY 3.0
