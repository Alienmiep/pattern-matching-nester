import os
from svgpathtools import svg2paths

from models.pattern import Pattern
from models.piece import Piece

SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_pattern_full.svg")

if __name__ == "__main__":
    if not os.path.exists(SVG_FILE):
            raise FileNotFoundError(f"SVG file not found: {SVG_FILE}")

    paths, attributes = svg2paths(SVG_FILE)
    pieces = []
    for path in paths:
        pieces.append(Piece(path))

    full_pattern = Pattern(pieces)

    print(full_pattern)
