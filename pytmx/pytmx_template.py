"""
This file was automatically generated during the pytmx build process.
Any changes to this will be lost if the build process is run again.
To make permanent changes, please edit the template and build again.
"""
from __future__ import division

import mason
import logging
from itertools import chain, product
from operator import attrgetter

logger = logging.getLogger(__name__)


class TiledElement(object):
    """ Base class for all pytmx types
    """


class TiledMap(TiledElement):
    """Contains the layers, objects, and images from a Tiled TMX map

    This class is meant to handle most of the work you need to do to use a map.

    All operations are reasonably safe and should raise informative errors.
    """

    # codegen: TilesetToken.__init__
        """ Create new TiledMap

        :type root: mason.MapToken

        :param filename: filename of tiled map to load
        :param image_loader: function that will load images (see below)
        :param invert_y: invert the y axis

        image_loader:
          this must be a reference to a function that will accept a tuple:
          (filename of image, bounding rect of tile in image, flags)
          the function must return a reference to to the tile.
        """
        # TiledElement.__init__(self, *args)

        # optional keyword arguments checked here
        # self.invert_y = kwargs.get('invert_y', True)

        # codegen: MapToken.attributes

        # pytmx embellishments
        self.properties = root.properties
        self.layers = list()  # all layers in proper order
        self.tilesets = list()
        self.tile_properties = dict()  # tiles that have properties
        self.layernames = dict()
        self.images = list()  # should be filled in by a loader function
        self.filename = None
        self.image_loader = None
        self.maxgid = 1

        # deconstruct the mason objects
        for token in root.layers:

            if isinstance(token, mason.TileToken):
                new_layer = TiledTileLayer(token.data)
            elif isinstance(token, mason.ObjectgroupToken):
                new_layer = TiledObjectGroup()
            elif isinstance(token, mason.ImagelayerToken):
                new_layer = TiledImageLayer()
            else:
                continue

            self.layers.append(new_layer)

    # def __repr__(self):
    #     return '<{0}: "{1}">'.format(self.__class__.__name__, self.filename)

    # iterate over layers and objects in map
    def __iter__(self):
        return chain(self.layers, self.objects)

    def get_tile_image(self, x, y, layer):
        """ Return the tile image for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: surface if found, otherwise 0
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
            logger.debug(msg)
            raise TypeError

        else:
            return self.get_tile_image_by_gid(gid)

    def get_tile_image_by_gid(self, gid):
        """ Return the tile image for this location

        :param gid: GID of image
        :rtype: surface if found, otherwise ValueError
        """
        try:
            assert (int(gid) >= 0)
            return self.images[gid]
        except TypeError:
            msg = "GIDs must be expressed as a number.  Got: {0}"
            logger.debug(msg.format(gid))
            raise TypeError
        except (AssertionError, IndexError):
            msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
            logger.debug(msg.format(gid))
            raise ValueError

    def get_tile_gid(self, x, y, layer):
        """ Return the tile image GID for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer: layer number
        :rtype: surface if found, otherwise ValueError
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

    def get_tile_properties(self, x, y, layer):
        """ Return the tile image GID for this location

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
            logger.debug(msg.format(x, y, layer))
            raise Exception

        else:
            try:
                return self.tile_properties[gid]
            except (IndexError, ValueError):
                msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
                logger.debug(msg.format(x, y, layer, gid))
                raise Exception
            except KeyError:
                return None

    def get_tile_locations_by_gid(self, gid):
        """ Search map for tile locations by the GID

        Return (int, int, int) tuples, where the layer is index of
        the visible tile layers.

        Note: Not a fast operation.  Cache results if used often.

        :param gid: GID to be searched for
        :rtype: generator of tile locations
        """
        for l in self.visible_tile_layers:
            for x, y, _gid in [i for i in self.layers[l].iter_data() if i[2] == gid]:
                yield x, y, l

    def get_tile_properties_by_gid(self, gid):
        """ Get the tile properties of a tile GID

        :param gid: GID
        :rtype: python dict if found, otherwise None
        """
        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

    def get_tile_properties_by_layer(self, layer):
        """ Get the tile properties of each GID in layer

        :param layer: layer number
        :rtype: iterator of (gid, properties) tuples
        """
        try:
            assert (int(layer) >= 0)
            layer = int(layer)
        except (TypeError, AssertionError):
            msg = "Layer must be a positive integer.  Got {0} instead."
            logger.debug(msg.format(type(layer)))
            raise ValueError

        p = product(range(self.width), range(self.height))
        layergids = set(self.layers[layer].data[y][x] for x, y in p)

        for gid in layergids:
            try:
                yield gid, self.tile_properties[gid]
            except KeyError:
                continue

    def get_layer_by_name(self, name):
        """Return a layer by name

        :param name: Name of layer.  Case-sensitive.
        :rtype: Layer object if found, otherwise ValueError
        """
        try:
            return self.layernames[name]
        except KeyError:
            msg = 'Layer "{0}" not found.'
            logger.debug(msg.format(name))
            raise ValueError

    def get_object_by_name(self, name):
        """ Find an object by name.

        :param name: Name of object.  Case-sensitive.
        :rtype: Object if found, otherwise ValueError
        """
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise ValueError

    def get_tileset_from_gid(self, gid):
        """ Return tileset that owns the gid

        Note: this is a slow operation, so if you are expecting to do this
              often, it would be worthwhile to cache the results of this.

        :param gid: gid of tile image
        :rtype: TiledTileset if found, otherwise ValueError
        """
        try:
            tiled_gid = self.tiledgidmap[gid]
        except KeyError:
            raise ValueError

        for tileset in sorted(self.tilesets, key=attrgetter('firstgid'),
                              reverse=True):
            if tiled_gid >= tileset.firstgid:
                return tileset

        raise ValueError

    @property
    def objectgroups(self):
        """Return iterator of ObjectGroup objects

        :rtype: Iterator
        """
        return (l for l in self.layers if isinstance(l, TiledObjectGroup))

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


class TiledTileset(TiledElement):
    """ Represents a Tiled Tileset

    External tilesets are supported.  GID/ID's from Tiled are not guaranteed to
    be the same after loaded.

    """
    # codegen: TilesetToken.__init__
    # codegen: TilesetToken.attributes


class TiledTileLayer(TiledElement):
    """ Represents a TileLayer

    To just get the tile images, use TiledTileLayer.tiles()
    """

    # codegen: LayerToken.__init__
    # codegen: LayerToken.attributes

    def __iter__(self):
        return self.iter_data()

    def iter_data(self):
        """ Iterate over layer data

        Yields X, Y, GID tuples for each tile in the layer

        :return: Generator
        """
        for y, row in enumerate(self.data):
            for x, gid in enumerate(row):
                yield x, y, gid

    def tiles(self):
        """ Iterate over tile images of this layer

        This is an optimised generator function that returns
        (tile_x, tile_y, tile_image) tuples,

        :rtype: Generator
        :return: (x, y, image) tuples
        """
        images = self.parent.images
        for x, y, gid in [i for i in self if i[2]]:
            yield x, y, images[gid]


class TiledObject(TiledElement):
    """ Represents a any Tiled Object

    Supported types: Box, Ellipse, Tile Object, Polyline, Polygon
    """

    # codegen: ObjectToken.__init__
    # codegen: ObjectToken.attributes

    @property
    def image(self):
        if self.gid:
            return self.parent.images[self.gid]
        return None


class TiledObjectGroup(TiledElement, list):
    """ Represents a Tiled ObjectGroup

    Supports any operation of a normal list.
    """
    # codegen: ObjectgroupToken.__init__
    # codegen: ObjectgroupToken.attributes


class TiledImageLayer(TiledElement):
    """ Represents Tiled Image Layer

    The image associated with this layer will be loaded and assigned a GID.
    """

    # codegen: ImagelayerToken.__init__
    # codegen: ImagelayerToken.attributes

    @property
    def image(self):
        if self.gid:
            return self.parent.images[self.gid]
        return None
