## PyTMX
##### For Python 2.7 and 3.3+

This is the most up-to-date version of PyTMX available and works with Python 2.7
and 3.3+.

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
tile loading with a fast and efficient storage base.  Not only does it
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

#### Load with pygame images:

```python
from pytmx.util_pygame import load_pygame
tmx_data = load_pygame('map.tmx')
```

The loader will correctly convert() or convert_alpha() each tile image, so you
don't have to worry about that after you load the map.


#### Load with pysdl2 images (experimental):

```python
from pytmx.util_pysdl2 import load_pysdl2
tmx_data = load_pysdl2('map.tmx')
```

#### Load with pyglet images (experimental):

```python
from pytmx.util_pyglet import pyglet_image_loader
tmx_data = load_pygame('map.tmx')
```


TiledMap Objects
===============================================================================

TiledMap objects are returned from the loader.  They contain layers, objects,
and a bunch of useful functions for getting information about the map.

Here is a list of attributes for use.  (ie: TiledMap.layers):

- layers: all layers in order
- tile_properties: dictionary of tile properties {GID: {props...}, ...}
- layernames: dictionary of layers with names: {name: layer, ...}
- images: list of all images in use, indexed by GID.  Index 0 is always None.
- version
- orientation
- width: width of map in tiles, not pixels
- height: height of map in tiles, not pixels
- tileheight: height of tile in pixels.  may differ between layers.
- tilewidth: width of tile in pixels.  may differ between layers.
- background_color: map background color specified in Tiled


#### Optional loading flags

All loaders support the following flags:
- load_all_tiles: if True, all tiles will be loaded, even if unused
- invert_y: used for OpenGL graphics libs.  Screen origin is at lower-left
- allow_duplicate_names: Force load maps with ambigious data (see 'reserved names')

```python
from pytmx.util_pygame import load_pygame
tiled_map = load_pygame(path_to_tmx_file, invert_y=True)
```

#### Loading from XML strings

Most pytmx objects support loading from XML strings.  For some objects, they require
references to other objects (like a layer has references to a tileset) and won't load
from XML.  If you want to store XML in a database or something, you can still load the
entire map with an XML string:

```python
import pytmx
tiled_map = pytmx.TiledMap.from_xml_string(some_string_here)
```

#### Custom Image Loading

The pytmx.TiledMap object constructor now accepts an optional keyword "image_loader".  The argument should be a function that accepts filename, colorkey (false, or a color) and pixelalpha (boolean) arguments.  The function should return another function that will accept a rect-like object and any flags that the image loader might need to know, specific to the graphics library.  Since that concept might be difficult to understand, I'll illustrate with some code.




#### Using TiledMap objects

Please continue reading for basic use.  Advanced functionality can be found by reading
the doc strings for visiting the project documentation at http://pytmx.readthedocs.org


#### A note abput GID's

pytmx does not load unused tiles by default, so the GID you find in Tiled may
differ than the one you find in data loaded with pytmx.  Do not hard code
references to GID's.  They really are for internal use.


Getting Layers, Objects and Tiles
===============================================================================

#### Tiles

To just get a tile for a particular spot, there is a handy method on
TiledMap objects.  TiledMap objects are returned from load_map or load_pygame.
The tile image type will depend on the loader used.  load_pygame returns
pygame surfaces.

```python
pygame_surface = tmx_data.get_tile_image(x, y, layer)
```

#### Objects

Objects can be accessed through the TiledMap or through a group.
Object groups can be used just like a python list.

```python
object = tiled_map.objects[0]
all_objects = tiled_map.get_object_by_name("baddy001")  # will not return duplicates
group = tiled_map.get_layer_by_name("traps")
traps = group[:]
```

#### Getting Layers and Groups

Layers are accessed through the TiledMap class and there are a few ways to
get references to them:

```python
layer = tiled_map.layers[0]
layer = tiled_map.get_layer_by_name("base layer")
layers = tiled_map.visible_tile_layers
layers = tile_map.visible_object_groups
layer_dict = tiled_map.layernames
```

#### Working with layer data and images

Layer tiles are stored as a 'list of lists', or '2d array'.  Each element of
layer data is a number which refers to a specific image in the map.  These
numbers are called GID.  Do not make references to these numbers, as they
will change if the map changes.

With pygame, images will be plain pygame surfaces.  These surfaces will be
checked for colorkey or per-pixel alpha automatically using information from
the TMX file and from checking each image for transparent pixels.  You
do not need, and should not convert the tiles, because it is already done. 

The following methods work for pygame, pysdl2, pyglet and maps without loaded
images.  If you do not load images, then the image will be an object describing
the image.

#### Least effort involved getting tile images.  Do this if you plan to render with pytmx objects.

```python
layer = tiled_map.layers[0]
for x, y, image in layer.tiles():
    ...
```


Working with Objects
===============================================================================

Pytmx loads all objects and their data:
- name
- type
- x
- y
- width
- height
- rotation
- gid (if it has an image)
- visible
- image
- properties

#### Basics
Attributes x, y, width, and height all represent the bounding box of the object,
even polygons and polylines.  You can access object properties by the
'properties' attribute.

#### Image Objects
If using a loader, then TiledObject.image will be a reference to the image used.

#### Polygon/Polyline Objects
These objects have special atributes: 'closed' and 'points'.  Each point is (x, y) tuple.
If the object is a polygon, then TiledObject.closed will be True.  Points are not
rotated if the rotation property is used.



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
maps, you can use any data structure you want, as long as pygame is used.

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
"color".  Overall, this check will help enforce clean design. 
 
However, If you really don't care about name conflicts, there is an option
you can try at your own risk.  Pass 'allow_duplicate_names=True' to any
loader or to the TiledMap constructor and the checks will be disabled.

```python
from pytmx.util_pygame import load_pygame
tmx_data = load_pygame('map.tmx', allow_duplicate_names=True)
```

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
