## PyTMX
##### For Python 2.7 and 3.3+

This is the most up-to-date version of PyTMX available and works with Python 2.7
and 3.3+ with no changes to the source code.  Please use this branch for all new
PyTMX projects.

If you have any problems or suggestions, please open an issue.
I am also often lurking #pygame on freenode.  Feel free to contact me.

Requires the six module.

*Released under the LGPL v3*

#### See the "apps" folder for example use.  


News
===============================================================================

__04/18/15__ - Document support for pysdl2 and pyglet  
__09/14/14__ - Merge python3 branch.  Now 100% compatible with 2.7 and 3.3+  
__07/26/14__ - New python3/2 release.  Check it out in the python3 branch.  
__05/29/14__ - Added support for rotated objects and floating point  
__04/04/14__ - New Six Branch created  
__02/28/14__ - Image layer support, object points changed, new test.py!  
__02/24/14__ - New Python 3 Support: see python3 branch  
__02/06/14__ - Python 3 support coming soon  


Introduction
===============================================================================

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


Documentation
===============================================================================

This readme does not include much detailed documentation.  Full API reference
and documentation can be found at the site below.  For examples of real use,
check out the apps folder in this repo.  The 'test' apps demonstrate how to
load maps, get layer, tile, and object data, as well as some rendering.

http://pytmx.readthedocs.org/


Getting Help
===============================================================================

For bugs or feature requests, please use the issues feature of github.  For
all other general questions, join me on IRC at freennode.net #pygame.


Design Goals and Features
===============================================================================

* API with many handy functions
* Memory efficient and performant
* Loads data, "properties" metadata, and images from Tiled's TMX format
* Supports base64, csv, gzip, zlib and uncompressed XML formats
* Properties for all native Tiled object types
* Point data for polygon and polyline objects
* Automatic flipping and rotation of tiles
* Built-in image loading with pygame, pysdl2, and pyglet


Why use PyTMX?
===============================================================================

### PyTMX is efficient:
* Only the tiles used on a map are loaded into memory
* Map information is stored as integers, not python objects (32+kb)
* Extensive use of generators and iterators make it easy on memory
* Code is designed for compact size and readability

### PyTMX is flexible:
* Supports all major Tiled features and object types
* PyTMX data classes can be extended
* Does not force you to render data in any particular way
* Includes many checks to give useful debugging information
* Supports pygame, pyglet, and pysdl2 image loading

### PyTMX is supported:
* GitHub hosting allows for community participation
* I have kept PyTMX current with new versions of Tiled since v.7

### PyTMX is usable:
* Liberal LGPL license means you can use PyTMX for your project


Installation
===============================================================================

Install from pip

    pip install pytmx


You can also manually install it

    python setup.py install


Basic use:
===============================================================================

#### Just data, no images:
```python
import pytmx
tmx_data = pytmx.TiledMap('map.tmx')
```

#### Load with Pygame Images:

```python
from pytmx.util_pygame import load_pygame
tmx_data = load_pygame('map.tmx')
```

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


#### Load with pysdl2 Images (experimental):

```python
from pytmx.util_pysdl2 import load_pysdl2
tmx_data = load_pysdl2('map.tmx')
```

#### Load with pyglet Images (experimental):

```python
from pytmx.util_pyglet import pyglet_image_loader
tmx_data = load_pygame('map.tmx')
```


#### Getting the Tile Image

```python
image = tmx_data.get_tile_image(x, y, layer)
```


Tile, Object, and Map Properties
===============================================================================

Properties are a powerful feature of Tiled that allows the level designer to
assign key/value data to individual maps, tilesets, tiles, and objects.  Pytmx
includes full support for reading this data so you can set parameters for stuff
in Tiled, instead of maintaining external data files, or even values in source.

Individual tile properties are accessed through the the parent map object:

```
tmxdata = TiledMap('level1.tmx')
props = txmdata.get_tile_properties(x, y, layer)
props = tmxdata.get_tile_properties_by_gid(tile_gid)
```

All other objects, including the map, layer, objects, etc. are in an
object attribute (type: dict) called "properties":

```python
# this is the map object
tmx_data = TiledMap('level1.tmx')

# so, here are the properties of the map
tmx_data.properties['name']

# and the properties of each layer
for layer in tmxdata.visible_layers:
    layer.properties['movement_speed']
    
# here are properties of each object
for obj in layer.objects():
    obj.properties['attack_strength']
```


Scrolling Maps for Pygame
===============================================================================

I have another repo with a working demo of a proper scrolling map using Tiled
maps and pygame.  Please feel free to test drive it.  It isn't limited to Tiled
maps, you can use any data structure you want, as long as PyGame is used.

https://github.com/bitcraft/pyscroll


Reserved Names
================================================================================

Tiled supports user created metadata called "properties" for all the built-in
objects, like the map, tileset, objects, etc.  Due to how the Tiled XML data is
stored, there are situations where Tiled internal metadata might have the same
name as user-created properties.

Pytmx will raise a ValueError if it detects any conflicts.  This check is
performed in order to prevent any situations where a level change might be made
in Tiled, but the programmer/designer doesn't know or forgets if the change was
made in the Tiled metadata or the user properties.

I realize that it creates problems with certain common names like "id", or
"color".  Overall, it should help with clean design.  In the future, I may
make an option for removing this check, as long as the programmer understands
the risk.

In summary, don't use the following names when creating properties in Tiled:

As of 0.11.0, these values are:

map:         version, orientation, width, height, tilewidth, tileheight  
             properties, tileset, layer, objectgroup

tileset:     firstgid, source, name, tilewidth, tileheight, spacing, margin,  
             image, tile, properties  

tile:        id, image, properties  

layer:       name, x, y, width, height, opacity, properties, data  

objectgroup: name, color, x, y, width, height, opacity, object, properties  

object:      name, type, x, y, width, height, gid, properties, polygon,  
             polyline, image, id


Running the Tests
===============================================================================

Install the nose package with pip then from the root of the project run:

        nosetests


Artwork Attributions
===============================================================================
The 16x16 overworld tiles were created by MrBeast at opengameart.org. CC-BY 3.0

* If I missed your attribution, please let me know.
