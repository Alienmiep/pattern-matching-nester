from itertools import product

from shapely.geometry import Polygon
from shapely.affinity import translate

import helper
from helper import EdgePair

a_poly = Polygon([(9, 5), (8, 8), (5, 6)])          # static, both anti-clockwise
b_poly_untranslated = Polygon([(14, 6), (20, 6), (22, 12), (16, 10)])  # orbiting
# TODO potentially a problem, because GarmentCode parts are defined clockwise

# 1. setup
# TODO more advanced version where you give a reference point and then try to find a touching, non-intersecting position for b_poly
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
    # TODO this also "fires" if the polygons touch in two points


# 2. orbiting
# 2a) detection of touching edges

# test each edge of A against each edge of B
# store these touching pairs, along with the position of the touching vertex
# at the current step, this should leave us with 4 pairs, even in the case of identical edges

edges_poly_a = helper.incident_edges(a_poly, shared_point)
edges_poly_b = helper.incident_edges(b_poly, shared_point)

combinations = list(product(edges_poly_a, edges_poly_b))

# these edge pairs can fall into three different cases:
# (1) both touch in a vertex (like a V)
# (2) orbiting edge touches middle of stationary edge (like a T)
# (3) stationary edge touches the middle of orbiting edge (also like a T)

touching_pairs = []
for edge_pair in combinations:
    edge_case = helper.classify_edge_pair(edge_pair)
    touching_pairs.append(EdgePair(edge_pair[0], edge_pair[1], shared_point, edge_case))


# 2b) create potential translation vectors
# create translation vectors from these pairs
# if a B-edge is used, reverse direction

# the three cases have to be handled differently:
# (2) touching point -> stationary edge's end vertex
# (3) touching point -> orbiting edge's end vertex AND reverse direction
# (1) a little more complicated... (this is also the case that we start out with)

potential_translation_vectors = []
for pair in touching_pairs:
    match pair.edge_case:
        case 1:
            translation = helper.translation_vector_from_edge_pair(pair)
            if translation and translation not in potential_translation_vectors:
                potential_translation_vectors.append(translation)
        case 2:
            potential_translation_vectors.append(helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_a.coords[1]))
        case 3:
            translation = helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_a.coords[1])
            potential_translation_vectors.append((-translation[0], -translation[1]))
        case _:
            raise Exception("Invalid edge case")

print(potential_translation_vectors)


# 2c) find feasible translation
# choose a translation vector that doesn't immediately cause an intersection :)
# consult touching edge pairs list to find it
# each of these pairs defines an angular range within which a translation vector is allowed
# and the candidate translation vector has to fit into all of them

# case (1) feasible range should be angle between the vectors + 180°
# cases (2) and (3) need the "correct" 180°

feasible_translation_vectors = []
for translation_vector in potential_translation_vectors:
    is_feasible = True
    for pair in touching_pairs:
        is_feasible = is_feasible and helper.is_in_feasible_range(translation_vector, pair)
    if is_feasible:
        feasible_translation_vectors.append(translation_vector)

print(feasible_translation_vectors)


# 2d) trim feasible translation
# 2e) apply feasible translation




# TODO allow for arbitrary reference point on B
# - for which we need to ensure that it doesn't intersect with A (so choose correct vertex of A)
