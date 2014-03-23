from itertools import chain, product, islice
from collections import defaultdict
from xml.etree import ElementTree
from .constants import *



__all__ = ['TiledMap', 'TiledTileset', 'TiledTileLayer', 'TiledObject', 'TiledObjectGroup', 'TiledImageLayer']


def decode_gid(raw_gid):
    # gids are encoded with extra information
    # as of 0.7.0 it determines if the tile should be flipped when rendered
    # as of 0.8.0 bit 30 determines if GID is rotated

    flags = 0
    if raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX: flags += TRANS_FLIPX
    if raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY: flags += TRANS_FLIPY
    if raw_gid & GID_TRANS_ROT == GID_TRANS_ROT: flags += TRANS_ROT
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)

    return gid, flags


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
        if text == "false":  return False
        if text == "no":     return False
    except:
        pass

    raise ValueError

# used to change the unicode string returned from xml to proper python variable types.
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


def parse_properties(node):
    """
    parse a node and return a dict that represents a tiled "property"

    the "properties" from tiled's tmx have an annoying quality that "name"
    and "value" is included. here we mangle it to get that junk out.
    """
    d = {}
    for child in node.findall('properties'):
        for subnode in child.findall('property'):
            d[subnode.get('name')] = subnode.get('value')
    return d


class TiledElement:
    def set_properties(self, node):
        """
        read the xml attributes and tiled "properties" from a xml node and fill
        in the values into the object's dictionary.  Names will be checked to
        make sure that they do not conflict with reserved names.
        """
        # set the attributes reserved for tiled
        [setattr(self, k, types[str(k)](v)) for (k, v) in node.items()]

        # set the attributes that are derived from tiled 'properties'
        for k, v in parse_properties(node).items():
            if k in self.reserved:
                msg = '{0} "{1}" has a property called "{2}"'
                print(msg.format(self.__class__.__name__, self.name, k, self.__class__.__name__))
                msg = "This name is reserved for {0} objects and cannot be used."
                print(msg.format(self.__class__.__name__))
                print("Please change the name in Tiled and try again.")
                raise ValueError
            setattr(self, k, types[str(k)](v))

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.name)


class TiledMap(TiledElement):
    """
    Contains the layers, objects, and images from a Tiled TMX map
    """
    reserved = "version orientation width height tilewidth tileheight properties tileset layer objectgroup".split()

    def __init__(self, filename=None):
        self.layers = []           # list of all layers in proper order
        self.tilesets = []         # list of TiledTileset objects
        self.objectgroups = []     # list of TiledObjectGroup objects
        self.tile_properties = {}  # dict of tiles that have metadata
        self.filename = filename

        self.layernames = {}

        # only used tiles are actually loaded, so there will be a difference
        # between the GIDs in the Tiled map data (tmx) and the data in this
        # object and the layers.  This dictionary keeps track of that difference.
        self.gidmap = defaultdict(list)
        self.imagemap = {}  # mapping of gid and trans flags to real gids
        self.maxgid = 1

        # should be filled in by a loader function
        self.images = []

        # defaults from the TMX specification
        self.version = 0.0
        self.orientation = None
        self.width = 0       # width of map in tiles
        self.height = 0      # height of map in tiles
        self.tilewidth = 0   # width of a tile in pixels
        self.tileheight = 0  # height of a tile in pixels
        self.background_color = None

        if filename:
            self.load()

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.filename)

    def draw_iterator(self):
        """
        return an iterator of all the visible map elements for drawing

        meant to be quick, so some internal functions are duplicated here

        incomplete
        """
        # TODO: need some optimizations
        for layer in self.layers:
            if isinstance(layer, TiledTileLayer):
                for tile in layer:
                    x, y, gid = tile
                    yield x, y, self.images[gid]

    def get_tile_image(self, x, y, layer):
        """
        return the tile image for this location
        x and y must be integers and are in tile coordinates, not pixel
        x, y, and layer must be positive numbers

        return value will be 0 if there is no tile with that location.
        exception will be thrown is coordinates are illegal
        """
        try:
            assert(x >= 0 and y >= 0)
        except AssertionError:
            raise ValueError

        try:
            layer = self.layers[layer]
        except TypeError:
            assert(isinstance(layer, TiledTileLayer))
        except IndexError:
            raise ValueError

        try:
            gid = layer.data[y][x]
        except (IndexError, ValueError):
            raise ValueError
        except TypeError:
            msg = "Tiles must be specified in integers."
            print(msg)
            raise TypeError

        else:
            return self.get_tile_image_by_gid(gid)

    def get_tile_image_by_gid(self, gid):
        try:
            assert(gid >= 0)
            return self.images[gid]
        except (IndexError, ValueError, AssertionError):
            msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
            print(msg.format(x, y, layer, gid))
            raise TypeError

    def get_tile_gid(self, x, y, layer):
        """
        return GID of a tile in this location
        x and y must be integers and are in tile coordinates, not pixel
        x, y, and layer must be positive numbers
        """
        try:
            assert(x >= 0 and y >= 0 and layer >= 0)
        except AssertionError:
            raise ValueError

        try:
            return self.layers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid"
            print(msg.format(x, y, layer))
            raise ValueError

    def get_tile_images(self, r, layer):
        """
        return a group of tiles in an area
        expects a pygame rect or rect-like list/tuple

        useful if you don't want to repeatedly call getTileImage
        """
        raise NotImplementedError

    def get_tile_properties(self, x, y, layer):
        """
        return the properties for the tile, if any

        x and y must be integers and are in tile coordinates, not pixel
        x, y, and layer must be positive numbers

        returns a dict of there are properties, otherwise will be None
        """
        try:
            assert(x >= 0 and y >= 0 and layer >= 0)
        except AssertionError:
            raise ValueError

        try:
            gid = self.layers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid."
            print(msg.format(x, y, layer))
            raise Exception

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
                print(msg.format(x, y, layer, gid))
                raise Exception
            except KeyError:
                return None

    def get_layer_data(self, layer):
        """
        Return the data for a layer.
        layer must be positive

        Data is an array of arrays.

        >>> pos = data[y][x]
        """
        try:
            assert(layer >= 0)
            return self.layers[layer].data
        except (IndexError, AssertionError):
            msg = "Layer {0} does not exist."
            print(msg.format(layer))
            raise ValueError

    def get_tile_location(self, gid):
        """
        experimental way to find locations of a tile by the GID
        """
        p = product(range(self.width),
                    range(self.height),
                    range(len(self.layers)))

        return [(x, y, l) for (x, y, l) in p
                if self.layers[l].data[y][x] == gid]

    def get_tile_properties_by_gid(self, gid):
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

    def set_tile_properties(self, gid, d):
        """
        set the properties of a tile by GID.
        must use a standard python dict as d
        """
        try:
            self.tile_properties[gid] = d
        except KeyError:
            msg = "GID #{0} does not exist."
            print(msg.format(gid))
            raise ValueError

    def get_tile_properties_by_layer(self, layer):
        """
        Generator of tile properties in this tile layer
        """
        try:
            assert(int(layer) >= 0)
            layer = int(layer)
        except (TypeError, AssertionError):
            msg = "Layer must be a positive integer.  Got {0} instead."
            print(msg.format(type(layer)))
            raise ValueError

        p = product(range(self.width), range(self.height))
        layergids = set(self.layers[layer].data[y][x] for x, y in p)

        for gid in layergids:
            try:
                yield gid, self.tile_properties[gid]
            except KeyError:
                continue

    def register_gid(self, real_gid, flags=0):
        """
        used to manage the mapping of GIDs between the tmx file and the internal data

        return internal gid
        """
        if real_gid:
            try:
                return self.imagemap[(real_gid, flags)][0]
            except KeyError:
                gid = self.maxgid
                self.maxgid += 1
                self.imagemap[(real_gid, flags)] = (gid, flags)
                self.gidmap[real_gid].append((gid, flags))
                return gid

        else:
            return 0

    def map_gid(self, real_gid):
        """
        used to lookup a GID read from a TMX file's data
        """
        try:
            return self.gidmap[int(real_gid)]
        except KeyError:
            return None
        except TypeError:
            msg = "GIDs must be an integer"
            print(msg)
            raise TypeError

    def load(self):
        """
        parse a map node from a tiled tmx file
        """
        etree = ElementTree.parse(self.filename).getroot()
        self.set_properties(etree)

        # initialize the gid mapping
        self.imagemap[(0, 0)] = 0

        self.background_color = etree.get('backgroundcolor', self.background_color)

        # *** do not change this load order!  mapping errors will occur if changed ***
        for node in etree.findall('layer'):
            self.add_layer(TiledTileLayer(self, node))

        for node in etree.findall('imagelayer'):
            self.add_layer(TiledImageLayer(self, node))

        for node in etree.findall('objectgroup'):
            self.objectgroups.append(TiledObjectGroup(self, node))

        for node in etree.findall('tileset'):
            self.tilesets.append(TiledTileset(self, node))

        # "tile objects", objects with a GID, have need to have their
        # attributes set after the tileset is loaded, so this step must be performed last
        for o in self.objects:
            p = self.get_tile_properties_by_gid(o.gid)
            if p:
                o.__dict__.update(p)

    def add_layer(self, layer, position=None):
        """
        add a layer (TileTileLayer or TiledImageLayer) to the map
        """
        assert(isinstance(layer, (TiledTileLayer, TiledImageLayer)))

        if position is None:
            self.layers.append(layer)
        else:
            self.layers.insert(position, layer)

        self.layernames[layer.name] = layer

    def get_layer_by_name(self, name):
        """
        This is case-sensitive.
        """
        try:
            return self.layernames[name]
        except KeyError:
            msg = 'Layer "{0}" not found.'
            print(msg.format(name))
            raise ValueError

    def get_layer_order(self):
        """
        Return a list of the map's layers in drawing order.
        """
        return list(self.layers)

    def get_object_by_name(self, name):
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise ValueError

    @property
    def objects(self):
        """
        Return iterator of all the objects associated with this map
        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """
        Returns a list of TileLayer objects that are set 'visible'.

        Layers have their visibility set in Tiled.  Optionally, you can over-
        ride the Tiled visibility by creating a property named 'visible'.
        """
        return (l for l in self.layers if l.visible)


class TiledTileset(TiledElement):
    reserved = "firstgid source name tilewidth tileheight spacing margin image tile properties".split()

    def __init__(self, parent, node):
        self.parent = parent

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0
        self.tiles = {}

        # TODO: TileOffset

        self.parse(node)

    def parse(self, node):
        """
        parse a tileset element and return a tileset object and properties for
        tiles as a dict

        a bit of mangling is done here so that tilesets that have external
        TSX files appear the same as those that don't
        """
        import os

        # if true, then node references an external tileset
        source = node.get('source', None)
        if source:
            if source[-4:].lower() == ".tsx":

                # external tilesets don't save this, store it for later
                self.firstgid = int(node.get('firstgid'))

                # we need to mangle the path - tiled stores relative paths
                dirname = os.path.dirname(self.parent.filename)
                path = os.path.abspath(os.path.join(dirname, source))
                try:
                    node = ElementTree.parse(path).getroot()
                except IOError:
                    msg = "Cannot load external tileset: {0}"
                    print(msg.format(path))
                    raise Exception

            else:
                msg = "Found external tileset, but cannot handle type: {0}"
                print(msg.format(self.source))
                raise Exception

        self.set_properties(node)

        # since tile objects [probably] don't have a lot of metadata,
        # we store it separately in the parent (a TiledMap instance)
        for child in node.getiterator('tile'):
            real_gid = int(child.get("id"))
            p = parse_properties(child)
            p['width'] = self.tilewidth
            p['height'] = self.tileheight
            for gid, flags in self.parent.map_gid(real_gid + self.firstgid):
                self.parent.set_tile_properties(gid, p)

        image_node = node.find('image')
        self.source = image_node.get('source')
        self.trans = image_node.get("trans", None)


class TiledTileLayer(TiledElement):
    reserved = "name x y width height opacity properties data".split()

    def __init__(self, parent, node):
        self.parent = parent
        self.data = []

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = True
        self.height = 0
        self.width = 0

        self.parse(node)

    def __iter__(self):
        return self.iter_tiles()

    def iter_tiles(self):
        for y, x in product(range(self.height), range(self.width)):
            yield x, y, self.data[y][x]

    def parse(self, node):
        """
        parse a layer element
        """
        from struct import unpack
        import array

        def group(l, n):
            return zip(*(islice(l, i, None, n) for i in range(n)))

        self.set_properties(node)

        data = None
        next_gid = None

        data_node = node.find('data')

        encoding = data_node.get("encoding", None)
        if encoding == "base64":
            from base64 import b64decode
            data = b64decode(bytes(data_node.text.strip(), 'ascii'))

        elif encoding == "csv":
            next_gid = map(int, "".join(
                line.strip() for line in data_node.text.strip()
            ).split(","))

        elif encoding:
            msg = "TMX encoding type: {0} is not supported."
            print(msg.format(encoding))
            raise Exception

        compression = data_node.get("compression", None)
        if compression == "gzip":
            from io import BytesIO
            import gzip
            with gzip.GzipFile(fileobj=BytesIO(data)) as fh:
                data = fh.read()

        elif compression == "zlib":
            import zlib
            data = zlib.decompress(data)

        elif compression:
            msg = "TMX compression type: {0} is not supported."
            print(msg.format(compression))
            raise Exception

        # if data is None, then it was not decoded or decompressed, so
        # we assume here that it is going to be a bunch of tile elements
        # TODO: this will probably raise an exception if there are no tiles
        if encoding == next_gid is None:
            def get_children(parent):
                for child in parent.findall('tile'):
                    yield int(child.get('gid'))
            next_gid = get_children(data_node)

        elif data:
            # data is cast as 32-bit ints - this is the case after encoding or compression
            def u(i):
                return unpack("<L", bytes(i))[0]
            next_gid = map(u, group(data, 4))

        # may be a limitation for very detailed maps
        self.data = tuple(array.array("H") for i in range(self.height))
        for (y, x) in product(range(self.height), range(self.width)):
            self.data[y].append(self.parent.register_gid(*decode_gid(next(next_gid))))


class TiledObjectGroup(TiledElement, list):
    """
    Stores TiledObjects.  Supports any operation of a normal list.
    """
    reserved = "name color x y width height opacity object properties".split()

    def __init__(self, parent, node):
        self.parent = parent

        # defaults from the specification
        self.name = None
        self.color = None
        self.opacity = 1
        self.visible = 1

        self.parse(node)

    def parse(self, node):
        """
        parse a objectgroup element and return an object group
        """
        self.set_properties(node)

        for child in node.findall('object'):
            o = TiledObject(self.parent, child)
            self.append(o)


class TiledObject(TiledElement):
    reserved = "name type x y width height gid properties polygon polyline image".split()

    def __init__(self, parent, node):
        self.parent = parent

        # defaults from the specification
        self.name = None
        self.type = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.rotation = 0
        self.gid = 0
        self.visible = 1

        # TODO: ellipse

        self.parse(node)

    def parse(self, node):
        def read_points(text):
            """
            parse a text string of integer tuples and return [(x,...),...]
            """
            return tuple(tuple(map(int, i.split(','))) for i in text.split())

        self.set_properties(node)

        # correctly handle "tile objects" (object with gid set)
        if self.gid:
            self.gid = self.parent.register_gid(self.gid)

        polygon = node.find('polygon')
        if polygon is not None:
            x1 = x2 = y1 = y2 = 0
            self.points = read_points(polygon.get('points'))
            self.closed = True
            for x, y in self.points:
                if x < x1: x1 = x
                if x > x2: x2 = x
                if y < y1: y1 = y
                if y > y2: y2 = y
            self.width = abs(x1) + abs(x2)
            self.height = abs(y1) + abs(y2)

        polyline = node.find('polyline')
        if polyline is not None:
            x1 = x2 = y1 = y2 = 0
            self.points = read_points(polyline.get('points'))
            self.closed = False
            for x, y in self.points:
                if x < x1: x1 = x
                if x > x2: x2 = x
                if y < y1: y1 = y
                if y > y2: y2 = y
            self.width = abs(x1) + abs(x2)
            self.height = abs(y1) + abs(y2)


class TiledImageLayer(TiledElement):
    reserved = "source name width height opacity visible".split()

    def __init__(self, parent, node):
        self.parent = parent

        # unify the structure of layers
        self.gid = 0

        # defaults from the specification
        self.name = None
        self.opacity = 1
        self.visible = 1

        self.parse(node)

    def parse(self, node):
        """
        basic implementation of imagelayers.
        """
        self.set_properties(node)

        self.name = node.get('name', None)
        self.opacity = node.get('opacity', self.opacity)
        self.visible = node.get('visible', self.visible)

        image_node = node.find('image')
        self.source = image_node.get('source')
        self.trans = image_node.get('trans', None)

