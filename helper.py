import math
from dataclasses import dataclass

from shapely.geometry import Polygon, Point, LineString

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
        if edge.touches(point):  # this should work for edge cases (2) and (3) as well
            edges.append(edge)
    return edges


def classify_edge_pair(edge_pair: tuple) -> int:
    endpoints_a = {edge_pair[0].coords[0], edge_pair[0].coords[-1]}
    endpoints_b = {edge_pair[1].coords[0], edge_pair[1].coords[-1]}

    # check if they share an endpoint (case (1))
    shared_points = endpoints_a & endpoints_b
    if shared_points:
        return 1

    inter = edge_pair[0].intersection(edge_pair[1])
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


def is_left_or_right(edge_a: LineString, edge_b: LineString) -> str:
    if list(edge_a.coords) == list(edge_b.coords) or list(edge_a.coords) == list(edge_b.coords)[::-1]:
        return "parallel"

    # point A: non-touching point of edge_b
    # point B: start of edge_a
    # point C: end of edge_a
    point_a = edge_b.coords[0] if edge_b.coords[0] not in list(edge_a.coords) else edge_b.coords[1]
    point_b = edge_a.coords[0]
    point_c = edge_a.coords[1]
    angle = angle_from_points(point_a, point_b, point_c)
    return "left" if angle > 180 else "right"


def get_edge_case(edge_a_part: str, edge_b_part: str, relative_posiion: str) -> int:
    if relative_posiion == "parallel":
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
        if value == [edge_a_part, edge_b_part, relative_posiion]:
            return key
    return 0


def get_disallowed_location(a_part: str, b_part: str) -> tuple:
    # page 37, Fig. 10
    location_a = "left" if a_part == "start" else "right"
    location_b = "left" if b_part == "start" else "right"
    return location_a, location_b


def is_in_feasible_range(translation_vector: tuple, pair: EdgePair) -> bool:
    translation_vector_endpoint = (pair.shared_vertex.x + translation_vector[0], pair.shared_vertex.y + translation_vector[1])
    translation_vector_linestring = LineString([(pair.shared_vertex.x, pair.shared_vertex.y), translation_vector_endpoint])

    match pair.edge_case:
        case 1:
            # which part of a/b is touching the shared vertex
            edge_a_part = "start" if Point(pair.edge_a.coords[0]) == pair.shared_vertex else "end"
            edge_b_part = "start" if Point(pair.edge_b.coords[0]) == pair.shared_vertex else "end"
            disallowed_a, disallowed_b = get_disallowed_location(edge_a_part, edge_b_part)
            location_a = is_left_or_right(pair.edge_a, translation_vector_linestring)
            location_b = is_left_or_right(pair.edge_b, translation_vector_linestring)
            print(location_a, location_b)
            print(disallowed_a, disallowed_b)
            if location_a == "parallel":  # TODO <- questionable
                location_a = disallowed_a
            if location_b == "parallel":
                location_b = disallowed_b
            print(not (location_a == disallowed_a and location_b == disallowed_b))
            return not (location_a == disallowed_a and location_b == disallowed_b)
        case 2:
            location_a = is_left_or_right(pair.edge_a, translation_vector_linestring)
            return location_a == "right"
        case 3:
            location_b = is_left_or_right(pair.edge_b, translation_vector_linestring)
            return location_b == "left"


def trim_translation_vector(source_poly: Polygon, target_poly: Polygon, translation_vector: tuple, shared_vertex: tuple, reverse: bool = False) -> tuple:
    dx, dy = translation_vector
    if reverse:
        dx, dy = -dx, -dy

    for x, y in source_poly.exterior.coords[:-1]:
        start = (x, y)
        if start == shared_vertex:  # would intersect immediately
            continue

        end = (x + dx, y + dy)
        path = LineString([start, end])
        intersection = path.intersection(target_poly)

        if not intersection.is_empty:
            if intersection.geom_type == "Point":
                intersection_point = intersection
            elif intersection.geom_type.startswith("Multi"):
                intersection_point = list(intersection.geoms)[0]
            else:
                continue

            # Set vector to go only up to the intersection point
            ix, iy = intersection_point.coords[0]
            trimmed_vector = (ix - x, iy - y)
            # If reverse, flip vector back to match original direction
            if reverse:
                trimmed_vector = (-trimmed_vector[0], -trimmed_vector[1])

            return trimmed_vector

    return translation_vector


def is_closed_loop(nfp, tol=1e-8):
    if len(nfp) < 3:
        return False
    start = Point(nfp[0])
    end = Point(nfp[-1])
    return start.distance(end) < tol

# ----- more general helpers -----

def vector_from_points(start: tuple, end: tuple) -> tuple:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return (dx, dy)


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
