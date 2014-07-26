import logging
import six
from itertools import chain, product, islice
from collections import defaultdict
from xml.etree import ElementTree
from six.moves import zip, map
from .constants import *

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

__all__ = ['TiledMap', 'TiledTileset', 'TiledTileLayer', 'TiledObject',
           'TiledObjectGroup', 'TiledImageLayer']


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
        if text == "true":  return True
        if text == "yes":   return True
        if text == "false": return False
        if text == "no":    return False
    except:
        pass

    raise ValueError

# used to change the unicode string returned from xml to
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
    "trans": str,
    "id": int,
    "opacity": float,
    "visible": handle_bool,
    "encoding": str,
    "compression": str,
    "gid": int,
    "type": str,
    "x": float,
    "y": float,
    "value": str,
    "rotation": float,
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


class TiledElement(object):
    def __init__(self):
        self.properties = {}

    @classmethod
    def fromstring(cls, xml_string):
        """Return a TileElement object from a xml string

        :param xml_string: string containing xml data
        rtype: TiledElement instance
        """
        new = cls()
        node = ElementTree.fromstring(xml_string)
        new.parse(node)
        return new

    def set_properties(self, node):
        """
        read the xml attributes and tiled "properties" from a xml node and fill
        in the values into the object's dictionary.  Names will be checked to
        make sure that they do not conflict with reserved names.
        """
        # set the correct types
        [setattr(self, k, types[str(k)](v)) for (k, v) in node.items()]

        prop = parse_properties(node)

        # set the attributes that are derived from tiled 'properties'
        invalid = False
        for k, v in prop.items():
            if k in self.reserved:
                invalid = True
                msg = '{0} "{1}" has a property called "{2}"'
                print(msg.format(self.__class__.__name__, self.name, k,
                                 self.__class__.__name__))

        if invalid:
            msg = "This name(s) is reserved for {0} objects and cannot be used."
            print(msg.format(self.__class__.__name__))
            print("Please change the name(s) in Tiled and try again.")
            raise ValueError

        self.properties = prop

    def __getattr__(self, item):
        try:
            return self.properties[item]
        except KeyError:
            raise AttributeError

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.name)


class TiledMap(TiledElement):
    """Contains the layers, objects, and images from a Tiled TMX map

    This class is meant to handle most of the work you need to do to use a map.
    """
    reserved = "visible version orientation width height tilewidth \
                tileheight properties tileset layer objectgroup".split()

    def __init__(self, filename=None):
        """
        :param filename: filename of tiled map to load
        """
        TiledElement.__init__(self)
        self.layers = []           # list of all layers in proper order
        self.tilesets = []         # list of TiledTileset objects
        self.tile_properties = {}  # dict of tiles that have metadata
        self.filename = filename

        self.layernames = {}

        # only used tiles are actually loaded, so there will be a difference
        # between the GIDs in the Tiled map data (tmx) and the data in this
        # object and the layers.  This dictionary keeps track of that.
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

        # initialize the gid mapping
        self.imagemap[(0, 0)] = 0

        if filename:
            # Parse a map node from a tiled tmx file
            node = ElementTree.parse(self.filename).getroot()
            self.parse(node)

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.filename)

    # iterate over layers and objects in map
    def __iter__(self):
        return chain(self.layers, self.objects)

    def parse(self, node):
        """Parse a map from ElementTree xml node

        :param node: ElementTree xml node
        """
        self.set_properties(node)

        self.background_color = node.get('backgroundcolor',
                                         self.background_color)

        # ***        do not change this load order!      *** #
        # ***  gid mapping errors will occur if changed  *** #
        for subnode in node.findall('layer'):
            self.add_layer(TiledTileLayer(self, subnode))

        for subnode in node.findall('imagelayer'):
            self.add_layer(TiledImageLayer(self, subnode))

        for subnode in node.findall('objectgroup'):
            self.add_layer(TiledObjectGroup(self, subnode))

        for subnode in node.findall('tileset'):
            self.add_tileset(TiledTileset(self, subnode))

        # "tile objects", objects with a GID, have need to have their
        # attributes set after the tileset is loaded,
        # so this step must be performed last
        for o in self.objects:
            p = self.get_tile_properties_by_gid(o.gid)
            if p:
                o.properties.update(p)

    def get_tile_image(self, x, y, layer):
        """Return the tile image for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: pygame surface if found, otherwise 0
        """
        try:
            assert (x >= 0 and y >= 0)
        except AssertionError:
            raise ValueError

        try:
            layer = self.layers[layer]
        except IndexError:
            raise ValueError

        assert (isinstance(layer, TiledTileLayer))

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
        """Return the tile image for this location

        :param gid: GID of image
        :rtype: pygame surface if found, otherwise ValueError
        """
        try:
            assert (int(gid) >= 0)
            return self.images[gid]
        except (TypeError):
            msg = "GIDs must be expressed as a number.  Got: {0}"
            print(msg.format(gid))
            raise TypeError
        except (AssertionError, IndexError):
            msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
            print(msg.format(gid))
            raise ValueError

    def get_tile_gid(self, x, y, layer):
        """Return the tile image GID for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: pygame surface if found, otherwise ValueError
        """
        try:
            assert (x >= 0 and y >= 0 and layer >= 0)
        except AssertionError:
            raise ValueError

        try:
            return self.layers[int(layer)].data[int(y)][int(x)]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} is invalid"
            logger.debug(msg, (x, y, layer))
            raise ValueError

    def get_tile_images(self, r, layer):
        """Return iterator of images (not complete)

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: pygame surface if found, otherwise ValueError
        """
        raise NotImplementedError

    def get_tile_properties(self, x, y, layer):
        """Return the tile image GID for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: python dict if found, otherwise None
        """
        try:
            assert (x >= 0 and y >= 0 and layer >= 0)
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

    def get_tile_locations_by_gid(self, gid):
        """Search map for tile locations by the GID

        Not a fast operation

        :param gid: GID to be searched for
        :rtype: generator of tile locations
        """

        # use this func to make sure GID is valid
        try:
            self.get_tile_image_by_gid(gid)
        except:
            raise

        p = product(range(self.width),
                    range(self.height),
                    range(len(self.layers)))

        return ((x, y, l) for (x, y, l) in p if
                self.layers[l].data[y][x] == gid)

    def get_tile_properties_by_gid(self, gid):
        """Get the tile properties of a tile GID

        :param gid: GID
        :rtype: python dict if found, otherwise None
        """
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

    def set_tile_properties(self, gid, properties):
        """Set the tile properties of a tile GID

        :param gid: GID
        :param properties: python dict of properties for GID
        """
        self.tile_properties[gid] = properties

    def get_tile_properties_by_layer(self, layer):
        """Get the tile properties of each GID in layer

        :param layer: layer number
        rtype: iterator of (gid, properties) tuples for each tile gid with \
        properties in the tile layer
        """
        try:
            assert (int(layer) >= 0)
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

    def add_layer(self, layer):
        """Add a layer (TileTileLayer, TiledImageLayer, or TiledObjectGroup)

        :param layer: TileTileLayer, TiledImageLayer, TiledObjectGroup object
        """
        assert (
            isinstance(layer,
                       (TiledTileLayer, TiledImageLayer, TiledObjectGroup)))

        self.layers.append(layer)
        self.layernames[layer.name] = layer

    def add_tileset(self, tileset):
        """ Add a tileset to the map

        :param tileset: TiledTileset
        """
        assert (isinstance(tileset, TiledTileset))
        self.tilesets.append(tileset)

    def get_layer_by_name(self, name):
        """Return a layer by name

        :param name: Name of layer.  Case-sensitive.
        :rtype: Layer object if found, otherwise ValueError
        """
        try:
            return self.layernames[name]
        except KeyError:
            msg = 'Layer "{0}" not found.'
            print(msg.format(name))
            raise ValueError

    def get_object_by_name(self, name):
        """Find an object

        :param name: Name of object.  Case-sensitive.
        :rtype: Object if found, otherwise ValueError
        """
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise ValueError

    @property
    def objectgroups(self):
        """Return iterator of all object groups

        :rtype: Iterator
        """
        return (layer for layer in self.layers
                if isinstance(layer, TiledObjectGroup))

    @property
    def objects(self):
        """Return iterator of all the objects associated with this map

        :rtype: Iterator
        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """Return iterator of Layer objects that are set 'visible'

        :rtype: Iterator
        """
        return (l for l in self.layers if l.visible)

    @property
    def visible_tile_layers(self):
        """Return iterator of layer indexes that are set 'visible'

        :rtype: Iterator
        """
        return (i for (i, l) in enumerate(self.layers)
                if l.visible and isinstance(l, TiledTileLayer))

    @property
    def visible_object_groups(self):
        """Return iterator of object group indexes that are set 'visible'

        :rtype: Iterator
        """
        return (i for (i, l) in enumerate(self.layers)
                if l.visible and isinstance(l, TiledObjectGroup))

    def register_gid(self, tiled_gid, flags=0):
        """Used to manage the mapping of GIDs between the tmx and pytmx

        :param tiled_gid: GID that is found in TMX data
        rtype: GID that pytmx uses for the the GID passed
        """
        if tiled_gid:
            try:
                return self.imagemap[(tiled_gid, flags)][0]
            except KeyError:
                gid = self.maxgid
                self.maxgid += 1
                self.imagemap[(tiled_gid, flags)] = (gid, flags)
                self.gidmap[tiled_gid].append((gid, flags))
                return gid

        else:
            return 0

    def map_gid(self, tiled_gid):
        """Used to lookup a GID read from a TMX file's data

        :param tiled_gid: GID that is found in TMX data
        rtype: (GID, flags) that pytmx uses for the the GID passed

        returns None if the tile is not used in the map:
        """
        try:
            return self.gidmap[int(tiled_gid)]
        except KeyError:
            return None
        except TypeError:
            msg = "GIDs must be an integer"
            print(msg)
            raise TypeError


class TiledTileset(TiledElement):
    """ Represents a Tiled Tileset

    External tilesets are supported.  GID/ID's from Tiled are not guaranteed to
    be the same after loaded.
    """
    reserved = "visible firstgid source name tilewidth tileheight spacing \
                margin image tile properties".split()

    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0
        self.trans = None
        self.width = 0
        self.height = 0

        self.parse(node)

    def parse(self, node):
        """Parse a Tileset from ElementTree xml node

        A bit of mangling is done here so that tilesets that have external
        TSX files appear the same as those that don't

        :param node: ElementTree xml node
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

            # handle tiles that have their own image
            image = child.find('image')
            if image is None:
                p['width'] = self.tilewidth
                p['height'] = self.tileheight
            else:
                p['source'] = image.get('source')
                p['trans'] = image.get('trans', None)
                p['width'] = image.get('width')
                p['height'] = image.get('height')

            for gid, flags in self.parent.map_gid(real_gid + self.firstgid):
                self.parent.set_tile_properties(gid, p)

        # handle the optional 'tileoffset' node
        self.offset = node.find('tileoffset')
        if self.offset is None:
            self.offset = (0, 0)
        else:
            self.offset = (self.offset.get('x', 0), self.offset.get('y', 0))

        image_node = node.find('image')
        if image_node is not None:
            self.source = image_node.get('source')
            self.trans = image_node.get('trans', None)
            self.width = int(image_node.get('width'))
            self.height = int(image_node.get('height'))


class TiledTileLayer(TiledElement):
    """ Represents a TileLayer

    Iterate over the layer using the iterator protocol
    """
    reserved = "visible name x y width height opacity properties data".split()

    def __init__(self, parent, node):
        TiledElement.__init__(self)
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
        """Parse a Tile Layer from ElementTree xml node

        :param node: ElementTree xml node
        """
        import struct
        import array

        self.set_properties(node)

        data = None
        next_gid = None

        data_node = node.find('data')

        encoding = data_node.get('encoding', None)
        if encoding == 'base64':
            from base64 import b64decode
            data = b64decode(data_node.text.strip())

        elif encoding == 'csv':
            next_gid = map(int, "".join(
                line.strip() for line in data_node.text.strip()
            ).split(","))

        elif encoding:
            msg = 'TMX encoding type: {0} is not supported.'
            print(msg.format(encoding))
            raise Exception

        compression = data_node.get('compression', None)
        if compression == 'gzip':
            # py3 => bytes
            import gzip
            with gzip.GzipFile(fileobj=six.BytesIO(data)) as fh:
                data = fh.read()

        elif compression == 'zlib':
            import zlib
            data = zlib.decompress(data)

        elif compression:
            msg = 'TMX compression type: {0} is not supported.'
            print(msg.format(compression))
            raise Exception

        # if data is None, then it was not decoded or decompressed, so
        # we assume here that it is going to be a bunch of tile elements
        # TODO: this will/should raise an exception if there are no tiles
        if encoding == next_gid is None:
            def get_children(parent):
                for child in parent.findall('tile'):
                    yield int(child.get('gid'))
            next_gid = get_children(data_node)

        elif data:
            if type(data) == bytes:
                fmt = struct.Struct('<L')
                iterator = (data[i:i+4] for i in range(0, len(data), 4))
                next_gid = (fmt.unpack(i)[0] for i in iterator)
            else:
                print(type(data))
                raise Exception

        def init():
            return [0] * self.width
        reg = self.parent.register_gid

        # H (16-bit) may be a limitation for very detailed maps
        self.data = tuple(array.array('H', init()) for i in range(self.height))
        for (y, x) in product(range(self.height), range(self.width)):
            self.data[y][x] = reg(*decode_gid(next(next_gid)))


class TiledObject(TiledElement):
    """ Represents a any Tiled Object

    Supported types: Box, Ellispe, Tile Object, Polyline, Polygon
    """
    reserved = "visible name type x y width height gid properties polygon \
               polyline image".split()

    def __init__(self, parent, node):
        TiledElement.__init__(self)
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

        self.parse(node)

    def parse(self, node):
        """Parse an Object from ElementTree xml node

        :param node: ElementTree xml node
        """

        def read_points(text):
            """
            parse a text string of float tuples and return [(x,...),...]
            """
            return tuple(tuple(map(float, i.split(','))) for i in text.split())

        self.set_properties(node)

        # correctly handle "tile objects" (object with gid set)
        if self.gid:
            self.gid = self.parent.register_gid(self.gid)
            # tiled stores the origin of GID objects by the lower right corner
            # this is different for all other types, so i just adjust it here
            # so all types loaded with pytmx are uniform.
            # TODO: map the gid to the tileset to get the correct height
            self.y -= self.parent.tileheight

        points = None

        polygon = node.find('polygon')
        if polygon is not None:
            points = read_points(polygon.get('points'))
            self.closed = True

        polyline = node.find('polyline')
        if polyline is not None:
            points = read_points(polyline.get('points'))
            self.closed = False

        if points:
            x1 = x2 = y1 = y2 = 0
            for x, y in points:
                if x < x1: x1 = x
                if x > x2: x2 = x
                if y < y1: y1 = y
                if y > y2: y2 = y
            self.width = abs(x1) + abs(x2)
            self.height = abs(y1) + abs(y2)
            self.points = tuple(
                [(i[0] + self.x, i[1] + self.y) for i in points])


class TiledObjectGroup(TiledElement, list):
    """ Represents a Tiled ObjectGroup

    Supports any operation of a normal list.
    """
    reserved = "visible name color x y width height opacity object \
                properties".split()

    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent

        # defaults from the specification
        self.name = None
        self.color = None
        self.opacity = 1
        self.visible = 1

        self.parse(node)

    def parse(self, node):
        """Parse an Object Group from ElementTree xml node

        :param node: ElementTree xml node
        """
        self.set_properties(node)

        for child in node.findall('object'):
            o = TiledObject(self.parent, child)
            self.append(o)


class TiledImageLayer(TiledElement):
    """ Represents Tiled Image Layer

    The image associated with this layer will be loaded and assigned a GID.
    (pygame only)
    """
    reserved = "visible source name width height opacity visible".split()

    def __init__(self, parent, node):
        TiledElement.__init__(self)
        self.parent = parent
        self.source = None
        self.trans = None

        # unify the structure of layers
        self.gid = 0

        # defaults from the specification
        self.name = None
        self.opacity = 1
        self.visible = 1

        self.parse(node)

    def parse(self, node):
        """Parse an Image Layer from ElementTree xml node

        :param node: ElementTree xml node
        """
        self.set_properties(node)

        self.name = node.get('name', None)
        self.opacity = node.get('opacity', self.opacity)
        self.visible = node.get('visible', self.visible)

        image_node = node.find('image')
        self.source = image_node.get('source')
        self.trans = image_node.get('trans', None)
