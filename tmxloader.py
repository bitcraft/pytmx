"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v.12 - for python 2.7

If you have any problems or suggestions, please contact me via email.
Tested with Tiled 0.8.0 for Mac.

released under the GPL v3

===============================================================================

This map loader can be used to load maps created in the Tiled map editor.  It
provides a simple way to get tiles and associated metadata so that you can draw
a map onto the screen.

This is *not* a rendering engine.  It will load the data that is necessary to
render a map onto the screen.  All tiles will be loaded into in memory and
available to blit onto the screen.


Design Goals:
    Simple api
    Memory efficient and fast

Features:
    Loads data and "properties" metadata from Tile's TMX format
    "Properties" for: maps, tilesets, layers, objectgroups, objects, and tiles
    Automatic flipping and rotation of tiles
    Supports base64, csv, gzip, zlib and uncompressed TMX
    Image loading with pygame

Missing:
    Polyline (new in 0.8.0)
    Polygon (new in 0.8.0)


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


NOTES:

* The Tiled "properties" have reserved names.

If you use "properties" for any of the following object types, you cannot use
any of theese words as a name for your property.  A ValueError will be raised
if there are any conflicts.

As of 0.8.0, these values are:

map:        version, orientation, width, height, tilewidth, tileheight
            properties, tileset, layer, objectgroup

tileset:    firstgid, source, name, tilewidth, tileheight, spacing, margin,
            image, tile, properties

tile:       id, image, properties

layer:      name, x, y, width, height, opacity, visible, properties, data

objectgroup: name, color, x, y, width, height, opacity, visible, object,
             properties

object:     name, type, x, y, width, height, gid, properties, polygon,
            polyline, image



I've had some suggestions that I include a rendering function for this loader.
I have been intentionally not including a rendering utility since rendering a
map will not be the same in every situation.  However, I can appreciate that
some poeple won't understand how it works unless they see it, so I am including
a sample map and viewer.

I've included a copy of this loader that may work with python 3.x.  I
personally do not think that python 3.x should be used with pygame, yet (and I
am not the only person).  You can try it if you insist on using pygame with
python 3.x, but it is not supported.

===============================================================================

Basic usage sample:

    >>> import tmxloader
    >>> tiledmap = tmxloader.load_pygame("map.tmx")


When you want to draw tiles, you simply call "get_tile_image":

    >>> image = tiledmap.get_tile_image(x, y, layer)    
    >>> screen.blit(position, image)


Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tiledmap.layers[0]
    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'


Tiles properties are the exception here, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tiledmap.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'

"""

from itertools import chain
import pprint


# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4


# Tiled gid flags
GID_TRANS_FLIPX = 1<<31
GID_TRANS_FLIPY = 1<<30
GID_TRANS_ROT   = 1<<29


class TiledElement(object):
    pass

class TiledMap(TiledElement):
    """
    not really useful unless "loaded"  ie: don't instance directly.
    see the pygame loader for inspiration
    """

    reserved = "version orientation width height tilewidth tileheight properties tileset layer objectgroup".split()


    def __init__(self):
        TiledElement.__init__(self)
        self.layers = []            # list of all layers
        self.tilesets = []          # list of TiledTileset objects
        self.tilelayers   = []      # list of TiledLayer objects
        self.objectgroups = []      # list of TiledObjectGroup objects
        self.tile_properties = {}   # dict of tiles that have metadata
        self.used_gids = []         # list of all the GIDs that are used
        self.filename = None

        # index 0 is a work around to tiled's strange way of storing gid's
        self.images = [0]

        # defaults from the TMX specification
        self.version = 0.0
        self.orientation = None
        self.width = 0
        self.height = 0
        self.tilewidth = 0
        self.tileheight = 0 


    def get_tile_image(self, x, y, layer):
        """
        return the tile image for this location
        x and y must be integers and are in tile coordinates, not pixel

        return value will be 0 if there is no tile with that location.
        """

        try:
            gid = self.tilelayers[layer].data[y][x]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            raise Exception, msg.format(x, y, layer)

        else:
            try:
                return self.images[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invaid GID: {3}/{4}."
                raise Exception, msg.format(x, y, layer, gid, len(self.images))


    def getTileGID(self, x, y, layer):
        """
        return GID of a tile in this location
        x and y must be integers and are in tile coordinates, not pixel
        """

        try:
            return self.tilelayers[layer].data[y][x]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            raise Exception, msg.format(x, y, layer)


    def getDrawOrder(self):
        """
        return a list of objects in the order that they should be drawn
        this will also exclude any layers that are not set to visible

        may be useful if you have objects and want to control rendering
        from tiled
        """

        raise NotImplementedError


    def getTileImages(self, r, layer):
        """
        return a group of tiles in an area
        expects a pygame rect or rect-like list/tuple

        usefull if you don't want to repeatedly call get_tile_image
        probably not the most effecient way of doing this, but oh well.
        """

        raise NotImplementedError


    def getObjects(self):
        """
        Return iterator of all the objects associated with this map
        """

        return chain(*[ i.objects for i in self.objectgroups ])


    def getTileProperties(self, x, y, layer):
        """
        return the properties for the tile, if any
        x and y must be integers and are in tile coordinates, not pixel

        returns a dict of there are properties, otherwise will be None
        """

        try:
            gid = self.tilelayers[layer].data[y][x]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            raise Exception, msg.format(x, y, layer)

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invaid GID: {3}/{4}."
                raise Exception, msg.format(x, y, layer, gid, len(self.images))


    def getTilePropertiesByGID(self, gid):
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None


# the following classes get their attributes filled in with the loader

class TiledTileset(TiledElement):
    reserved = "firstgid source name tilewidth tileheight spacing margin image tile properties".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.lastgid = 0

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0

class TiledLayer(TiledElement):
    reserved = "name x y width height opacity visible properties data".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.data = None

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = 1
        
class TiledObjectGroup(TiledElement):
    reserved = "name color x y width height opacity visible object properties".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.objects = []

        # defaults from the specification
        self.name = None

class TiledObject(TiledElement):
    __slots__ = "reserved name type x y width height gid".split()
    reserved = "name type x y width height gid properties polygon polyline image".split()

    def __init__(self):
        TiledElement.__init__(self)

        # defaults from the specification
        self.name = None
        self.type = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.gid = 0


def load_tmx(filename, *args, **kwargs):
    """
    Utility function to parse a Tiled TMX and return a usable object.
    Images will not be loaded, so probably not useful to call this directly

    See the load_pygame func for an idea of what to do if you want to extend
    this further.
    """

    from xml.dom.minidom import parse
    from itertools import tee, islice, izip, chain, imap
    from collections import defaultdict 
    from struct import unpack
    import array, os

    # used to change the unicode string returned from minidom to
    # proper python variable types.
    types = {
        "version": float,
        "orientation": str,
        "width": int,
        "height": int,
        "tilewidth": int,
        "tileheight": int,
        "firstgid": int,
        "source": str,
        "name": str,
        "spacing": int,
        "margin": int,
        "source": str,
        "trans": str,
        "id": int,
        "opacity": float,
        "visible": bool,
        "encoding": str,
        "compression": str,
        "gid": int,
        "type": str,
        "x": int,
        "y": int,
        "value": str,
    }

    # used to condense the size of the images array
    gid_mapping = {}
 
    def pairwise(iterable):
        # return a list as a sequence of pairs
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)

    def group(l, n):
        # return a list as a sequence of n tuples
        return izip(*[islice(l, i, None, n) for i in xrange(n)])

    def parse_properties(node):
        """
        parse a node and return a dict that represents a tiled "property"
        """

        d = {}

        for child in node.childNodes:
            if child.nodeName == "properties":
                for subnode in child.getElementsByTagName("property"):
                    # the "properties" from tiled's tmx have an annoying
                    # quality that "name" and "value" is included.
                    # here we mangle it to get that stuff out.
                    d.update(dict(pairwise(
                        [str(i.value) for i in subnode.attributes.values()])))

        return d

    def get_properties(node, reserved=[]):
        """
        parses a node and returns a dict that contains the data from the node's
        attributes and any data from "property" elements as well.  Names will
        be checked to make sure that they do not conflict with reserved names.
        """

        d = {}

        # set the attributes that are set by tiled
        d.update(get_attributes(node))

        # set the attributes that are derived from tiled 'properties'
        for k,v in parse_properties(node).items():
            if k in reserved:
                msg = "The name \"{}\" is reserved cannot be used.\nPlease change the name in Tiled and try again."
                raise ValueError, msg.format(k)
            d[k] = v

        return d

    def set_properties(obj, node):
        """
        read the xml attributes and tiled "properties" from a xml node and fill
        in the values into the object's dictionary.  Names will be checked to
        make sure that they do not conflict with reserved names.
        """

        # set the attributes from reserved for tiled
        [ setattr(obj, k, v) for k,v in get_attributes(node).items() ] 

        # set the attributes that are derived from tiled 'properties'
        for k,v in parse_properties(node).items():
            if k in obj.reserved:
                msg = "{} has a property called \"{}\".\nThis name is reserved for {} objects and can cannot be used.\nPlease change the name in Tiled and try again."
                raise ValueError, msg.format(obj.name, k, obj.__class__.__name__)
            setattr(obj, k, v)


    def get_attributes(node):
        """
        get the attributes from a node and fix them to the correct type
        """

        d = defaultdict(lambda:None)

        for k, v in node.attributes.items():
            k = str(k)
            d[k] = types[k](v)

        return d

    def decode_gid(raw_gid):
        # gid's are encoded with extra information
        # as of 0.7.0 it determines if the tile should be flipped when rendered
        # as of 0.8.0 bit 30 determines if tip is rotated

        flags = 0
        if raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX: flags += TRANS_FLIPX
        if raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY: flags += TRANS_FLIPY
        if raw_gid & GID_TRANS_ROT == GID_TRANS_ROT: flags += TRANS_ROT
        gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)

        return gid, flags


    def parse_tileset(node, firstgid=None):
        """
        parse a tileset element and return a tileset object and properties for
        tiles as a dict
        """

        tileset = TiledTileset()
        set_properties(tileset, node)
        tiles = {}

        if firstgid != None:
            tileset.firstgid = firstgid

        # since tile objects [probably] don't have a lot of metadata,
        # we store it seperately from the class itself
        for child in node.childNodes:
            if child.nodeName == "tile":
                p = get_properties(child)
                gid = p["id"] + tileset.firstgid
                del p["id"]
                tiles[gid] = p

        # check for tiled "external tilesets"
        if tileset.source:
            if tileset.source[-4:].lower() == ".tsx":
                try:
                    # we need to mangle the path - tiled stores relative paths
                    path=os.path.join(os.path.dirname(filename),tileset.source)
                    tsx = parse(path)
                except IOError:
                    msg = "Cannot load external tileset: {}"
                    raise Exception, msg.format(path)

                tileset_node = tsx.getElementsByTagName("tileset")[0]
                tileset, tiles = parse_tileset(tileset_node, tileset.firstgid)
            else:
                msg = "Found external tileset, but cannot handle type: {}"
                raise Exception, msg.format(tileset.source)

        # if we have an "image" tag, process it here
        try:
            image_node = node.getElementsByTagName("image")[0]
        except IndexError:
            pass
        else:
            attr = get_attributes(image_node)
            tileset.source = attr["source"]
            tileset.trans = attr["trans"]

            # calculate the number of tiles in this tileset
            x, r = divmod(attr["width"], tileset.tilewidth)
            y, r = divmod(attr["height"], tileset.tileheight)

            tileset.lastgid = tileset.firstgid + x + y
          
        return tileset, tiles


    def parse_layer(tilesets, node):
        """
        parse a layer element
        returns a layer object and the gids that are used in it

        tilesets is required since we need to mangle gid's here
        """

        layer = TiledLayer()
        layer.data = []
        layer.flipped_tiles = []
        set_properties(layer, node)

        data = None
        next_gid = None

        data_node = node.getElementsByTagName("data")[0]
        attr = get_attributes(data_node)

        if attr["encoding"] == "base64":
            from base64 import decodestring
            data = decodestring(data_node.lastChild.nodeValue)

        elif attr["encoding"] == "csv":
            next_gid = imap(int, "".join(
                [ line.strip() for line in data_node.lastChild.nodeValue ]
                ).split(","))

        elif not attr["encoding"] == None:
            msg = "TMX encoding type: {} is not supported."
            raise Exception, msg.format(str(attr["encoding"]))

        if attr["compression"] == "gzip":
            from StringIO import StringIO
            import gzip
            with gzip.GzipFile(fileobj=StringIO(data)) as fh:
                data = fh.read()

        elif attr["compression"] == "zlib":
            try:
                import zlib
            except:
                msg = "Cannot import zlib. Make sure it is installed."
                raise Exception, msg

            data = zlib.decompress(data)

        elif not attr["compression"] == None:
            msg = "TMX compression type: {} is not supported."
            raise Exception, msg.format(str(attr["compression"]))
     
        # if data is None, then it was not decoded or decompressed, so
        # we assume here that it is going to be a bunch of tile elements
        # TODO: this will probably raise an exception if there are no tiles
        if attr["encoding"] == next_gid == None:
            def get_children(parent):
                for child in parent.getElementsByTagName("tile"):
                    yield int(child.getAttribute("gid"))

            next_gid = get_children(data_node)

        elif not data == None:
            # data is a list of gid's. cast as 32-bit ints to format properly
            next_gid=imap(lambda i:unpack("<L", "".join(i))[0], group(data, 4))

        # we will use this to determine which gids are actually used
        used_gids = set()

        # fill up our 2D array of gid's.
        for y in xrange(layer.height):

            # since we will never use enough tiles to require a 32-bit int,
            # store as array of 16-bit ints
            layer.data.append(array.array("H"))

            for x in xrange(layer.width):
                gid, flags = decode_gid(next(next_gid))
                used_gids.add(gid)
                # check for tile transformations and add them to a list
                # it is up to the graphics library to handle the actual
                # transforming of the tile.  see load_pygame() for ideas.
                if not flags == 0:
                    layer.flipped_tiles.append((x, y, gid, flags))
                layer.data[y].append(gid)
                gid_mapping[gid] = len(used_gids)

        return layer, used_gids


    def parse_objectgroup(node):
        """
        parse a objectgroup element and return a object group
        """

        objgroup = TiledObjectGroup()
        set_properties(objgroup, node)

        for subnode in node.getElementsByTagName("object"):
            obj = TiledObject()
            set_properties(obj, subnode)
            objgroup.objects.append(obj)

        return objgroup


    def parse_map(node):
        """
        parse a map node from a tiled tmx file
        return a tiledmap
        """

        tiledmap = TiledMap()
        tiledmap.filename = filename
        set_properties(tiledmap, map_node)

        used_gids = set()

        for node in map_node.getElementsByTagName("tileset"):
            t, tiles = parse_tileset(node)
            tiledmap.tilesets.append(t)
            tiledmap.tile_properties.update(tiles)

        for node in dom.getElementsByTagName("layer"):
            l, gids = parse_layer(tiledmap.tilesets, node)
            tiledmap.tilelayers.append(l)
            tiledmap.layers.append(l)
            used_gids = used_gids.union(gids)

        for node in dom.getElementsByTagName("objectgroup"):
            o = parse_objectgroup(node)
            tiledmap.objectgroups.append(o)
            tiledmap.layers.append(o)

        # this tuple defines all the gids that are will be displayed
        tiledmap.used_gids = tuple(used_gids)

        return tiledmap


    # open and read our TMX (which is really just xml)
    dom = parse(filename)
    map_node = dom.getElementsByTagName("map")[0]

    m = parse_map(map_node)

    return m


def load_pygame(filename, *args, **kwargs):
    """
    load a tiled TMX map for use with pygame

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
    may not look like the original.
    """

    # load the data
    tiledmap = load_tmx(filename, *args, **kwargs)

    from itertools import product
    from pygame import Surface
    import pygame, os

    pixelalpha     = kwargs.get("pixelalpha", False)
    force_colorkey = kwargs.get("force_colorkey", False)
    force_bitdepth = kwargs.get("depth", False)

    if force_colorkey:
        try:
            force_colorkey = pygame.Color(*force_colorkey)
        except:
            msg = "Cannot understand color: {}".format(force_colorkey)
            raise Exception, msg

    # cache will find duplicate tiles to reduce memory usage
    # mostly this is a problem in the blank areas of a tilemap
    cache = {}
    gid = 0

    # just a precaution so that tileset images are added in the correct order
    for firstgid, t in sorted([ (t.firstgid, t) for t in tiledmap.tilesets ]):
        path = os.path.join(os.path.dirname(tiledmap.filename), t.source)

        if force_colorkey:
            temp = pygame.image.load(path).convert_alpha()
            image = Surface(temp.get_size())
            image.fill(force_colorkey)
            image.blit(temp, (0,0))
 
        elif t.trans == None:
            image = pygame.image.load(path).convert_alpha()

        else:
            image = pygame.image.load(path)

        w, h = image.get_size()
        tile_size = (t.tilewidth, t.tileheight)
        gid = firstgid

        # some tileset images may be slightly larger than the tiles area
        # ie: may include a banner, copyright, ect.  this compensates for that
        x_range = xrange(0, int(w / t.tilewidth) * t.tilewidth, t.tilewidth)
        y_range = xrange(0, int(h / t.tileheight) * t.tileheight, t.tileheight)

        # using product avoids the overhead of nested loops
        for (y, x) in product(y_range, x_range):

            # prevent loading of tiles that are never used in the loader
            # TODO: create a mapping so that the images array is smaller
            #       instead of adding zeros.  This would save memory.
            if gid not in tiledmap.used_gids:
                tiledmap.images.append(0)
                gid += 1
                continue

            if force_bitdepth:
                tile = Surface(tile_size, depth=force_bitdepth)
            else:
                tile = Surface(tile_size)

            if force_colorkey:
                tile.set_colorkey(force_colorkey, pygame.RLEACCEL)

            elif t.trans:
                tile.set_colorkey(t.trans, pygame.RLEACCEL)

            elif t.trans == None:
                if pixelalpha:
                    tile = Surface(tile_size, pygame.SRCALPHA)
                else:
                    tile = Surface(tile_size)

            # blit the smaller portion onto a new image from the larger one
            tile.blit(image, (0,0), ((x, y), tile_size))

            # make a unique id for this image
            if pixelalpha:
                key = pygame.image.tostring(tile, "RGBA")
            else:    
                key = pygame.image.tostring(tile, "RGB")

            # make sure we don't have a duplicate tile
            try:
                tile = cache[key]
            except KeyError:

                cache[key] = tile

            gid += 1
            tiledmap.images.append(tile)

    del cache

    # correctly handle transformed tiles.  currently flipped tiles are handled
    # by creating a new gid for the transformed tile and changing the gid in
    # the layer to the gid for the flipped tile.
    cache = {}

    for layer in tiledmap.tilelayers:
        for x, y, gid, trans in layer.flipped_tiles:

            try:
                gid = cache[(gid, trans)]
                layer.data[y][x] = gid
                continue
            except KeyError:
                pass

            fx = trans & TRANS_FLIPX == TRANS_FLIPX
            fy = trans & TRANS_FLIPY == TRANS_FLIPY
            r  = trans & TRANS_ROT == TRANS_ROT

            tile = tiledmap.images[gid]

            if r:
                # not sure why the flip is required...but it is.
                tile = pygame.transform.rotate(tile, 270)
                tile = pygame.transform.flip(tile, 1, 0)

            if fx or fy:
                newtile = pygame.transform.flip(tile, fx, fy)

            # make sure we preserve any flags that may have been lost after
            # the transformation
            tile = tile.convert(tiledmap.images[gid])

            new_gid = len(tiledmap.images)
            tiledmap.images.append(tile)
            layer.data[y][x] = new_gid
            cache[(gid, trans)] = new_gid

        del layer.flipped_tiles
    del cache
    del tiledmap.used_gids

    return tiledmap
