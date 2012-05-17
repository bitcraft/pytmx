"""
Map loader for TMX Files
bitcraft (leif dot theden at gmail.com)
v.14 - for python 2.7

If you have any problems or suggestions, please contact me via email.
Tested with Tiled 0.8.1 for Mac.

released under the LGPL v3

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
a sample map and viewer.  it includes a scrolling/zooming renderer.

I've included a copy of this loader that may work with python 3.x.  I
personally do not think that python 3.x should be used with pygame, yet (and I
am not the only person).  You can try it if you insist on using pygame with
python 3.x, but I don't update that often.

===============================================================================

Basic usage sample:

    >>> from pytmx import tmxloader
    >>> tmxdata = tmxloader.load_pygame("map.tmx")


When you want to draw tiles, you simply call "getTileImage":

    >>> image = tmxdata.getTileImage(x, y, layer)    
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



Please see the TiledMap class for some api information.
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

    In the interest of memory conservation, the loader ignores any tiles that
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
        self.visibleTileLayers = [] # list of tile layers that should be drawn
        self.filename = None

        # only used tiles are actually loaded, so there will be a difference
        # between the GID's in the Tile map data (tmx) and the data in this class
        # and the layers.  This dictionary keeps track of that difference.
        self.gidmap = defaultdict(list)

        # should be filled in by a loader function
        self.images = []

        # defaults from the TMX specification
        self.version = 0.0
        self.orientation = None
        self.width = 0
        self.height = 0
        self.tilewidth = 0
        self.tileheight = 0 

        self.imagemap = {}  # mapping of gid and trans flags to real gids
        self.maxgid = 1

    def __repr__(self):
        return "<{}: \"{}\">".format(self.__class__.__name__, self.filename)

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
                msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
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

        useful if you don't want to repeatedly call getTileImage
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

        >>> pos = data[y][x]
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
            msg = "Layer must be an integer.  Got {} instead."
            raise ValueError, msg.format(type(layer))

        p = product(range(self.width),range(self.height))
        layergids = set( self.tilelayers[layer].data[y][x] for x, y in p )

        props = []
        for gid in layergids:
            try:
                props.append((gid, self.tile_properties[gid]))
            except:
                continue
            
        return props


    def registerGID(self, real_gid, flags=0):
        """
        used to manage the mapping of GID between the tmx data and the internal
        data.
        number returned is gid used internally
        """

        if real_gid:
            try:
                return self.imagemap[(real_gid, flags)][0]
            except KeyError:
                # this tile has not been encountered before, or it has been
                # transformed in some way.  make a new GID for it.
                gid = self.maxgid
                self.maxgid += 1
                self.imagemap[(real_gid, flags)] = (gid, flags)
                self.gidmap[real_gid].append((gid, flags))
                return gid

        else:
            return 0



    def mapGID(self, real_gid):
        try:
            return self.gidmap[real_gid]
        except KeyError:
            return None


    def loadTileImages(self, filename):
        raise NotImplementedError


# the following classes get their attributes filled in with the loader

class TiledTileset(TiledElement):
    reserved = "firstgid source name tilewidth tileheight spacing margin image tile properties".split()

    def __init__(self):
        TiledElement.__init__(self)

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0

    def __repr__(self):
        return "<{}: \"{}\">".format(self.__class__.__name__, self.name)

class TiledLayer(TiledElement):
    reserved = "name x y width height opacity properties data".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.data = None

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = True
       
    def __repr__(self):
        return "<{}: \"{}\">".format(self.__class__.__name__, self.name)
 
class TiledObjectGroup(TiledElement):
    reserved = "name color x y width height opacity object properties".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.objects = []

        # defaults from the specification
        self.name = None

    def __repr__(self):
        return "<{}: \"{}\">".format(self.__class__.__name__, self.name)

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

    def __repr__(self):
        return "<{}: \"{}\">".format(self.__class__.__name__, self.name)

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
        return izip(*(islice(l, i, None, n) for i in xrange(n)))

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
                        str(i.value) for i in subnode.attributes.values())))

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

        return dict((str(k), types[str(k)](v))
                    for (k,v) in node.attributes.items())


    def decode_gid(raw_gid):
        # gid's are encoded with extra information
        # as of 0.7.0 it determines if the tile should be flipped when rendered
        # as of 0.8.0 bit 30 determines if GID is rotated

        flags = 0
        if raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX: flags += TRANS_FLIPX
        if raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY: flags += TRANS_FLIPY
        if raw_gid & GID_TRANS_ROT == GID_TRANS_ROT: flags += TRANS_ROT
        gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)

        return gid, flags


    def parse_tileset(tmxdata, node, firstgid=None):
        """
        parse a tileset element and return a tileset object and properties for
        tiles as a dict
        """

        tileset = TiledTileset()
        set_properties(tileset, node)
        tiles = {}

        if firstgid:
            tileset.firstgid = firstgid

        # since tile objects [probably] don't have a lot of metadata,
        # we store it seperately from the class itself
        for child in node.childNodes:
            if child.nodeName == "tile":
                p = get_properties(child)
                for gid, flags in tmxdata.mapGID(p["id"] + tileset.firstgid):
                    tiles[gid] = p
                del p["id"]

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
                tileset, tiles = parse_tileset(tmxdata, tileset_node, \
                                               tileset.firstgid)
            else:
                msg = "Found external tileset, but cannot handle type: {}"
                raise Exception, msg.format(tileset.source)

        # if we have an "image" tag, process it here
        # TODO: make sure this is the right thing to do here
        try:
            image_node = node.getElementsByTagName("image")[0]
        except IndexError:
            pass
        else:
            attr = get_attributes(image_node)
            tileset.source = attr["source"]
            tileset.trans = attr.get("trans", None)

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

        encoding = attr.get("encoding", None)
        if encoding == "base64":
            from base64 import decodestring
            data = decodestring(data_node.lastChild.nodeValue)

        elif encoding == "csv":
            next_gid = imap(int, "".join(
                line.strip() for line in data_node.lastChild.nodeValue
                ).split(","))

        elif encoding:
            msg = "TMX encoding type: {} is not supported."
            raise Exception, msg.format(str(attr["encoding"]))

        compression = attr.get("compression", None)
        if compression == "gzip":
            from StringIO import StringIO
            import gzip
            with gzip.GzipFile(fileobj=StringIO(data)) as fh:
                data = fh.read()

        elif compression == "zlib":
            import zlib
            data = zlib.decompress(data)

        elif compression:
            msg = "TMX compression type: {} is not supported."
            raise Exception, msg.format(str(attr["compression"]))
     
        # if data is None, then it was not decoded or decompressed, so
        # we assume here that it is going to be a bunch of tile elements
        # TODO: this will probably raise an exception if there are no tiles
        if encoding == next_gid == None:
            def get_children(parent):
                for child in parent.getElementsByTagName("tile"):
                    yield int(child.getAttribute("gid"))

            next_gid = get_children(data_node)

        elif data:
            # data is a list of gid's. cast as 32-bit ints to format properly
            # create iterator to effeciently parse data
            next_gid=imap(lambda i:unpack("<L", "".join(i))[0], group(data, 4))

        # using bytes here limits the layer to 256 unique tiles
        # may be a limitation for very detailed maps, but most maps are not
        # so detailed. 
        [ layer.data.append(array.array("B")) for i in xrange(layer.height) ]

        for (y, x) in product(xrange(layer.height), xrange(layer.width)):
            layer.data[y].append(tmxdata.registerGID(*decode_gid(next(next_gid))))

        return layer


    def parse_objectgroup(node):
        """
        parse a objectgroup element and return a object group
        """

        objgroup = TiledObjectGroup()
        set_properties(objgroup, node)

        # TODO: objects may contain a GID, we need to change it to mapped GID
        for subnode in node.getElementsByTagName("object"):
            obj = TiledObject()
            set_properties(obj, subnode)
            objgroup.objects.append(obj)

        return objgroup


    def parse_map(node):
        """
        parse a map node from a tiled tmx file
        return a TiledMap object 
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

        # load tilesets...
        for node in map_node.getElementsByTagName("tileset"):
            t, tiles = parse_tileset(tmxdata, node)
            tmxdata.tilesets.append(t)
            tmxdata.tile_properties.update(tiles)
            print tiles

        # we may have created new GID's because a tile was transformed.
        # go through tile properties and make copies if needed

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
    given tmx data, return an array of images.

    why use this?  to change the tileset on the fly without reloading the
    the entire .tmx file.  metadata will be preserved. (test this)
    """

    from itertools import product
    from pygame import Surface, mask
    import pygame, os


    def handle_transformation(tile, flags):
        if flags:
            fx = flags & TRANS_FLIPX == TRANS_FLIPX
            fy = flags & TRANS_FLIPY == TRANS_FLIPY
            r  = flags & TRANS_ROT == TRANS_ROT

            if r:
                # not sure why the flip is required...but it is.
                newtile = pygame.transform.rotate(tile, 270)
                newtile = pygame.transform.flip(newtile, 1, 0)

                if fx or fy:
                    newtile = pygame.transform.flip(newtile, fx, fy)

            elif fx or fy:
                newtile = pygame.transform.flip(tile, fx, fy)

            # preserve any flags that may have been lost after the transformation
            return newtile.convert(tile)

        else:
            return tile


    pixelalpha     = kwargs.get("pixelalpha", False)
    force_colorkey = kwargs.get("force_colorkey", False)
    force_bitdepth = kwargs.get("depth", False)

    if force_colorkey:
        try:
            force_colorkey = pygame.Color(*force_colorkey)
        except:
            msg = "Cannot understand color: {}"
            raise Exception, msg.format(force_colorkey)

    tmxdata.images = [0] * tmxdata.maxgid

    for firstgid, t in sorted((t.firstgid, t) for t in tmxdata.tilesets):
        path = os.path.join(os.path.dirname(tmxdata.filename), t.source)

        image = pygame.image.load(path)

        w, h = image.get_size()
        tile_size = (t.tilewidth, t.tileheight)
        real_gid = t.firstgid - 1

        if t.trans:
            tileset_colorkey = pygame.Color("#{}".format(t.trans)) 

        # i dont agree with margins and spacing, but i'll support it anyway
        # such is life.  okay.jpg
        tilewidth = t.tilewidth + t.spacing
        tileheight = t.tileheight + t.spacing

        # some tileset images may be slightly larger than the tile area
        # ie: may include a banner, copyright, ect.  this compensates for that
        width = ((int((w-t.margin*2) + t.spacing) / tilewidth) * tilewidth) - t.spacing
        height = ((int((h-t.margin*2) + t.spacing) / tileheight) * tileheight) - t.spacing

        # using product avoids the overhead of nested loops
        p = product(xrange(t.margin, height+t.margin, tileheight),
                    xrange(t.margin, width+t.margin, tilewidth))

        for (y, x) in p:
            real_gid += 1
            gids = tmxdata.mapGID(real_gid)
            if gids == []: continue

            # we do some tests to correctly handle the tile and set the right
            # blitting flags.  just grab a section of it.
            temp = image.subsurface(((x,y), tile_size))

            # count the number of pixels in the tile that are not transparent
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
                tile.set_colorkey(tileset_colorkey, pygame.RLEACCEL)

            # there are transparent pixels, and set for perpixel alpha
            elif pixelalpha:
                tile = temp.convert_alpha()

            # there are transparent pixels, and we won't handle them
            else:
                tile = temp.convert()

            for gid, flags in gids:
                tmxdata.images[gid] = handle_transformation(tile, flags)


    del tmxdata.imagemap
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


def buildDistributionRects(tmxmap, layer, tileset=None, real_gid=None):
    """
    generate a set of non-overlapping rects that represents the distribution
    of the specfied gid.

    useful for generating rects for use in collision detection
    """
    
    import maputils

    if isinstance(tileset, int):
        try:
            tileset = tmxmap.tilesets[tileset]
        except IndexError:
            msg = "Tileset #{} not found in map {}."
            raise IndexError, msg.format(tileset, tmxmap)

    elif isinstance(tileset, str):
        try:
            tileset = [ t for t in tmxmap.tilesets if t.name == tileset ].pop()
        except IndexError:
            msg = "Tileset \"{}\" not found in map {}."
            raise ValueError, msg.format(tileset, tmxmap)

    elif tileset:
        msg = "Tileset must be either a int or string. got: {}"
        raise ValueError, msg.format(type(tileset))

    gid = None
    if real_gid:
        try:
            gid, flags = tmxmap.mapGID(real_gid)[0]
        except KeyError, IndexError:
            msg = "GID #{} not found"
            raise ValueError, msg.format(real_gid)


    if isinstance(layer, int):
        layer_data = tmxmap.getLayerData(layer).data
    elif isinstance(layer, str):
        try:
            layer = [ l for l in tmxmap.layers if l.name == layer ].pop()
            layer_data = layer.data
        except IndexError:
            msg = "Layer \"{}\" not found in map {}."
            raise ValueError, msg.format(layer, tmxmap)

    p = product(xrange(tmxmap.width), xrange(tmxmap.height))
    if gid:
        points = [ (x,y) for (x,y) in p if layer_data[y][x] == gid ]
    else:
        points = [ (x,y) for (x,y) in p if layer_data[y][x] ]

    rects = maputils.simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects
