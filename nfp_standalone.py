from itertools import product

from shapely import set_precision, orient_polygons, line_merge
from shapely.geometry import Polygon, Point
from shapely.affinity import translate
import matplotlib.pyplot as plt

import helper as helper
from helper import EdgePair, INTERSECTION_PRECISION

# a_poly = Polygon([(9, 5), (8, 8), (5, 6)])          # static, both anti-clockwise
# a_poly = Polygon([(73, 0), (73, 58.5), (0, 58.5), (0, 0), (73, 0)])
a_poly = orient_polygons(Polygon([(-22.5, 98.9), (-25.0, 98.9), (-25.0, 121.4), (-21.9, 122.2), (-19.7, 123.8), (-18.3, 125.9), (-17.5, 128.7), (-17.1, 132.1), (-17.0, 136.0), (-17.0, 140.5), (-17.0, 140.8), (-17.0, 141.1), (-17.0, 141.4), (-7.5, 143.1), (-5.8, 140.4), (-3.1, 138.6), (-0.0, 138.0), (3.1, 138.6), (5.8, 140.4), (7.5, 143.1), (17.0, 141.4), (17.0, 141.1), (17.0, 140.8), (17.0, 140.5), (17.0, 136.0), (17.1, 132.1), (17.5, 128.7), (18.3, 125.9), (19.7, 123.8), (21.9, 122.2), (25.0, 121.4), (25.0, 98.9), (22.5, 98.9), (0.0, 98.9)]))
a_poly_edges = helper.get_edges(a_poly)

# b_poly_untranslated = Polygon([(14, 6), (16, 8), (20, 6), (22, 12), (16, 10)])  # orbiting
# b_poly_untranslated = Polygon([(108.8, 111.0), (108.8, 169.5), (61.5, 169.5), (61.5, 111.0)])
b_poly_untranslated = orient_polygons(Polygon([(142.5, 140.3), (140.0, 141.0), (137.6, 142.2), (128.1, 140.5), (129.2, 136.2), (130.0, 132.4), (130.4, 129.1), (130.3, 126.3), (129.5, 123.9), (127.8, 122.0), (125.1, 120.5), (125.1, 98.0), (145.1, 98.0), (165.1, 98.0), (165.1, 120.5), (162.4, 122.0), (160.8, 123.9), (160.0, 126.3), (159.9, 129.1), (160.3, 132.4), (161.1, 136.2), (162.1, 140.5), (152.6, 142.2), (150.3, 141.0), (147.8, 140.3), (145.1, 140.0)]))

# 1. setup
# TODO more advanced version where you give a reference point and then try to find a touching, non-intersecting position for b_poly
# find lowest y point of A pt_a_ymin
pt_a_ymin = min(a_poly.exterior.coords, key=lambda p: p[1])
nfp = [pt_a_ymin]
nfp_edges = []

# find highest y point of B pt_b_ymax
pt_b_ymax = max(b_poly_untranslated.exterior.coords, key=lambda p: p[1])

# translate B with trans: B->A = pt_a_ymin - pt_b_ymax
dx = pt_a_ymin[0] - pt_b_ymax[0]
dy = pt_a_ymin[1] - pt_b_ymax[1]
b_poly = orient_polygons(translate(b_poly_untranslated, xoff=dx, yoff=dy))
b_poly_edges = helper.get_edges(b_poly)

if not a_poly.touches(b_poly):
    raise Exception("Polygons need to touch at the start")


nfp_is_closed_loop = False
while not nfp_is_closed_loop:
    shared_points = []
    line_intersection_flag = False
    intersection = helper.precision_aware_intersection(a_poly, b_poly)
    if intersection.is_empty:
        raise Exception("Polygons are not touching")

    if intersection.geom_type == "Point":
        shared_points = [intersection]
    elif intersection.geom_type == "MultiPoint":
        shared_points = list(intersection.geoms)
    elif intersection.geom_type in ["LineString", "MultiLineString"]:
        line_intersection_flag = True
        merged_linestring = line_merge(intersection)
        if merged_linestring.geom_type == "LineString":
            shared_points = [Point(merged_linestring.coords[0]), Point(merged_linestring.coords[-1])]
            linestring_intersection_length = merged_linestring.length
        elif merged_linestring.geom_type == "MultiLineString":
            linestring_intersection_length = 0
            for line in merged_linestring.geoms:
                shared_points.append(Point(line.coords[0]))
                shared_points.append(Point(line.coords[-1]))
    elif intersection.geom_type in ('Polygon', 'MultiPolygon'):
        raise Exception("Polygons seem to overlap")

    # 2. orbiting
    # 2a) detection of touching edges

    # test each edge of A against each edge of B
    # store these touching pairs, along with the position of the touching vertex
    # at the current step, this should leave us with 4 pairs, even in the case of identical edges

    combinations = {}
    for shared_point in shared_points:
        edges_poly_a = helper.incident_edges(a_poly, shared_point)
        edges_poly_b = helper.incident_edges(b_poly, shared_point)
        combinations[shared_point] = list(product(edges_poly_a, edges_poly_b))

    print("identified edge pair combinations: ", combinations)

    # these edge pairs can fall into three different cases:
    # (1) both touch in a vertex (like a V)
    # (2) orbiting edge touches middle of stationary edge (like a T)
    # (3) stationary edge touches the middle of orbiting edge (also like a T)

    touching_pairs = []
    for shared_point, edge_pair_list in combinations.items():
        for edge_pair in edge_pair_list:
            edge_case = helper.classify_edge_pair(edge_pair, shared_point)
            edge_a_index = helper.find_edge_index(a_poly_edges, edge_pair[0])
            edge_b_index = helper.find_edge_index(b_poly_edges, edge_pair[1])
            touching_pairs.append(EdgePair(edge_pair[0], edge_a_index, edge_pair[1], edge_b_index, shared_point, edge_case))

    # 2b) create potential translation vectors
    # create translation vectors from these pairs
    # if a B-edge is used, reverse direction

    # the three cases have to be handled differently:
    # (2) touching point -> stationary edge's end vertex
    # (3) touching point -> orbiting edge's end vertex AND reverse direction
    # (1) a little more complicated... (this is also the case that we start out with)

    potential_translation_vectors = []
    potential_translation_vectors_edges = []  # keep track of the edges used to generate them
    for pair in touching_pairs:
        match pair.edge_case:
            case 1:
                translation, edge = helper.translation_vector_from_edge_pair(pair)
            case 2:
                translation = helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_a.coords[1])
                edge = ("a", pair.edge_a_index)
            case 3:
                translation_wrong_direction = helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_b.coords[1])
                translation = (-translation_wrong_direction[0], -translation_wrong_direction[1])
                edge = ("b", pair.edge_b_index)
            case _:
                raise Exception("Invalid edge case")
        if translation and translation not in potential_translation_vectors and translation != (0, 0):
            potential_translation_vectors.append(translation)
            potential_translation_vectors_edges.append(edge)

    print("potential translation vectors: ", potential_translation_vectors)
    print("edges used to generate them: ", potential_translation_vectors_edges)

    potential_translation_vectors , potential_translation_vectors_edges= helper.filter_redundant_vectors(potential_translation_vectors, potential_translation_vectors_edges)
    print("potential translation vectors after filtering redundancies: ", potential_translation_vectors)
    print("edges used to generate them: ", potential_translation_vectors_edges)

    # 2c) find feasible translation
    # choose a translation vector that doesn't immediately cause an intersection :)
    # consult touching edge pairs list to find it
    # each of these pairs defines an angular range within which a translation vector is allowed
    # and the candidate translation vector has to fit into all of them

    feasible_translation_vectors = []
    feasible_translation_vectors_edges = []
    for index, translation_vector in enumerate(potential_translation_vectors):
        is_feasible = True
        for pair in touching_pairs:
            is_feasible = is_feasible and helper.is_in_feasible_range(translation_vector, pair)  # stops checking once an edge has been found not feasible
        if is_feasible:
            feasible_translation_vectors.append(translation_vector)
            feasible_translation_vectors_edges.append(potential_translation_vectors_edges[index])

    print("feasible translation vectors: ", feasible_translation_vectors)
    print("edges used to generate them: ", feasible_translation_vectors_edges)
    print("NFP edges so far:", nfp_edges)
    if line_intersection_flag and linestring_intersection_length:
        # cap the length of the translation vector to the length of the intersection
        feasible_translation_vectors = helper.cap_translation_vectors(feasible_translation_vectors, linestring_intersection_length)

    if len(feasible_translation_vectors) > 1:
        # when dealing with rectangular pieces, we might end up with a seemingly possible translation vector that can't be detected by the feasability check
        actually_feasible_vectors = []
        actually_feasible_vectors_edges = []
        if not line_intersection_flag:
            for index, candidate in enumerate(feasible_translation_vectors):
                b_poly_candidate = translate(b_poly, xoff=candidate[0], yoff=candidate[1])
                if not helper.precision_aware_intersection(a_poly, b_poly_candidate).is_empty:
                    actually_feasible_vectors.append(candidate)
                    actually_feasible_vectors_edges.append(feasible_translation_vectors_edges[index])
            if len(actually_feasible_vectors) > 1:
                # choose "the edge that is nearest (in edge order) to the previous move"
                # helper.decide_translation_vector(a_poly_edges, b_poly_edges, nfp_edges, feasible_translation_vectors, feasible_translation_vectors_edges)
                raise NotImplementedError("Multiple possible translation vectors are not supported yet")
            if not actually_feasible_vectors:
                raise Exception("No feasible translation vectors left after intersection (or lack thereof) check")
        else:
            for index, candidate in enumerate(feasible_translation_vectors):
                translation_vector_endpoint = (intersection.coords[1][0] + candidate[0], intersection.coords[1][1] + candidate[1])
                angle = helper.angle_from_points(intersection.coords[0], intersection.coords[1], translation_vector_endpoint)
                print(angle)
                if angle != 90.0 and angle != 270.0:
                    actually_feasible_vectors.append(candidate)
                    actually_feasible_vectors_edges.append(feasible_translation_vectors_edges[index])
            print("actually feasible: ", actually_feasible_vectors)
            if len(actually_feasible_vectors) > 1:
                raise NotImplementedError("Multiple possible translation vectors are not supported yet (line_intersection_flag is true)")
            if not actually_feasible_vectors:
                raise Exception("No feasible translation vectors left after 90° check")
        untrimmed_translation = actually_feasible_vectors[0]
        untrimmed_translation_edge = actually_feasible_vectors_edges[0]
    else:
        untrimmed_translation = feasible_translation_vectors[0]
        untrimmed_translation_edge = feasible_translation_vectors_edges[0]

    print("decided on translation vector: ", untrimmed_translation)
    print("made from edge: ", untrimmed_translation_edge)

    # 2d) trim feasible translation
    # for all points of B, apply the translation and see if (and where) it intersects
    # for all points of A, apply the translation "backwards" and see if (and where) it intersects
    # trim translation vector as you go
    # TODO this can be used to eliminate intersection tests

    trimmed_translation_vector = helper.trim_translation_vector(b_poly, a_poly, untrimmed_translation, shared_points)
    trimmed_translation_vector = helper.trim_translation_vector(a_poly, b_poly, trimmed_translation_vector, shared_points, reverse=True)
    print("trimmed translation vector: ", trimmed_translation_vector)

    if trimmed_translation_vector[0] == 0 and trimmed_translation_vector[1] == 0:
        raise Exception("Translation vector (0,0) is not allowed")

    # 2e) apply feasible translation
    b_poly_imprecise = translate(b_poly, xoff=trimmed_translation_vector[0], yoff=trimmed_translation_vector[1])
    b_poly = orient_polygons(set_precision(b_poly_imprecise, INTERSECTION_PRECISION))
    b_poly_edges = helper.get_edges(b_poly)
    nfp.append((nfp[-1][0] + trimmed_translation_vector[0], nfp[-1][1] + trimmed_translation_vector[1]))
    nfp_edges.append(untrimmed_translation_edge)

    print("NFP: ", nfp)
    nfp_is_closed_loop = helper.is_closed_loop(nfp)

    if len(nfp) > 100:  # safety mechanism
        nfp_is_closed_loop = True


# --- visualization! ---
def plot_polygon(ax, poly, color, label):
    x, y = poly.exterior.xy
    ax.fill(x, y, alpha=0.5, fc=color, ec='black', label=label)

# Set up the plot
fig, ax = plt.subplots()

# Plot polygons
plot_polygon(ax, a_poly, 'blue', 'A Polygon')
plot_polygon(ax, b_poly, 'green', 'B Polygon')

# Plot NFP points
nfp_x, nfp_y = zip(*nfp)
ax.plot(nfp_x, nfp_y, 'ro-', label='NFP Path')  # red points with lines

# Misc plot settings
ax.set_aspect('equal')
ax.legend()
ax.grid(True)
plt.title("Polygon NFP Visualization")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()


# TODO allow for arbitrary reference point on B
# - for which we need to ensure that it doesn't intersect with A (so choose correct vertex of A)
