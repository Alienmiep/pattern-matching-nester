from itertools import product
from shapely.geometry import Polygon, Point
from shapely.affinity import translate

a_poly = Polygon([(9, 5), (8, 8), (5, 6)])          # static, both anti-clockwise
b_poly_untranslated = Polygon([(14, 6), (20, 6), (22, 12), (16, 10)])  # orbiting

# 1. setup
# find lowest y point of A pt_a_ymin
pt_a_ymin = min(a_poly.exterior.coords, key=lambda p: p[1])

# find highest y point of B pt_b_ymax
pt_b_ymax = max(b_poly_untranslated.exterior.coords, key=lambda p: p[1])

# translate B with trans: B->A = pt_a_ymin - pt_b_ymax
dx = pt_a_ymin[0] - pt_b_ymax[0]
dy = pt_a_ymin[1] - pt_b_ymax[1]
b_poly = translate(b_poly_untranslated, xoff=dx, yoff=dy)

if not a_poly.touches(b_poly):
    raise Exception("Polygons need to touch at the start")

shared_point = a_poly.intersection(b_poly)

if not shared_point.geom_type == 'Point':
    raise Exception("Polygons seem to overlap")


# 2. orbiting
# 2a) detection of touching edges

# test each edge of A against each edge of B
# store these touching pairs, along with the position of the touching vertex
# at the current step, this should leave us with 4 pairs, even in the case of identical edges

def incident_edges(polygon: Polygon, point: Point):
    coords = list(polygon.exterior.coords)
    point_xy = (point.x, point.y)
    edges = []
    for i in range(len(coords) - 1):  # skip closing segment
        edge = (coords[i], coords[i + 1])
        if point_xy in edge:
            edges.append(edge)
    return edges

edges_poly_a = incident_edges(a_poly, shared_point)
edges_poly_b = incident_edges(b_poly, shared_point)

combinations = list(product(edges_poly_a, edges_poly_b))
print(combinations)


# these edge pairs can fall into three different cases:
# (1) both touch in a vertex (like a V)
# (2) orbiting edge touches middle of stationary edge (like a T)
# (3) stationary edge touches the middle of orbiting edge (also like a T)

# 2b) create potential translation vectors
# create translation vectors from these pairs
# if a B-edge is used, reverse direction

# the three cases have to be handled differently:
# (2) touching point -> stationary edge's end vertex
# (3) touching point -> orbiting edge's end vertex AND reverse direction
# (1) a little more complicated... (this is also the case that we start out with)

# find out
# - which part of the edges is touching and
# - whether orbiting edge b is left or right of stationary edge b (so by x value of non-touching point)
# then consult Table 1 as to which edge to use as a translation vector

# not all edge pairs will result in a translation vector and that is okay

# 2c) find feasible translation
# choose a translation vector that doesn't immediately cause an intersection :)
# consult touching edge pairs list to find it
# each of these pairs defines an angular range within which a translation vector is allowed
# and the candidate translation vector has to fit into all of them

# case (1) should be angle between the vectors + 180°
# cases (2) and (3) need the "correct" 180°

# 2d) trim feasible translation
# 2e) apply feasible translation




# TODO allow for arbitrary reference point on B
# - for which we need to ensure that it doesn't intersect with A (so choose correct vertex of A)
