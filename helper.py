import math
from dataclasses import dataclass

from shapely import set_precision
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import nearest_points

INTERSECTION_PRECISION = 0.01
NO_OF_ROUNDING_DIGITS = 2

@dataclass
class EdgePair:
    edge_a: LineString
    edge_a_index: int
    edge_b: LineString
    edge_b_index: int
    shared_vertex: Point
    edge_case: int


def incident_edges(polygon: Polygon, point: Point) -> list:
    coords = list(polygon.exterior.coords)
    edges = []
    for i in range(len(coords) - 1):  # skip closing segment
        edge = LineString([coords[i], coords[i + 1]])
        if edge.distance(point) <= INTERSECTION_PRECISION:  # Point-Edge intersection is too flaky, unfortunately
            edges.append(edge)
    return edges


def classify_edge_pair(edge_pair: tuple, shared_point: Point) -> int:
    precise_edge_a = set_precision(edge_pair[0], INTERSECTION_PRECISION)
    precise_edge_b = set_precision(edge_pair[1], INTERSECTION_PRECISION)
    endpoints_a = {precise_edge_a.coords[0], precise_edge_a.coords[-1]}
    endpoints_b = {precise_edge_b.coords[0], precise_edge_b.coords[-1]}

    # check if they share an endpoint (case (1))
    common_endpoint = endpoints_a & endpoints_b
    if common_endpoint:
        if len(common_endpoint) == 2:
            return 1

        endpoint = common_endpoint.pop()
        if endpoint == shared_point.coords[0]:
            return 1

        # but! if the non-shared endpoint of one edge touches the middle of the other edge, the case actually depends on the shared_point we're looking at
        print("handling more complex case")
        return 2 if endpoint in endpoints_b else 3

    inter = precision_aware_intersection(edge_pair[0], edge_pair[1])
    if isinstance(inter, Point) and tuple(inter.coords)[0] not in endpoints_a:
        return 2

    elif isinstance(inter, Point) and tuple(inter.coords)[0] not in endpoints_b:
        return 3

    return 0


def translation_vector_from_edge_pair(pair: EdgePair) -> tuple:
    # 1. find out whether the touching vertex is start of end of a/b
    edge_a_part = "start" if Point(pair.edge_a.coords[0]) == pair.shared_vertex else "end"
    edge_b_part = "start" if Point(pair.edge_b.coords[0]) == pair.shared_vertex else "end"

    # 2. find out if edge b is left or right (or parallel) of edge a
    relative_position = is_left_or_right(pair.edge_a, pair.edge_b)

    # 3. get case and return translation vector (or None, that's fine too)
    match(get_edge_case(edge_a_part, edge_b_part, relative_position)):
        case 1 | 6 | 8:
            return vector_from_points(pair.edge_b.coords[1], pair.edge_b.coords[0]), ("b", pair.edge_b_index)  # reverse direction here
        case 2 | 4:
            return vector_from_points(pair.edge_a.coords[0], pair.edge_a.coords[1]), ("a", pair.edge_a_index)
        case 3 | 5 | 7:
            return None, None
        case _:
            raise Exception("Edge pair case could not be resolved")


def is_left_or_right(edge_a_imprecise: LineString, edge_b_imprecise: LineString) -> str:
    edge_a = set_precision(edge_a_imprecise, INTERSECTION_PRECISION)
    edge_b = set_precision(edge_b_imprecise, INTERSECTION_PRECISION)
    if list(edge_a.coords) == list(edge_b.coords) or list(edge_a.coords) == list(edge_b.coords)[::-1]:
        return "parallel"

    # point A: non-touching point of edge_b
    # point B: start of edge_a
    # point C: end of edge_a
    point_a = edge_b.coords[0] if edge_b.coords[0] not in list(edge_a.coords) else edge_b.coords[1]
    point_b = edge_a.coords[0]
    point_c = edge_a.coords[1]
    angle = angle_from_points(point_a, point_b, point_c)
    if angle > 180:
        return "left"
    if angle == 180 or (angle <= 0.5 and angle >= -0.5):
        return "parallel"
    return "right"


def get_edge_case(edge_a_part: str, edge_b_part: str, relative_position: str) -> int:
    if relative_position == "parallel":
        return 8
    elif edge_a_part == "end" and edge_b_part == "end":
        return 7

    case_table = {
        1: ["start", "start", "left"],
        2: ["start", "start", "right"],
        3: ["start", "end", "left"],
        4: ["start", "end", "right"],
        5: ["end", "start", "left"],
        6: ["end", "start", "right"],
    }
    for key, value in case_table.items():
        if value == [edge_a_part, edge_b_part, relative_position]:
            return key
    return 0


def is_in_feasible_range(translation_vector: tuple, pair: EdgePair) -> bool:
    shared_vertex = (pair.shared_vertex.x, pair.shared_vertex.y)
    translation_vector_endpoint = (pair.shared_vertex.x + translation_vector[0], pair.shared_vertex.y + translation_vector[1])
    translation_vector_linestring = LineString([shared_vertex, translation_vector_endpoint])
    print(pair)

    match pair.edge_case:
        case 1:
            # the allowed range is the side of a that b is on, union with the side of b that a is not on
            # borders (="parallel") are allowed too
            if pair.edge_a_index == 3:
                pass
            allowed_side_a = is_left_or_right(pair.edge_a, pair.edge_b)
            allowed_side_b = is_left_or_right(pair.edge_b, pair.edge_a)
            location_a = is_left_or_right(pair.edge_a, translation_vector_linestring)
            location_b = is_left_or_right(pair.edge_b, translation_vector_linestring)
            if allowed_side_a == "parallel" and allowed_side_b == "parallel":
                return True

            if location_a == "parallel":  # TODO this check is important, but it has false positives. Get into "start" and "end" again?
                non_touching_vertex_of_a = pair.edge_a.coords[0] if pair.edge_a.coords[1] == shared_vertex else pair.edge_a.coords[1]
                angle_a = angle_from_points(non_touching_vertex_of_a, shared_vertex, translation_vector_endpoint)
                # compute fresh angle and check that for 180°
                if angle_a == 180:
                    return False

            if location_b == "parallel":
                # same here, points should be non-touching vertex of b, shared_point, translation_vector_endpoint
                non_touching_vertex_of_b = pair.edge_b.coords[0] if pair.edge_b.coords[1] == shared_vertex else pair.edge_b.coords[1]
                angle_b = angle_from_points(non_touching_vertex_of_b, shared_vertex, translation_vector_endpoint)
                if angle_b == 0:
                    return False

            negated_side_b = "right" if allowed_side_b == "left" else "left"
            return location_a in [allowed_side_a, "parallel"] or location_b in [negated_side_b, "parallel"]
        case 2:
            # side of a that b is on, but only use the part of a betweeen shared_vertex and its end
            trimmed_a = LineString([shared_vertex, (pair.edge_a.coords[1])])
            allowed_side_a = is_left_or_right(trimmed_a, pair.edge_b)
            if allowed_side_a == "parallel":  # in cases 2 and 3 that means the two edges are laying on top of each other
                return True

            location_a = is_left_or_right(trimmed_a, translation_vector_linestring)
            return location_a in [allowed_side_a, "parallel"]
        case 3:
            # side of b that a is not on, but only use the part of b betweeen shared_vertex and its end
            trimmed_b = LineString([shared_vertex, (pair.edge_b.coords[1])])
            disallowed_side_b = is_left_or_right(trimmed_b, pair.edge_a)
            if disallowed_side_b == "parallel":
                return True

            location_b = is_left_or_right(trimmed_b, translation_vector_linestring)
            return location_b != disallowed_side_b


def trim_translation_vector(source_poly: Polygon, target_poly: Polygon, translation_vector: tuple, shared_vertices: list, reverse: bool = False) -> tuple:
    dx, dy = translation_vector
    if reverse:
        dx, dy = -dx, -dy

    for x, y in source_poly.exterior.coords[:-1]:
        start = (x, y)
        end = (x + dx, y + dy)

        if end in source_poly.exterior.coords:
            continue
        if start in target_poly.exterior.coords and end in target_poly.exterior.coords:
            continue

        path = LineString([start, end])
        intersection = precision_aware_intersection(path, target_poly)

        if not intersection.is_empty:
            if intersection.geom_type == "Point":
                intersection_point = intersection.coords[0]
                if intersection in shared_vertices:
                    continue
            elif intersection.geom_type == "LineString":  # can happen in edge cases 2 and 3
                print("Skipped due to LineString intersection")
                continue
            else:
                # example: GEOMETRYCOLLECTION (LINESTRING (10.571428571428571 9.714285714285714, 11 10), POINT (8 8))
                intersection_point = find_closest_intersection(start, intersection)

            # Set vector to go only up to the intersection point
            ix, iy = intersection_point
            dx = round(ix - start[0], NO_OF_ROUNDING_DIGITS)
            dy = round(iy - start[1], NO_OF_ROUNDING_DIGITS)
    # If reverse, flip vector back to match original direction
    if reverse:
        return (-dx, -dy)

    return (dx, dy)


def find_closest_intersection(start: tuple, geometry_collection) -> Point | None:
    start_point = Point(start)
    closest_point = None
    min_distance = float("inf")

    geoms = (geometry_collection.geoms if hasattr(geometry_collection, "geoms") else [geometry_collection])

    for geom in geoms:
        if geom.is_empty:
            continue

        if isinstance(geom, Point):
            if geom.equals(start_point):
                continue  # skip exact start point
            dist = start_point.distance(geom)
            if dist < min_distance:
                closest_point = geom
                min_distance = dist

        elif isinstance(geom, LineString):
            p1, p2 = nearest_points(start_point, geom)
            if p2.equals(start_point):
                continue  # again, skip exact start
            dist = start_point.distance(p2)
            if dist < min_distance:
                closest_point = p2
                min_distance = dist

    return (closest_point.x, closest_point.y)


def is_closed_loop(nfp, tol=1e-8):
    if len(nfp) < 3:
        return False
    start = Point(nfp[0])
    end = Point(nfp[-1])
    return start.distance(end) < tol

# ----- more general helpers -----

def precision_aware_intersection(obj1, obj2, precision=INTERSECTION_PRECISION):
    obj1_snapped = set_precision(obj1, precision)
    obj2_snapped = set_precision(obj2, precision)
    return obj1_snapped.intersection(obj2_snapped)


def vector_from_points(start: tuple, end: tuple) -> tuple:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return (round(dx, NO_OF_ROUNDING_DIGITS), round(dy, NO_OF_ROUNDING_DIGITS))


def angle_from_points(point_a: tuple, point_b: tuple, point_c: tuple) -> float:
    ba = vector_from_points(point_b, point_a)
    bc = vector_from_points(point_b, point_c)

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    cross = ba[0] * bc[1] - ba[1] * bc[0]

    angle_rad = math.atan2(cross, dot)
    angle_deg = math.degrees(angle_rad)

    # Normalize to [0, 360)
    if angle_deg < 0:
        angle_deg += 360

    return angle_deg


def get_edges(polygon):
    coords = list(polygon.exterior.coords)
    edges = [LineString([coords[i], coords[i+1]]) for i in range(len(coords)-1)]
    return edges


def find_edge_index(poly_edges: list, edge: LineString) -> int:
    for i, e in enumerate(poly_edges):
        if e.equals(edge):
            return i
    raise Exception("Cannot find specified edge in polygon")
