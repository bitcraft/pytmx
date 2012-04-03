from pygame import Rect


def simplify(all_points, tilewidth, tileheight):
    """
    klugde:

    "A kludge (or kluge) is a workaround, a quick-and-dirty solution,
    a clumsy or inelegant, yet effective, solution to a problem, typically
    using parts that are cobbled together."

    -- wikipedia
   
    turn a list of points into a rects 
    adjacent rects will be combined.

    plain english:
        the input list must be a a list of tuples that represent
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
    but i haven't found that it is excessively bad.  certainly much better than
    making a list of rects, one for each tile on the map!

    """

    def pick_rect(points, rects):
        ox, oy = sorted([ (sum(p), p) for p in points ])[0][1]
        x = ox
        y = oy
        ex = None            

        while 1:
            x += 1
            if not (x, y) in points:
                if ex == None:
                    ex = x - 1

                if ((ox, y+1) in points):
                    if x == ex + 1 :
                        y += 1
                        x = ox

                    else:
                        y -= 1
                        break
                else:
                    if x <= ex: y-= 1
                    break

        c_rect = Rect(ox*tilewidth,oy*tileheight,\
                     (ex-ox+1)*tilewidth,(y-oy+1)*tileheight)

        rects.append(c_rect)

        rect = Rect(ox,oy,ex-ox+1,y-oy+1)
        kill = [ p for p in points if rect.collidepoint(p) ]
        [ points.remove(i) for i in kill ]

        if points:
            pick_rect(points, rects)

    rect_list = []
    while all_points:
        pick_rect(all_points, rect_list)

    return rect_list

