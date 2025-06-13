from shapely.geometry import Polygon, Point, LineString

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


def vector_from_points(start: tuple, end: tuple) -> tuple:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return (dx, dy)
