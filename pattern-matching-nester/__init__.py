import os
from svgpathtools import svg2paths

SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_pattern_full.svg")

class SewingPatternParser:
    def __init__(self, svg_file_path: str):
        if not os.path.exists(svg_file_path):
            raise FileNotFoundError(f"SVG file not found: {svg_file_path}")
        self.svg_file_path = svg_file_path
        self.tree = None
        self.paths = []


if __name__ == "__main__":

    if not os.path.exists(SVG_FILE):
            raise FileNotFoundError(f"SVG file not found: {SVG_FILE}")
    paths, attributes = svg2paths(SVG_FILE)

    print(paths[0])
