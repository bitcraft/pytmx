from itertools import product


def build_rects(tmxmap, layer, tileset=None, real_gid=None):
    """
    generate a set of non-overlapping rects that represents the distribution of the specified gid.

    useful for generating rects for use in collision detection
    """

    if isinstance(tileset, int):
        try:
            tileset = tmxmap.tilesets[tileset]
        except IndexError:
            msg = "Tileset #{0} not found in map {1}."
            print(msg.format(tileset, tmxmap))
            raise IndexError

    elif isinstance(tileset, str):
        try:
            tileset = [t for t in tmxmap.tilesets if t.name == tileset].pop()
        except IndexError:
            msg = "Tileset \"{0}\" not found in map {1}."
            print(msg.format(tileset, tmxmap))
            raise ValueError

    elif tileset:
        msg = "Tileset must be either a int or string. got: {0}"
        print(msg.format(type(tileset)))
        raise TypeError

    gid = None
    if real_gid:
        try:
            gid, flags = tmxmap.map_gid(real_gid)[0]
        except IndexError:
            msg = "GID #{0} not found"
            print(msg.format(real_gid))
            raise ValueError

    if isinstance(layer, int):
        layer_data = tmxmap.get_layer_data(layer)
    elif isinstance(layer, str):
        try:
            layer = [l for l in tmxmap.tilelayers if l.name == layer].pop()
            layer_data = layer.data
        except IndexError:
            msg = "Layer \"{0}\" not found in map {1}."
            print(msg.format(layer, tmxmap))
            raise ValueError

    p = product(range(tmxmap.width), range(tmxmap.height))
    if gid:
        points = [(x, y) for (x, y) in p if layer_data[y][x] == gid]
    else:
        points = [(x, y) for (x, y) in p if layer_data[y][x]]

    rects = simplify(points, tmxmap.tilewidth, tmxmap.tileheight)
    return rects


def simplify(all_points, tilewidth, tileheight):
    """
    kludge:

    "A kludge (or kluge) is a workaround, a quick-and-dirty solution,
    a clumsy or inelegant, yet effective, solution to a problem, typically
    using parts that are cobbled together."

    -- wikipedia

    turn a list of points into a rects
    adjacent rects will be combined.

    plain english:
        the input list must be a list of tuples that represent
        the areas to be combined into rects
        the rects will be blended together over solid groups

        so if data is something like:

        0 1 1 1 0 0 0
        0 1 1 0 0 0 0
        0 0 0 0 0 4 0
        0 0 0 0 0 4 0
        0 0 0 0 0 0 0
        0 0 1 1 1 1 1

        you'll have the 4 rects that mask the area like this:

        ..######......
        ..####........
        ..........##..
        ..........##..
        ..............
        ....##########

        pretty cool, right?

    there may be cases where the number of rectangles is not as low as possible,
    but I haven't found that it is excessively bad.  certainly much better than
    making a list of rects, one for each tile on the map!
    """
    from pygame import Rect


    def pick_rect(points, rects):
        ox, oy = sorted([(sum(p), p) for p in points])[0][1]
        x = ox
        y = oy
        ex = None

        while 1:
            x += 1
            if not (x, y) in points:
                if ex is None:
                    ex = x - 1

                if (ox, y + 1) in points:
                    if x == ex + 1:
                        y += 1
                        x = ox

                    else:
                        y -= 1
                        break
                else:
                    if x <= ex: y -= 1
                    break

        c_rect = Rect(ox * tilewidth, oy * tileheight,
                     (ex - ox + 1) * tilewidth, (y - oy + 1) * tileheight)

        rects.append(c_rect)

        rect = Rect(ox, oy, ex - ox + 1, y - oy + 1)
        kill = [p for p in points if rect.collidepoint(p)]
        [points.remove(i) for i in kill]

        if points:
            pick_rect(points, rects)

    rect_list = []
    while all_points:
        pick_rect(all_points, rect_list)

    return rect_list


__all__ = ['decode_gid', 'build_rects', 'simplify', 'handle_bool']