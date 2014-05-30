PyTMX
===============================================================================

### Map loader for TMX Files
##### For Python 2.7
##### *Use the python3 branch for python 3.3 support*


If you have any problems or suggestions, please contact me via email.

bitcraft (leif dot theden at gmail.com)

*Released under the LGPL v3*

PyTMX users:  I'm developing a new branch that uses the six module so I won't
have to really worry about porting/backporting features between the python2
and python3 branch.  Now is the time to let me know if there is a feature that
you want added:  open an issue as a feature request.  I estimate the new branch
will be ready in a month or so.

Thanks again to everyone who has been sending me emails and helping to make
PyTMX a great addition to python and pygame!

--leif


News
===============================================================================

##### 05/29/14 - Added support for rotated objects and floating point
##### sometime - Merged six branch into python 3 branch.  Use this for Py3.
##### 04/04/14 - New Six Branch created
##### 02/28/14 - Image layer support, object points changed, new test.py!
##### 02/24/14 - New Python 3 Support: see python3 branch
##### 02/06/14 - Python 3 support coming soon

## 2.16.1
Attention pytmx users!  Starting from 2.16.1,  pytmx has changed the way shape
'points' are stored.  Rather than points being relative to the object's origin,
they are now relative to the map's origin.  This change was made since it is
closer to the way many 3rd party libraries expect object coordinates, and it
makes drawing shapes to the screen more straightforward.

Sorry about any confusion that this change may have caused!



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


Tile and Object Metadata ("Properties")
===============================================================================

Tile properties is access through the map; see the getTileProperties methods

All other objects, including the map, layer, objects, etc. are attributes:     
  ie: map.name  //  layer.weather  // object.power


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

If you are using Python 2.7, you can install PyTMX using pip.

    pip install pytmx (for python 2.7 only!)

You can also manually install it

    python setup.py install


Basic use:
===============================================================================

### Just data:
    >>> import pytmx
    >>> tmx_data = pytmx.TiledMap("map.tmx")


### Load with Pygame Images:

    >>> from pytmx import load_pygame
    >>> tmx_data = load_pygame("map.tmx")


### Alpha Channel Support:

    >>> from pytmx import load_pygame
    >>> tmx_data = load_pygame("map.tmx", pixelalpha=True)

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


### Getting the Tile Surface

    >>> image = tmx_data.getTileImage(x, y, layer)
    >>> screen.blit(image, position)


### Getting Object Metadata ("Properties")

Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tmx_data.tilelayers[0]

or

    >>> layer = tmx_data.getTileLayerByName("Background")

    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'


EXCEPTIONS
===============================================================================
Tile properties are the exception here, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tmx_data.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'


Scrolling Demo
===============================================================================

I have another repo with a working demo of a proper scrolling map using Tiled
maps.  Please feel free to test drive it.  It isn't limited to Tiled maps,
you can use any data structure you want, as long as it is PyGame.    

https://github.com/bitcraft/pyscroll

*PyScroll is Python 3 project, but has a Python 2 branch.


===============================================================================
## IMPORTANT FOR PYGAME USERS!!

The loader will correctly convert() or convert_alpha() each tile image, so you
shouldn't attempt to circumvent the loading mechanisms.  If you are experiencing
problems with images and transparency, pass "pixelalpha=True" while loading.    
Load your map after initializing your display.

===============================================================================

Please see tmxloader.py's docstring for version information and sample usage.
Check tests/test.py and tests/demo.py for examples on how to use the library.

===============================================================================
The 16x16 overworld tiles were created by MrBeast at opengameart.org. CC-BY 3.0
