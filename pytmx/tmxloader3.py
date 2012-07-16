"""
Map loader for TMX Files
bitcraft (leif.theden at gmail.com)
v.7  -- for python 3.x

If you have any problems, please contact me via email.
Tested with Tiled 0.7.1 for Mac.

released under the LGPL v3

======================================================================
Design Goals:
    Simple api
    Memory efficient and fast
    Quick access to tiles, attributes, and properties

Non-Goals:
    Rendering

Works:
    Pygame image loading
    Map loading with all required types
    Properties for all types: maps, layers, objects, tiles
    Automatic flipping of tiles

Todo:
    Pygame: test colorkey transparency

    Optimized for maps that do not make heavy use of tile
    properties.  If I find that it is used a lot then I can rework
    it for better performance.

======================================================================

Basic usage sample:

    >>> import tmxloader
    >>> tiledmap = tmxloader.load_pygame("map.tmx")


When you want to draw tiles, you simply call "get_tile_image":

    >>> image = tiledmap.get_tile_image(x, y, layer)
    >>> screen.blit(position, image)


Layers, objectgroups, tilesets, and maps all have a simple way to access
metadata that was set inside tiled: they all become class attributes.

    >>> print(layer.tilewidth)
    32
    >>> print(layer.weather)
    'sunny'


Tiles are the exception here, and must be accessed through "getTileProperties"
and are regular Python dictionaries:

    >>> tile = tiledmap.getTileProperties(x, y, layer)
    >>> tile["name"]
    'CobbleStone'

"""

from itertools import chain


# internal flags
FLIP_X = 1
FLIP_Y = 2


# Tiled gid flags
GID_FLIP_X = 1<<31
GID_FLIP_Y = 1<<30


class TiledElement(object):
    pass

class TiledMap(TiledElement):
    """
    not really useful unless "loaded"  ie: don't instance directly.
    see the pygame loader for inspiration
    """

    def __init__(self):
        TiledElement.__init__(self)
        self.layers = []            # list of all layer types (tile layers + object layers)
        self.tilesets = []          # list of TiledTileset objects
        self.tilelayers   = []      # list of TiledLayer objects
        self.objectgroups = []      # list of TiledObjectGroup objects
        self.tile_properties = {}   # dict of tiles that have additional metadata (properties)
        self.filename = None

        # this is a work around to tiled's strange way of storing gid's
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
            msg = "Coords: ({0},{1}) in layer {2} is invalid.".format(x, y, layer)
            raise Exception(msg)

        else:
            try:
                return self.images[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}/{4}.".format(x, y, layer, gid, len(self.images))
                raise Exception(msg)

    def getTileGID(self, x, y, layer):
        """
        return GID of a tile in this location
        x and y must be integers and are in tile coordinates, not pixel
        """

        try:
            return self.tilelayers[layer].data[y][x]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid.".format(x, y, layer)
            raise Exception(msg)

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

        useful if you don't want to repeatedly call get_tile_image
        probably not the most efficient way of doing this, but oh well.
        """

        raise NotImplementedError

    def getObjects(self):
        """
        Return iterator all of the objects associated with this map
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
            msg = "Coords: ({0},{1}) in layer {2} is invalid.".format(x, y, layer)
            raise Exception(msg)

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invaid GID: {3}/{4}.".format(x, y, layer, gid, len(self.images))
                raise Exception(msg)

    def getTilePropertiesByGID(self, gid):
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

# the following classes get their attributes filled in with the loader

class TiledTileset(TiledElement):
    def __init__(self):
        TiledElement.__init__(self)

        # defaults from the specification
        self.firstgid = 0
        self.lastgid = 0
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0

class TiledLayer(TiledElement):
    def __init__(self):
        TiledElement.__init__(self)
        self.data = None

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = 1

class TiledObjectGroup(TiledElement):
    def __init__(self):
        TiledElement.__init__(self)
        self.objects = []

        # defaults from the specification
        self.name = None

class TiledObject(TiledElement):
    __slots__ = ['name', 'type', 'x', 'y', 'width', 'height', 'gid']

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


def load_tmx(filename):
    """
    Utility function to parse a Tiled TMX and return a usable object.
    Images will not be loaded, so probably not useful to call this directly

    See the load_pygame func for an idea of what to do
    """

    from xml.dom.minidom import parse
    from itertools import tee, islice, chain
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

    def pairwise(iterable):
        # return a list as a sequence of pairs
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    def group(l, n):
        # return a list as a sequence of n tuples
        return zip(*[islice(l, i, None, n) for i in range(n)])

    def parse_properties(node):
        """
        parse a node and return a dict that represents a tiled "property"
        """

        d = {}

        for child in node.childNodes:
            if child.nodeName == "properties":
                for subnode in child.getElementsByTagName("property"):
                    # the "properties" from tiled's tmx have an annoying
                    # quality that "name" and "value" is included as part of it.
                    # so we mangle it to get that stuff out.
                    d.update(dict(pairwise([ str(i.value) for i in list(subnode.attributes.values()) ])))

        return d

    def get_properties(node):
        """
        parses a node and returns a dict that contains the data from the node's
        attributes and any data from "property" elements as well.
        """

        d = {}

        # get tag attributes
        d.update(get_attributes(node))

        # get vlues of the properties element, if any
        d.update(parse_properties(node))

        return d

    def set_properties(obj, node):
        """
        read the xml attributes and tiled "properties" from a xml node and fill in
        the values into an object's dictionary
        """

        [ setattr(obj, k, v) for k,v in list(get_properties(node).items()) ]

    def get_attributes(node):
        """
        get the attributes from a node and fix them to the correct type
        """

        d = defaultdict(lambda:None)

        for k, v in list(node.attributes.items()):
            k = str(k)
            d[k] = types[k](v)

        return d

    def decode_gid(raw_gid):
        # gids are encoded with extra information
        # as of 0.7.0 it determines if the tile should be flipped when rendered

        flags = 0
        if raw_gid & GID_FLIP_X == GID_FLIP_X: flags += FLIP_X
        if raw_gid & GID_FLIP_Y == GID_FLIP_Y: flags += FLIP_Y
        gid = raw_gid & ~(GID_FLIP_X | GID_FLIP_Y)

        return gid, flags


    def parse_map(node):
        """
        parse a map node from a tiled tmx file
        return a tiledmap
        """

        tiledmap = TiledMap()
        tiledmap.filename = filename
        set_properties(tiledmap, map_node)

        for node in map_node.getElementsByTagName("tileset"):
            t, tiles = parse_tileset(node)
            tiledmap.tilesets.append(t)
            tiledmap.tile_properties.update(tiles)

        for node in dom.getElementsByTagName("layer"):
            l = parse_layer(tiledmap.tilesets, node)
            tiledmap.tilelayers.append(l)
            tiledmap.layers.append(l)

        for node in dom.getElementsByTagName("objectgroup"):
            o = parse_objectgroup(node)
            tiledmap.objectgroups.append(o)
            tiledmap.layers.append(o)

        return tiledmap


    def parse_tileset(node, firstgid=None):
        """
        parse a tileset element and return a tileset object and properties for tiles as a dict
        """

        tileset = TiledTileset()
        set_properties(tileset, node)
        tiles = {}

        if firstgid != None:
            tileset.firstgid = firstgid

        # since tile objects probably don't have a lot of metadata,
        # we store it separately from the class itself
        for child in node.childNodes:
            if child.nodeName == "tile":
                p = get_properties(child)
                gid = p["id"] + tileset.firstgid
                del p["id"]
                tiles[gid] = p

        # check for tiled "external tilesets"
        if hasattr(tileset, "source"):
            if tileset.source[-4:].lower() == ".tsx":
                try:
                    # we need to mangle the path some because tiled stores relative paths
                    path = os.path.join(os.path.dirname(filename), tileset.source)
                    tsx = parse(path)
                except IOError:
                    raise IOError("Cannot load external tileset: " + path)

                tileset_node = tsx.getElementsByTagName("tileset")[0]
                tileset, tiles = parse_tileset(tileset_node, tileset.firstgid)
            else:
                raise Exception("Found external tileset, but cannot handle type: " + tileset.source)

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
        parse a layer element and return a layer object

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
            from base64 import b64decode
            data = b64decode(bytes(data_node.lastChild.nodeValue, 'ascii'))

        elif attr["encoding"] == "csv":
            next_gid = map(int, "".join([line.strip() for line in data_node.lastChild.nodeValue]).split(","))

        elif not attr["encoding"] is None:
            raise Exception("TMX encoding type: " + str(attr["encoding"]) + " is not supported.")

        if attr["compression"] == "gzip":
            from io import BytesIO
            import gzip
            with gzip.GzipFile(fileobj=BytesIO(data)) as fh:
                data = fh.read()

        elif not attr["compression"] is None:
            raise Exception("TMX compression type: " + str(attr["compression"]) + " is not supported.")

        # if data is None, then it was not decoded or decompressed, so
        # we assume here that it is going to be a bunch of tile elements
        if attr["encoding"] == next_gid is None:
            def get_children(parent):
                for child in parent.getElementsByTagName("tile"):
                    yield int(child.getAttribute("gid"))

            next_gid = get_children(data_node)

        elif not data is None:
            # cast the data as a list of 32-bit integers
            def u(i): return unpack("<L", bytes(i))[0]
            next_gid = map(u, group(data, 4))

        gids = [ i.firstgid for i in tilesets ]

        # fill up our 2D array of gids.
        for y in range(layer.height):

            # store as 16-bit ints, since we will never use enough tiles to fill a 32-bit int
            layer.data.append(array.array("H"))

            for x in range(layer.width):
                gid, flags = decode_gid(next(next_gid))
                if not flags == 0: layer.flipped_tiles.append((x, y, gid, flags))
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


    # open and read our TMX (which is really just xml)
    dom = parse(filename)
    map_node =  dom.getElementsByTagName("map")[0]
    return parse_map(map_node)


def load_pygame(filename):
    """
    load a tiled TMX map for use with pygame
    """

    from pygame import Surface
    import pygame, os

    tiledmap = load_tmx(filename)

    # cache will find duplicate tiles to reduce memory usage
    # mostly this is a problem in the blank areas of a tilemap
    cache = {}

    # just a precaution to make sure tileset images are added in the correct order
    for firstgid, t in sorted([ (t.firstgid, t) for t in tiledmap.tilesets ]):
        path = os.path.join(os.path.dirname(tiledmap.filename), t.source)

        image = pygame.image.load(path)

        w, h = image.get_rect().size

        tile_size = (t.tilewidth, t.tileheight)

        # some tileset images may be slightly larger than the tiles area
        # ie: may include a banner, copyright, etc.  this compensates for that
        for y in range(0, int(h / t.tileheight) * t.tileheight, t.tileheight):
            for x in range(0, int(w / t.tilewidth) * t.tilewidth, t.tilewidth):

                # somewhat handle transparency, though colorkey handling is not tested
                if t.trans is None:
                    tile = Surface(tile_size, pygame.SRCALPHA)
                else:
                    tile = Surface(tile_size)

                # blit the smaller portion onto a new image from the larger one
                tile.blit(image, (0,0), ((x, y), tile_size))

                # make a unique id for this image, not sure if this is the best way, but it works
                key = pygame.image.tostring(tile, "RGBA")

                # make sure we don't have a duplicate tile
                try:
                    tile = cache[key]
                except KeyError:
                    if t.trans is None:
                        tile = tile.convert_alpha()
                    else:
                        tile = tile.convert()
                        tile.set_colorkey(t.trans)

                    # update the cache
                    cache[key] = tile

                tiledmap.images.append(tile)

    # correctly handle transformed tiles.  currently flipped tiles
    # work by creating a new gid for the flipped tile and changing the gid
    # in the layer to the new gid.
    for layer in tiledmap.tilelayers:
        for x, y, gid, trans in layer.flipped_tiles:
            fx = trans & FLIP_X == FLIP_X
            fy = trans & FLIP_Y == FLIP_Y

            tile = pygame.transform.flip(tiledmap.images[gid], fx, fy)
            tiledmap.images.append(tile)

            # change the original gid in the layer data to the new gid
            layer.data[y][x] = len(tiledmap.images) - 1

        del layer.flipped_tiles
    del cache

    return tiledmap

if __name__ == '__main__':
    print('[tmxloader] starting built-in test')
    load_tmx("../resources/maps/village.tmx")
