Introduction
============

PyTMX is a map loader for python/pygame designed for games.  It provides smart
tile loading with a fast and efficient storage base.  Not only will does it
correctly handle most Tiled object types, it also will load metadata for
them, so you can modify your maps and objects in Tiled, instead of modifying
your source code.

New support for pysdl2 and pyglet!  Check it out!

Because PyTMX was built with games in mind, it differs slightly from Tiled in
a few minor aspects:

- Layers not aligned to the grid are not supported.
- Some object metadata attribute names are not supported (see "Reserved Names")

PyTMX strives to balance performance and flexibility.  Feel free to use the
classes provided in pytmx.py as superclasses for your own maps, or simply
load the data with PyTMX and copy the data into your own classes with the api.

Finally, there is no save feature.  Once the map is loaded, it will be up to
you to provide a way to save changes to the map.  I've used the pickle module
with good results.


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


Load with pygame surfaces:

    >>> from pytmx.util_pygame import load_pygame
    >>> tmxdata = load_pygame("map.tmx")


Load with pysdl2 images (experimental):

    >>> from pytmx.util_pysdl2 import load_pysdl2
    >>> tmx_data = load_pysdl2('map.tmx')


Load with pyglet images (experimental):

    >>> from pytmx.util_pyglet import pyglet_image_loader
    >>> tmx_data = load_pygame('map.tmx')

Getting the tile image:

    >>> image = tmx_data.get_tile_image(x, y, layer)
    >>> screen.blit(image, position)


Tile, Object, and Map Properties
================================

Properties are a powerful feature of Tiled that allows the level designer to
assign key/value data to individual maps, tilesets, tiles, and objects.  Pytmx
includes full support for reading this data so you can set parameters for stuff
in Tiled, instead of maintaining external data files, or even values in source.

Individual tile properties are accessed through the the parent map object:

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

I have another repo with a working demo of a proper scrolling map using Tiled
maps and pygame.  Please feel free to test drive it.  It isn't limited to Tiled
maps, you can use any data structure you want, as long as PyGame is used.

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

