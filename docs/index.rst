PyTMX
=====

PyTMX is a map loader for python/pygame designed for games.  It provides smart
tile loading with a fast and efficient storage base.  Not only will does it
correctly handle most Tiled object types, it also will load metadata for
them, so you can modify your maps and objects in Tiled, instead of modifying
your source code.

PyTMX strives to balance performance and flexibility.  Feel free to use the
classes provided in pytmx.py as superclasses for your own maps, or simply
load the data with PyTMX and copy the data into your own classes with the api.


Design Goals and Features
=========================

* API with many handy functions
* Memory efficient and performant
* Loads data, "properties" metadata, and images from Tiled's TMX format
* Supports base64, csv, gzip, zlib and uncompressed XML
* Properties for all native Tiled object types
* Point data for polygon and polyline objects
* Automatic flipping and rotation of tiles
* Image loading with pygame (will work without images as well)


Getting Help
============

For bugs or feature requests, please use the issues feature of github.  For
all other general questions, join me on IRC at freennode.net #pygame.


Installation
============

Install from pip

    pip install pytmx


You can also manually install it

    python setup.py install


Basic use
=========

From a file:

    >>> import pytmx
    >>> tmxdata = pytmx.TiledMap("map.tmx")


From a XML string:

    >>> import pytmx
    >>> tmxdata = pytmx.TiledMap.fromstring(xml_string)


Load with PyGame surfaces:

    >>> from test_pytmx import load_pygame
    >>> tmxdata = load_pygame("map.tmx")


Getting the tile surface:

    >>> image = tmx_data.get_tile_image(x, y, layer)
    >>> screen.blit(image, position)


Tile, Object, and Map Properties
================================

Properties are any key/value data added to an object/map/layer in Tiled
through the properties dialog.  Tile properties are accessed through the the
parent map object:

    >>> tmxdata = TiledMap('level1.tmx')
    >>> props = txmdata.get_tile_properties(x, y, layer)
    >>> props = tmxdata.get_tile_properties_by_gid(tile_gid)

All other objects, including the map, layer, objects, etc. are in an
python dictionary attribute called "properties":

    >>> tmxdata = TiledMap('level1.tmx')
    >>> tmxdata.properties['name']
    >>> for layer in tmxdata.visible_layers:
    >>>     layer.properties['movement_speed']


Scrolling Demo
==============

Scrolling and Tiled maps go together, so I've created a library to make PyGame
projects easy to use PyTMX maps and have a great scrolling map.

pyscroll can use PyTMX maps to create an easy to use replacement for PyGame
SpriteGroups.  Just use the PyScroll group and you can use fast, multilayered,
scrolling maps.

https://github.com/bitcraft/pyscroll


Import Notice for PyGame Users
==============================

The loader will correctly convert() or convert_alpha() each tile image, so you
shouldn't attempt to circumvent the loading mechanisms.


API Documentation
=================

.. toctree::
   :maxdepth: 4

   pytmx


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

