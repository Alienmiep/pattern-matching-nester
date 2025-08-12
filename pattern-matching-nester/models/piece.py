from svgpathtools import Path, Line, Arc, CubicBezier, QuadraticBezier
from shapely.geometry import Polygon

COORDINATE_DECIMAL_PLACES = 1

class Piece():
    def __init__(self, index: int, name: str, path: Path, unit_scale: float):
        self.index = index
        self.name = name
        self.path = path
        self.vertices = self.__extract_vertices(unit_scale)
        self.aabb = None

    def __str__(self):
        return f"Index: {self.index}, Vertices: {self.vertices}"

    def __extract_vertices(self, unit_scale, base_resolution=3.0, min_samples=3, max_samples=20) -> list:
        """
        Converts a Path into a list of (x, y) vertices.
        - base_resolution: target spacing between points (in cm)
        - min_samples / max_samples: limits on sampling granularity
        """
        vertices = []
        if not self.path:
            return vertices

        for segment in self.path:
            segment_type = type(segment)
            segment_length = segment.length(error=1e-4)
            if segment_length == 0:
                continue  # avoid division by zero :^)

            num_samples = max(min_samples, min(int(segment_length / base_resolution), max_samples))

            if segment_type in (Line,):
                points = [segment.start, segment.end]
            elif segment_type in (Arc, CubicBezier, QuadraticBezier):
                points = [segment.point(t / num_samples) for t in range(0, num_samples + 1)]
            else:
                raise NotImplementedError(f"Unhandled segment type: {segment_type}")

            for pt in points:
                x = float(round(pt.real * unit_scale, COORDINATE_DECIMAL_PLACES))
                y = float(round(-pt.imag * unit_scale, COORDINATE_DECIMAL_PLACES))
                if (x, y) not in vertices:
                    vertices.append((x, y))  # avoid duplicate points

        return vertices  # do not reverse order of vertices, that is done at the start of NFP

    def area(self):
        polygon = Polygon(self.vertices)
        return polygon.area
