from itertools import product

from shapely.geometry import Polygon
from shapely.affinity import translate
import matplotlib.pyplot as plt

import helper
from helper import EdgePair, INTERSECTION_PRECISION


a_poly = Polygon([(9, 5), (8, 8), (5, 6)])          # static, both anti-clockwise
a_poly_edges = helper.get_edges(a_poly)
b_poly_untranslated = Polygon([(14, 6), (16, 8), (20, 6), (22, 12), (16, 10)])  # orbiting
# TODO potentially a problem, because GarmentCode parts are defined clockwise

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
b_poly = translate(b_poly_untranslated, xoff=dx, yoff=dy)
b_poly_edges = helper.get_edges(b_poly)

if not a_poly.touches(b_poly):
    raise Exception("Polygons need to touch at the start")


nfp_is_closed_loop = False
while not nfp_is_closed_loop:
    shared_point = a_poly.intersection(b_poly, INTERSECTION_PRECISION)
    # TODO multipoint time :)

    if shared_point.geom_type in ('Polygon', 'MultiPolygon'):
        raise Exception("Polygons seem to overlap")
        # TODO see how this reacts to touching along an edge

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
                if translation and translation not in potential_translation_vectors:
                    potential_translation_vectors.append(translation)
                    potential_translation_vectors_edges.append(edge)
            case 2:
                potential_translation_vectors.append(helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_a.coords[1]))
                potential_translation_vectors_edges.append(("a", pair.edge_a_index))
            case 3:
                translation = helper.vector_from_points((pair.shared_vertex.x, pair.shared_vertex.y), pair.edge_b.coords[1])
                potential_translation_vectors.append((-translation[0], -translation[1]))
                potential_translation_vectors_edges.append(("b", pair.edge_b_index))
            case _:
                raise Exception("Invalid edge case")

    print("potential translation vectors: ", potential_translation_vectors)
    print("edges uses to generate them: ", potential_translation_vectors_edges)


    # 2c) find feasible translation
    # choose a translation vector that doesn't immediately cause an intersection :)
    # consult touching edge pairs list to find it
    # each of these pairs defines an angular range within which a translation vector is allowed
    # and the candidate translation vector has to fit into all of them

    # case (1) feasible range should be angle between the vectors + 180°
    # cases (2) and (3) need the "correct" 180°

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
    print("edges uses to generate them: ", feasible_translation_vectors_edges)
    print("NFP edges so far:", nfp_edges)

    if len(feasible_translation_vectors) > 1:
        # choose "the edge that is nearest (in edge order) to the previous move"
        # helper.decide_translation_vector(a_poly_edges, b_poly_edges, nfp_edges, feasible_translation_vectors, feasible_translation_vectors_edges)
        raise NotImplementedError("Multiple possible translation vectors are not supported yet")
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

    trimmed_translation_vector = helper.trim_translation_vector(b_poly, a_poly, untrimmed_translation, (shared_point.x, shared_point.y))
    trimmed_translation_vector = helper.trim_translation_vector(a_poly, b_poly, trimmed_translation_vector, (shared_point.x, shared_point.y), reverse=True)
    print("trimmed translation vector: ", trimmed_translation_vector)

    # 2e) apply feasible translation
    b_poly = translate(b_poly, xoff=trimmed_translation_vector[0], yoff=trimmed_translation_vector[1])
    b_poly_edges = helper.get_edges(b_poly)
    nfp.append((nfp[-1][0] + trimmed_translation_vector[0], nfp[-1][1] + trimmed_translation_vector[1]))
    nfp_edges.append(untrimmed_translation_edge)

    print("NFP: ", nfp)
    nfp_is_closed_loop = helper.is_closed_loop(nfp)

    if len(nfp) > 5:
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
