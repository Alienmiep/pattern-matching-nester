from svgpathtools import Path, Line, Arc, CubicBezier, QuadraticBezier
from shapely.geometry import Polygon

COORDINATE_DECIMAL_PLACES = 1

class Piece():
    def __init__(self, index: int, name: str, path: Path, unit_scale: float):
        self.index = index
        self.name = name
        self.path = path
        self.original_vertices, self.vertices, self.vertex_mapping = self.__extract_vertices(unit_scale)
        self.aabb = None
        self.reference_point_index = None

    @property
    def reference_point(self):
        return self.vertices[self.reference_point_index]

    @reference_point.setter
    def reference_point(self, value):
        self.reference_point_index = self.vertices.index(value)

    def __str__(self):
        return f"Index: {self.index}, Vertices: {self.vertices}, original Vertices: {self.original_vertices}"

    def __extract_vertices(self, unit_scale, base_resolution=3.0, min_samples=3, max_samples=20) -> tuple:
        """
        Converts a Path into:
        - original_vertices: anchor points from the SVG path
        - vertices: full polygon with sampled points
        - vertex_mapping: mapping {original_index: [polygon_indices]}

        base_resolution: target spacing between points (in cm)
        min_samples / max_samples: limits on sampling granularity
        """
        vertices = []
        original_vertices = []
        vertex_mapping = {}

        if not self.path:
            return original_vertices, vertices, vertex_mapping

        for orig_idx, segment in enumerate(self.path):
            segment_type = type(segment)
            segment_length = segment.length(error=1e-4)
            if segment_length == 0:
                continue

            num_samples = max(min_samples, min(int(segment_length / base_resolution), max_samples))

            if segment_type in (Line,):
                points = [segment.start, segment.end]
            elif segment_type in (Arc, CubicBezier, QuadraticBezier):
                points = [segment.point(t / num_samples) for t in range(0, num_samples + 1)]
            else:
                raise NotImplementedError(f"Unhandled segment type: {segment_type}")

            for i, pt in enumerate(points):
                x = float(round(pt.real * unit_scale, COORDINATE_DECIMAL_PLACES))
                y = float(round(-pt.imag * unit_scale, COORDINATE_DECIMAL_PLACES))
                if (x, y) not in vertices:
                    vertices.append((x, y))

                    # if this is the *start* of the first segment, or the *end* of any segment,
                    # treat it as an original anchor
                    if (i == 0 and orig_idx == 0) or i == len(points) - 1:
                        original_vertices.append((x, y))
                        vertex_mapping[len(original_vertices) - 1] = len(vertices) - 1

        return original_vertices, vertices, vertex_mapping  # NFP algorithm ensures vertices are in the right order (counter-clockwise)

    def area(self):
        polygon = Polygon(self.vertices)
        return polygon.area
