from svgpathtools import Path

COORDINATE_DECIMAL_PLACES = 1

class Piece():
    def __init__(self, index: int, path: Path):
        self.index = index
        self.path = path
        self.vertices = self.__extract_vertices()

    def __str__(self):
        return f"Index: {self.index}, Vertices: {self.vertices}"

    def __extract_vertices(self) -> list:
        vertices = []
        if not self.path:
            return vertices

        for segment in self.path:
            x = round(segment.end.real, COORDINATE_DECIMAL_PLACES)
            y = round(-segment.end.imag, COORDINATE_DECIMAL_PLACES)  # imaginary component is inverted, adjust if needed
            if (x, y) not in vertices:  # avoid duplicate points
                vertices.append((x, y))
        return vertices
