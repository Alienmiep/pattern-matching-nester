import os
from svgpathtools import svg2paths, Path
import xml.etree.ElementTree as ET

from export_svg import export_piece_to_svg
from models.pattern import Pattern
from models.piece import Piece

SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_pattern_full.svg")


def __points_equal(p1: complex, p2: complex, tol: float = 1e-5) -> bool:
    return abs(p1.real - p2.real) < tol and abs(p1.imag - p2.imag) < tol


def __segments_equal(s1, s2, tol=1e-5) -> bool:
    return (
        __points_equal(s1.start, s2.start, tol) and __points_equal(s1.end, s2.end, tol)
    ) or (
        __points_equal(s1.start, s2.end, tol) and __points_equal(s1.end, s2.start, tol)
    )


def combine_paths(path1: Path, path2: Path) -> Path:
    combined_segments = list(path1) + list(path2)
    cleaned_segments = []

    while combined_segments:
        seg = combined_segments.pop(0)
        # Check if this segment (or its reverse) already exists
        duplicate_index = next(
            (i for i, s in enumerate(combined_segments) if __segments_equal(seg, s)),
            None
        )
        if duplicate_index is not None:
            # Remove the matching duplicate
            combined_segments.pop(duplicate_index)
        else:
            cleaned_segments.append(seg)

    return Path(*cleaned_segments)


def merge_pieces_with_common_vertices(pieces: list) -> list:
    merged_pieces = []
    while pieces:
        # print([str(x) for x in merged_pieces])
        piece = pieces.pop(0)
        match_found = False
        for p in pieces:
            merged_vertex_set = set(piece.vertices + p.vertices)
            if len(merged_vertex_set) <= len(piece.vertices) + len(p.vertices) - 2:  # share at least 2 vertices
                match_found = True
                pieces.remove(p)  # <- allows for only one match, so only 2 pieces can be merged together
                new_path = combine_paths(piece.path, p.path)
                merged_pieces.append(Piece(-1, new_path))
        if not match_found:
            merged_pieces.append(piece)
    return merged_pieces


def reindex(pieces: list) -> list:
    for index, piece in enumerate(pieces):
        piece.index = index
    return pieces


def get_svg_attributes(svg_file: str) -> dict:
    tree = ET.parse(svg_file)
    root = tree.getroot()

    return {
        key: root.attrib[key]
        for key in root.attrib
        if key in {'viewBox', 'width', 'height', 'baseProfile'} # , 'xmlns', 'xmlns:xlink', 'xmlns:ev', 'version', 'baseProfile'}
    }


if __name__ == "__main__":
    if not os.path.exists(SVG_FILE):
            raise FileNotFoundError(f"SVG file not found: {SVG_FILE}")

    svg_attributes = get_svg_attributes(SVG_FILE)

    paths, attributes = svg2paths(SVG_FILE)
    pieces = []
    for index, path in enumerate(paths):
        pieces.append(Piece(index, path))

    merged_pieces = reindex(merge_pieces_with_common_vertices(pieces))
    full_pattern = Pattern(merged_pieces)

    print(full_pattern)
    for piece in full_pattern.pieces:
        export_piece_to_svg(piece, f"piece_{piece.index}.svg", svg_attributes)
