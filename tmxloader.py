"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v.13 - for python 2.7

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

layer:      name, x, y, width, height, opacity, properties, data

objectgroup: name, color, x, y, width, height, opacity, object, properties

object:     name, type, x, y, width, height, gid, properties, polygon,
            polyline, image



I have been intentionally not including a rendering utility since rendering a
map will not be the same in every situation.  However, I can appreciate that
some poeple won't understand how it works unless they see it, so I am including
a sample map and viewer.

I've included a copy of this loader that may work with python 3.x.  I
personally do not think that python 3.x should be used with pygame, yet (and I
am not the only person).  You can try it if you insist on using pygame with
python 3.x, but I don't update that often.

===============================================================================

Basic usage sample:

    >>> import tmxloader
    >>> tmxdata = tmxloader.load_pygame("map.tmx")


When you want to draw tiles, you simply call "get_tile_image":

    >>> image = tmxdata.get_tile_image(x, y, layer)    
    >>> screen.blit(position, image)


Maps, tilesets, layers, objectgroups, and objects all have a simple way to
access metadata that was set inside tiled: they all become object attributes.

    >>> layer = tmxdata.layers[0]
    >>> print layer.tilewidth
    32
    >>> print layer.weather
    'sunny'


Tiles properties are the exception here, and must be accessed through
"getTileProperties".  The data is a regular Python dictionary:

    >>> tile = tmxdata.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'

"""

from itertools import chain, product


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

    In the interest of memory consumption, this loader ignores any tiles that
    are never actually displayed on the map.  As a consequence, the GID's that
    are stored in Tiled and the TMX format will not be the same in most cases.
    """

    reserved = "version orientation width height tilewidth tileheight properties tileset layer objectgroup".split()


    def __init__(self):
        from collections import defaultdict

        TiledElement.__init__(self)
        self.layers = []            # list of all layers
        self.tilesets = []          # list of TiledTileset objects
        self.tilelayers   = []      # list of TiledLayer objects
        self.objectgroups = []      # list of TiledObjectGroup objects
        self.tile_properties = {}   # dict of tiles that have metadata
        self.gidmap = {}            # mapping between gid that are loaded
        self.filename = None

        self.visibleTileLayers = [] # list of tile layers that should be drawn

        # should be filled in by a loader function
        self.images = []

        # defaults from the TMX specification
        self.version = 0.0
        self.orientation = None
        self.width = 0
        self.height = 0
        self.tilewidth = 0
        self.tileheight = 0 

        self.transgids = defaultdict(list)  # keep record of tiles to modify
        self.imagemap = {}  # mapping of gid and trans flags to real gids
        self.loadgids = []  # gids that should be loaded for display
        self.maxgid = 1


    def getTileImage(self, x, y, layer):
        """
        return the tile image for this location
        x and y must be integers and are in tile coordinates, not pixel

        return value will be 0 if there is no tile with that location.
        """

        try:
            gid = self.tilelayers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            raise Exception, msg.format(x, y, layer)
        except TypeError:
            msg = "Tiles must be specified in integers."
            raise TypeError, msg

        else:
            try:
                return self.images[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invaid GID: {3}"
                raise Exception, msg.format(x, y, layer, gid)


    def getTileGID(self, x, y, layer):
        """
        return GID of a tile in this location
        x and y must be integers and are in tile coordinates, not pixel
        """

        try:
            return self.tilelayers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid"
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
        """

        raise NotImplementedError


    def getObjects(self):
        """
        Return iterator of all the objects associated with this map
        """

        return chain(*[ i.objects for i in self.objectgroups ])


    def getTileProperties(self, (x, y, layer)):
        """
        return the properties for the tile, if any
        x and y must be integers and are in tile coordinates, not pixel

        returns a dict of there are properties, otherwise will be None
        """

        try:
            gid = self.tilelayers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            raise Exception, msg.format(x, y, layer)

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invaid GID: {3}"
                raise Exception, msg.format(x, y, layer, gid)
            except KeyError:
                return None


    def getLayerData(self, layer):
        """
        Return the data for a layer.

        Data is an array of arrays.

        pos = data[y][x]
        """

        try:
            return self.tilelayers[layer].data
        except IndexError:
            msg = "Layer {} does not exist."
            raise ValueError, msg.format(layer)


    def getTileLocation(self, gid):
        # experimental way to find locations of a tile by the GID

        p = product(xrange(self.width),
                    xrange(self.height),
                    xrange(len(self.tilelayers)))

        return [ (x,y,l) for (x,y,l) in p 
               if self.tilelayers[l].data[y][x] == gid ]


    def getTilePropertiesByGID(self, gid):
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None


    def getTilePropertiesByLayer(self, layer):
        """
        Return a list of tile properties (dict) in use in this tile layer.
        """

        try:
            layer = int(layer)
        except:
            msg = "Layer must be an integer"
            raise ValueError, msg

        p = product(range(self.width),range(self.height))
        layergids = set( self.tilelayers[layer].data[y][x] for x, y in p )

        props = []
        for gid in layergids:
            try:
                props.append((gid, self.tile_properties[gid]))
            except:
                continue
            
        return props


    def loadTileImages(self, filename):
        raise NotImplementedError


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
    reserved = "name x y width height opacity properties data".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.data = None

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = True
        
class TiledObjectGroup(TiledElement):
    reserved = "name color x y width height opacity object properties".split()

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
    (unless you just want the data).

    See the load_pygame func for an idea of what to do if you want to extend
    this further to load images.
    """

    from xml.dom.minidom import parse
    from itertools import tee, islice, izip, chain, imap
    from collections import defaultdict 
    from struct import unpack
    import array, os


    def handle_bool(text):
        # properly convert strings to a bool
        try:
            return bool(int(text))
        except:
            pass

        try:
            text = str(text).lower()
            if text == "true":   return True
            if text == "yes":    return True
            if text == "no":     return False
            if text == "false":  return False
        except:
            pass
            
        raise ValueError

    # used to change the unicode string returned from minidom to
    # proper python variable types.
    types = defaultdict(lambda: str)
    types.update({
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
        "visible": handle_bool,
        "encoding": str,
        "compression": str,
        "gid": int,
        "type": str,
        "x": int,
        "y": int,
        "value": str,
    })

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
        [ setattr(obj, k, types[str(k)](v)) 
        for k,v in get_attributes(node).items() ] 

        # set the attributes that are derived from tiled 'properties'
        for k,v in parse_properties(node).items():
            if k in obj.reserved:
                msg = "{} has a property called \"{}\".\nThis name is reserved for {} objects and can cannot be used.\nPlease change the name in Tiled and try again."
                raise ValueError, msg.format(obj.name, k, obj.__class__.__name__)
            setattr(obj, k, types[str(k)](v))


    def get_attributes(node):
        """
        get the attributes from a node and fix them to the correct type
        """

        return dict([ (str(k), types[str(k)](v))
                    for (k,v) in node.attributes.items() ])


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


    def parse_tileset(node, firstgid=None, mapping=None):
        """
        parse a tileset element and return a tileset object and properties for
        tiles as a dict

        if mapping is specified, the gid of tiles found will be used as a key,
        and will be changed to the value of the key.  gids not found in the
        dict will not be loaded
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
                if mapping == None:
                    del p["id"]
                    tiles[gid] = p
                elif isinstance(mapping, dict):
                    try:
                        tiles[mapping[gid]] = p
                        del p["id"]
                    except KeyError:
                        pass
                else:
                    msg = "mapping supplied to parse_tileset must be a dict"
                    raise TypeError, msg

        # check for tiled "external tilesets"
        if tileset.source:
            if tileset.source[-4:].lower() == ".tsx":
                # we need to mangle the path - tiled stores relative paths
                dirname = os.path.dirname(filename)
                path = os.path.abspath(os.path.join(dirname, tileset.source))
                try:
                    tsx = parse(path)
                except IOError:
                    msg = "Cannot load external tileset: {}"
                    raise Exception, msg.format(path)

                tileset_node = tsx.getElementsByTagName("tileset")[0]
                tileset, tiles = parse_tileset(tileset_node, \
                                                tileset.firstgid, mapping)
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
            tileset.trans = attr.get("trans", None)

            # calculate the number of tiles in this tileset
            x, r = divmod(attr["width"], tileset.tilewidth)
            y, r = divmod(attr["height"], tileset.tileheight)

            tileset.lastgid = tileset.firstgid + x + y
          
        return tileset, tiles


    def parse_layer(tmxdata, node):
        """
        parse a layer element
        returns a layer object and the gids that are used in it
        """

        layer = TiledLayer()
        layer.data = []
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

        # fill up our 2D array of gid's.
        for y in xrange(layer.height):

            # since we will never use enough tiles to require a 32-bit int,
            # store as array of bytes
            layer.data.append(array.array("B"))

            for x in xrange(layer.width):
                real_gid, flags = decode_gid(next(next_gid))

                # we make a new gid based on the transformation of the tile
                try:
                    gid = tmxdata.imagemap[(real_gid, flags)]
                except KeyError:
                    gid = tmxdata.maxgid
                    tmxdata.maxgid += 1
                    tmxdata.imagemap[(real_gid, flags)] = gid

                    if flags == 0:
                        tmxdata.loadgids.append(real_gid)
                        tmxdata.gidmap[real_gid] = gid
                    else:
                        tmxdata.transgids[real_gid].append((gid, flags))

                layer.data[y].append(gid)

        return layer


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
        return a tmxdata
        """

        tmxdata = TiledMap()
        tmxdata.filename = filename
        set_properties(tmxdata, map_node)

        # initialize the gid mapping
        tmxdata.imagemap[(0,0)] = 0

        # loading the layers first will fill in a list of used tiles
        for node in dom.getElementsByTagName("layer"):
            l = parse_layer(tmxdata, node)
            tmxdata.tilelayers.append(l)
            tmxdata.layers.append(l)
            if l.visible:
                tmxdata.visibleTileLayers.append(l)

        for node in map_node.getElementsByTagName("tileset"):
            t, tiles = parse_tileset(node, mapping=tmxdata.gidmap)
            tmxdata.tilesets.append(t)
            tmxdata.tile_properties.update(tiles)

        # we need to create references from the rotated tiles to their original
        # in order for tile properties to work (since they have a new GID)
        for realgid, l in tmxdata.transgids.items():
            d = tmxdata.tile_properties[tmxdata.gidmap[realgid]]
            for gid, flags in l:
                tmxdata.tile_properties[gid] = d

        for node in dom.getElementsByTagName("objectgroup"):
            o = parse_objectgroup(node)
            tmxdata.objectgroups.append(o)
            tmxdata.layers.append(o)

        return tmxdata


    dom = parse(filename)
    map_node = dom.getElementsByTagName("map")[0]

    return parse_map(map_node)


def load_images_pygame(tmxdata, mapping, *args, **kwargs):
    """
    given tmx data, return an array that is suitable as for the tmxdata object.
    why use this?  to change the tileset on the fly without reloading the
    the entire .tmx file.  metadata will be preserved.
    """

    from itertools import product
    from pygame import Surface, mask
    import pygame, os


    def handle_transformation(tile, flags):
        fx = flags & TRANS_FLIPX == TRANS_FLIPX
        fy = flags & TRANS_FLIPY == TRANS_FLIPY
        r  = flags & TRANS_ROT == TRANS_ROT

        if r:
            # not sure why the flip is required...but it is.
            newtile = pygame.transform.rotate(tile, 270)
            newtile = pygame.transform.flip(tile, 1, 0)

        if fx or fy:
            newtile = pygame.transform.flip(tile, fx, fy)

        # preserve any flags that may have been lost after the transformation
        newtile = newtile.convert(tile)

        return newtile

    pixelalpha     = kwargs.get("pixelalpha", False)
    force_colorkey = kwargs.get("force_colorkey", False)
    force_bitdepth = kwargs.get("depth", False)

    if force_colorkey:
        try:
            force_colorkey = pygame.Color(*force_colorkey)
        except:
            msg = "Cannot understand color: {}".format(force_colorkey)
            raise Exception, msg

    tmxdata.images = [0] * tmxdata.maxgid

    usedgids = tmxdata.loadgids[:]
    usedgids.extend(tmxdata.transgids.keys())

    for firstgid, t in sorted([ (t.firstgid, t) for t in tmxdata.tilesets ]):
        path = os.path.join(os.path.dirname(tmxdata.filename), t.source)

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
            if not gid in usedgids:
                gid += 1
                continue

            # determine if the tile contains any transparent area
            temp = image.subsurface(((x,y), tile_size))

            # if not, then we don't set any special blitting flags
            # make a copy so that the parent surface isn't lingering in memory
            px = mask.from_surface(temp).count()

            # there are no transparent pixels in the image
            if px == tile_size[0] * tile_size[1]:
                tile = temp.convert()

            # there are transparent pixels, and set to force a colorkey
            elif force_colorkey:
                tile = Surface(tile_size)
                tile.fill(force_colorkey)
                tile.blit(temp, (0,0))
                tile.set_colorkey(force_colorkey, pygame.RLEACCEL)

            # there are transparent pixels, and tiled set a colorkey
            elif t.trans:
                tile = temp.convert()
                tile.set_colorkey(t.trans, pygame.RLEACCEL)

            # there are transparent pixels, and set for perpixel alpha
            elif pixelalpha:
                tile = temp.convert_alpha()

            # there are transparent pixels, and we won't handle them
            else:
                tile = temp.convert()


            tmxdata.images[tmxdata.gidmap[gid]] = tile

            # handle transformations, if needed
            if gid in tmxdata.transgids.keys():
                for newgid, flags in tmxdata.transgids[gid]:
                    tmxdata.images[newgid]=handle_transformation(tile,flags)

            gid += 1


    del tmxdata.imagemap
    del tmxdata.loadgids
    del tmxdata.transgids
    del tmxdata.maxgid

    return tmxdata


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

    an impressive speedup of about 10x can be made for tiles that do not need
    colorkey transparency or per-pixel alphas.  for tiles that completely fill
    the surface, it is not needed to set colorkey or alpha and will result in
    much quicker blitting *for those tiles*
    """

    tmxdata = load_tmx(filename, *args, **kwargs)
    load_images_pygame(tmxdata, None, *args, **kwargs)

    return tmxdata


def buildDistributionRects(tmxmap, layer, gid=None):
    """
    generate a set of non-overlapping rects that represents the distribution
    of the specfied gid.  if gid is not passed, then will choose one.

    useful for collision detection
    """
    
    import maputils

    if gid == None:
        gid = tmxmap.gidmap[tmxmap.tilesets[layer].firstgid]

    layer_data = tmxmap.getLayerData(layer)
    p = product(xrange(tmxmap.width), xrange(tmxmap.height))
    points = [ (x,y) for (x,y) in p if layer_data[y][x] == gid ]
    rects = maputils.simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects
