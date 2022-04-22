<div align="center">

# pytmx

A map loader for Python/pygame, designed for video games

![pypi version](https://img.shields.io/pypi/v/pytmx)
![license](https://img.shields.io/github/license/bitcraft/pytmx)
![code style](https://img.shields.io/badge/code%20style-black-000000.svg)
![pypi downloads](https://img.shields.io/pypi/dm/pytmx)

</div>

About
===============================================================================
**For Python 3.7+**
A map loader for python/pygame designed for games. It provides smart
tile loading with a fast and efficient storage base. Not only does it
correctly handle most Tiled object types, it also will load metadata for
them so you can modify your maps and objects in Tiled instead of modifying
your source code. See the "apps" folder for example use and cut/paste code.

Since pytmx was built with games in mind, it differs slightly from Tiled in
a few minor aspects:
 - Layers not aligned to the grid are not supported.
 - Some object metadata attribute names are not supported (see "Reserved Names").
 - pytmx is not a rendering engine or Tiled Map Editor.

pytmx strives to balance performance and flexibility. Feel free to use the
classes provided in pytmx.py as superclasses for your own maps, or simply
load the data with pytmx and copy the data into your own classes with the API.

**There is no save feature.** Once the map is loaded, it will be up to
you to provide a way to save changes to the map. I've used the pickle module
with good results.

**As Python 2.7 is now EOL**, any changes moving forward past version 3.21.7 will
not take python 2.7 support into consideration and any breaking changes will not be 
fixed.

If you have any problems or suggestions, please open an issue or join the Discord server.
https://discord.gg/2taTP4aYR6

If you find this useful, please consider making a donation to help support it.
https://liberapay.com/ltheden/donate

*Released under the LGPL V3*

News
===============================================================================

| Date     | Changes
| -------- | --------
| 09/21/21 | Supports pygame._sdl2.
| 09/08/21 | Much faster loading, especially for large maps.
| 12/04/20 | Support tile colliders.
| 08/28/20 | Python 2.7 support removed. Use the "py27-legacy" branch.
| 11/13/15 | Animations are now loaded.
| 07/08/15 | Documentation overhaul.
| 04/18/15 | Document support for pysdl2 and pyglet.
| 09/14/14 | Merge python3 branch. Now 100% compatible with 2.7 and 3.3+.
| 07/26/14 | New python3/2 release. Check it out in the python3 branch.
| 05/29/14 | Added support for rotated objects and floating point.
| 04/04/14 | New Six Branch created.
| 02/28/14 | Image layer support, object points changed, new test.py!
| 02/24/14 | New Python 3 Support: see python3 branch.
| 02/06/14 | Python 3 support coming soon.


Documentation
===============================================================================

This readme does include some detailed documentation, but the full API reference
and documentation can be found at the site below.  For examples of real use,
check out the apps folder in this repo.  The 'test' apps demonstrate how to
load maps, get layer, tile, and object data, as well as some rendering.

http://pytmx.readthedocs.org/


# Table of Contents
1. [Installation](#installation)
2. [Basic Use](#basic-use)
3. [Getting Properties](#object-properties)
4. [Working with Maps](#working-with-maps)
5. [Loading from XML](#loading-from-xml)
6. [Custom Image Loading](#custom-image-loading)
7. [Working with Tile Layers](#working-with-tile-layers)
8. [Getting Tile Animations](#getting-tile-animations)
9. [Working with Objects](#working-with-objects)
10. [Understanding Properties](#understanding-properties)


Design Goals and Features
===============================================================================

* API with many handy functions
* Memory efficient and performant
* Loads data, "properties" metadata, and images from Tiled's TMX format
* Supports base64, csv, gzip, zlib and uncompressed XML formats
* Properties for all native Tiled object types
* Point data for polygon and polyline objects
* Automatic flipping and rotation of tiles
* Tile collider groups
* Built-in image loading with pygame, pysdl2, and pyglet
* Loads animation information


Why use pytmx?
===============================================================================

### pytmx is efficient:
* Map information is stored as integers, not python objects (32+kb)
* Extensive use of generators and iterators make it easy on memory
* Code is designed for compact size and readability

### pytmx is flexible:
* Supports all major Tiled features and object types
* pytmx data classes can be extended
* Does not force you to render data in any particular way
* Includes many checks to give useful debugging information
* Supports pygame, pyglet, and pysdl2 image loading

### pytmx is supported:
* GitHub hosting allows for community participation
* I have kept pytmx current with new versions of Tiled since v.7


Installation
===============================================================================

Install from pip

    pip install pytmx


Manually install it

    python setup.py install


You can also copy/paste the pytmx folder into your project


Basic use:
===============================================================================

#### Just data, no images:

```python
import pytmx
tiled_map = pytmx.TiledMap('map.tmx')
```

#### Load with pygame images:

```python
from pytmx.util_pygame import load_pygame
tiled_map = load_pygame('map.tmx')
```

#### Load with pyglet images (experimental):

```python
from pytmx.util_pyglet import load_pyglet
tiled_map = load_pyglet('map.tmx')
```

#### Load from XML string:

```python
import pytmx
tiled_map = pytmx.TiledMap.from_xml_string(some_string_here)
```

#### Iterate through layers and object groups:

```python
for layer in tiled_map.layers:
   ...
```

#### Iterate through tile images in a tile layer:

```python
for x, y, image in layer.tiles():
   ...
```

#### Iterate through Tiled objects in an object group:

```python
for obj in layer:
   ...
```

#### Get properties of various object types:

```python

# properties is a dict 
TiledMap.properties
TiledTileLayer.properties['name']
TiledObject.properties['type']

# tile ('GID') properties are accessed through the TiledMap:
properties = TiledMap.get_tile_properties(x, y, layer)
```

#### Get bounding box of an object:

```python
bbox = obj.x, obj.y, obj.width, obj.height
```

#### Get the points/vertex to draw a polygon/polyline object:

```python
points = obj.points
# if obj.closed == True, then obj is a polygon
```

#### Get the transformed points (after rotation) of object:

This works for box shaped objects, as well as polygon/line
```python
points = obj.apply_transformations()
```

#### Get tile colliders:

Tile colliders are a objectgroup, with each shape being a TiledObject
```python
# iterate over all of them
for gid, colliders in tiled_map.get_tile_colliders():
   pass

# get colliders for a specific gid
properties = TiledMap.get_tile_properties(x, y, layer) 
colliders = properties["colliders"]
```


Working with Maps
===============================================================================

TiledMap objects are returned from the loader.  They contain layers, objects,
and a bunch of useful functions for getting information about the map.  In
general, all of the pytmx types are not meant to be modified after being
returned from the loader.  While there is a potential for modifying them,
its not a supported function, and may change any time.  Please consider them
read-only.

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
- properties: all user created properties about the map


#### Optional loading flags

All loaders support the following flags:
- load_all_tiles: if True, all tiles will be loaded, even if unused
- invert_y: used for OpenGL graphics libs.  Screen origin is at lower-left
- allow_duplicate_names: Force load maps with ambiguous data (see 'reserved names')

```python
from pytmx.util_pygame import load_pygame
tiled_map = load_pygame(path_to_tmx_file, invert_y=True)
```

#### Loading from XML

Most pytmx objects support loading from XML strings.  For some objects, they require
references to other objects (like a layer has references to a tileset) and won't load
directly from XML.  They can only be loaded if the entire map is loaded first.  If you
want to store XML in a database or something, you can load the entire map with an XML string:

```python
import pytmx
tiled_map = pytmx.TiledMap.from_xml_string(some_string_here)
```

#### Custom Image Loading

The pytmx.TiledMap object constructor accepts an optional keyword "image_loader".  The argument should be a function that accepts filename, colorkey (false, or a color) and pixelalpha (boolean) arguments.  The function should return another function that will accept a rect-like object and any flags that the image loader might need to know, specific to the graphics library.  Since that concept might be difficult to understand, I'll illustrate with some code.  Use the following template code to load images from another graphics library.

 ```python
import pytmx

def other_library_loader(filename, colorkey, **kwargs):

    # filename is a file to load an image from
    # here you should load the image in whatever lib you want

    def extract_image(rect, flags):
    
        # rect is a (x, y, width, height) area where a particular tile is located
        # flags is a named tuple that indicates how tile is flipped or rotated
    
        # use the rect to specify a region of the image file loaded in the function
        # that encloses this one.
        
        # return an object to represent the tile
        
        # what is returned here will populate TiledMap.images, be returned by
        # TiledObject.Image and included in TiledTileLayer.tiles()

    return extract_image

level_map_and_images = pytmx.TiledMap("leveldata.tmx", image_loader=other_library_loader)
```

#### Accessing layers

Layers are accessed through the TiledMap class and there are a few ways to get references to them:

```python
# get a layer by name
layer_or_group = tiled_map.get_layer_by_name("base layer")

# TiledMap.layers is a list of layers and object groups
layer = tiled_map.layers[layer_index_number]

# easily get references to just the visible tile layers
for layer in tiled_map.visible_tile_layers:
    ...

# just get references to visible object groups
for group in tile_map.visible_object_groups:
    ...
```


Working with Tile Layers
===============================================================================

pytmx loads tile layers and their data:

- name
- opacity
- visible: indicates if user has hidden the layer
- data: 2d array of all tile gids (normally not needed to use!)
- properties

#### Tile Images

Single tile images are accessible from TiledMap, TiledTileLayer, and TiledObject objects.
If you requre all images in a layer, there are more efficient ways described below.

```python
# get image from the TiledMap using x, y, and layer numbers
pygame_surface = tile_map.get_tile_image(x, y, layer)

# get tile image from an object with a image/GID assigned to it
image = obj.image

# get image using gid (not needed for normal use!)
gid = layer.data[y][x]
image = tiled_map.images[gid]
```

#### Least effort involved getting all tile images

```python
for x, y, image in layer.tiles():
    ...
```

#### Getting tile animations

Tiled supports animated tiles, and pytmx has the ability to load them.
Animations are stored in the properties for the tile.  Animations from
pytmx are a list of AnimationFrame namedtuples.  Please see the example below.

```python
# just iterate over animated tiles and demo them

# tmx_map is a TiledMap object
# tile_properties is a dictionary of all tile properties

# iterate over the tile properties
for gid, props in tmx_map.tile_properties.items():

   # iterate over the frames of the animation
   # if there is no animation, this list will be empty
   for animation_frame in props['frames']:
   
       # do something with the gid and duration of the frame
       # this may change in the future, as it is a little awkward now
       image = tmx_map.get_tile_image_by_gid(gid)
       duration = animation_frame.duration
       ...

```

#### If you really want to work with layer data directly...

This information is provided for the curious, but for most people is not
required for normal use.

Layer tiles are stored as a 'list of lists', or '2d array'.  Each element of
layer data is a number which refers to a specific image in the map.  These
numbers are called GID.  Do not make references to these numbers, as they
will change if the map changes. 

Images for the GID can be accessed with the TiledMap.images list.

With pygame, images will be plain pygame surfaces.  These surfaces will be
checked for colorkey or per-pixel alpha automatically using information from
the TMX file and from checking each image for transparent pixels.  You
do not need, and should not convert the tiles because it is already done. 

```python
layer = tiled_map.layers[0]
for x, y, gid in layer:
    ...

# get image using gid (not needed for normal use!)
# row index = 'y'
# column index = 'x'
image_gid = layer[row_index][column_index]
image = tiled_map.images[image_gid]

# change GID of a position
layer[y][x] = new_gid
```

Working with Objects
===============================================================================

Tiled "objects" are things that are created in object layers, and include
polygons, polylings, boxes, ellipses, and tile objects.  pytmx loads all objects
and their data:

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
even polygons and polylines.

#### Image Objects
If using a loader, then TiledObject.image will be a reference to the image used.

#### Tile Objects
Tile Objects are objects that reference a tile in a tileset.  These are loaded and
the image will be available to use.

#### Polygon/Polyline Objects
These objects have special attributes: 'closed' and 'points'.  Each point is (x, y) tuple.
If the object is a polygon, then TiledObject.closed will be True.  Points are not
rotated if the rotation property is used.

#### Accessing objects

Objects can be accessed through the TiledMap or through a group.  Object groups can be
used just like a python list, and support indexing, slicing, etc.

```python
# search for an object with a specific name
my_object = tiled_map.get_object_by_name("baddy001")  # will not return duplicates

# get a group by name
group = tiled_map.get_layer_by_name("traps")

# copy a group
traps = group[:]

# iterate through objects in a group:
for obj in group:
    ...
```

Understanding Properties
===============================================================================

Properties are a powerful feature of Tiled that allows the level designer to
assign key/value data to individual maps, tilesets, tiles, and objects.  pytmx
includes full support for reading this data so you can set parameters for stuff
in Tiled, instead of maintaining external data files, or even values in source.

Properties are created by the user in tiled.  There is also another set of data
that is part of each object, accessed by normal object attributes.  This other
data is not set directly by the user, but is instead set by tiled.  Typical
data that is object attributes are: 'name', 'x', 'opacity', or 'id'.

If the user sets data for an object in Tiled, it becomes part of 'properties'.
'Properties' is just a normal python dictionary.

```python
# get data normally set by Tiled
obj.name
obj.x
obj.opacity

# get data set by the user in Tiled
obj.properties['hit points']
obj.properties['goes to 11']
```

Individual tile properties are accessed through the the parent map object:

```
tiled_map = TiledMap('level1.tmx')
props = tiled_map.get_tile_properties(x, y, layer)
props = tiled_map.get_tile_properties_by_gid(tile_gid)
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

pytmx will raise a ValueError if it detects any conflicts.  This check is
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
tiled_map = load_pygame('map.tmx', allow_duplicate_names=True)
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

object:      id, name, type, x, y, width, height, gid, properties, polygon,  
             polyline, image


#### Please consider the following:

pytmx is a map __loader__.  pytmx takes the pain out of parsing XML, variable type conversion, shape loading, properties, and of course image loading.  When asking for help, please understand that I want people to make their own games or utilities, and that pytmx is able to make Tiled Maps easy to use.

pytmx is not going to make your JRPG for you.  You will need to do that yourself, and I, the author, cannot simply respond to every new developer who expects pytmx, pygame, or any other game library to simply make it work for them.  Programming is a learned skill, and for most it takes practice and diligent study to get proficient at.  I'm generally open to help, so before you flame me on your blog or reddit, understand what pytmx is used for, read the documentation and copy/paste the demo code if you have to.  Thank you.

I have a working solution to using Tiled Maps and Pygame ready for you.  If you simply want a library to render the maps for you, please check it out, as they are designed to work together.

http://github.com/bitcraft/pyscroll


Artwork Attributions
===============================================================================
The 16x16 overworld tiles were created by MrBeast at opengameart.org. CC-BY 3.0

* If I missed your attribution, please let me know.

