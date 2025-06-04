import os
import re
import math
from svgpathtools import Path, parse_path
import lxml.etree as ETree
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from export_svg import export_piece_to_svg
from models.pattern import Pattern
from models.piece import Piece

# "profiles" for different sewing pattern sources

# SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_pattern_full.svg")
# MERGE_PIECES = True
# ALLOWED_CLASS_LISTS = []

# SVG_FILE = os.path.join(os.getcwd(), "data", "example.svg")
# MERGE_PIECES = True
# ALLOWED_CLASS_LISTS = []

SVG_FILE = os.path.join(os.getcwd(), "data", "freesewing-huey.svg")
MERGE_PIECES = False
ALLOWED_CLASS_LISTS = [["fabric"], ["various"]]

# SVG_FILE = os.path.join(os.getcwd(), "pattern.svg")
# MERGE_PIECES = False
# ALLOWED_CLASS_LISTS = []


# seam information dataclasses
@dataclass
class Seampart:
    part: str
    start: tuple
    end: tuple
    direction: bool


@dataclass
class Seam:
    id: int
    seamparts: list

# helpers for merging

def __points_equal(p1: complex, p2: complex, tol: float = 1e-5) -> bool:
    return abs(p1.real - p2.real) < tol and abs(p1.imag - p2.imag) < tol


def __segments_equal(s1, s2, tol=1e-5) -> bool:
    return (
        __points_equal(s1.start, s2.start, tol) and __points_equal(s1.end, s2.end, tol)
    ) or (
        __points_equal(s1.start, s2.end, tol) and __points_equal(s1.end, s2.start, tol)
    )


def __reorder_segments(segments: list, tol=1e-6) -> list:
    """Reorder and orient segments so they form a continuous path."""
    if not segments:
        return []

    ordered = [segments.pop(0)]
    while segments:
        previous_segment = ordered[-1]

        match_index = None
        reverse_needed = False
        for i, seg in enumerate(segments):
            if abs(seg.start - previous_segment.end) < tol:
                match_index = i
                reverse_needed = False
                break
            elif abs(seg.end - previous_segment.end) < tol:
                match_index = i
                reverse_needed = True
                break

        if match_index is not None:
            match = segments.pop(match_index)
            if reverse_needed:
                match = match.reversed()
            ordered.append(match)
        else:
            # No match found: path is not fully continuous
            break

    return ordered


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

    # Reorder to restore continuity
    reordered = __reorder_segments(cleaned_segments)

    return Path(*reordered)


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


def load_selected_paths(svg_file: str) -> list:
    tree = ETree.parse(svg_file)
    root = tree.getroot()
    selected_paths = []
    for elem in root.iter():
        if 'path' not in str(elem.tag):
            continue

        path_data = elem.attrib.get('d')
        if not path_data:
            continue

        class_list = elem.attrib.get('class', '').split()
        if ALLOWED_CLASS_LISTS and class_list not in ALLOWED_CLASS_LISTS:
            continue

        path = parse_path(path_data)

        # Walk up the tree and apply any group transforms, starting at the element itself
        current_elem = elem
        while current_elem is not None:
            transform_attr = current_elem.attrib.get('transform')
            if transform_attr:
                path = apply_svg_transform(path, transform_attr)
            current_elem = current_elem.getparent()
        selected_paths.append(path)

    return selected_paths


def apply_svg_transform(path: Path, transform_str: str) -> Path:
    transform_regex = re.findall(r'(translate|scale|rotate)\(([^)]*)\)', transform_str)
    for name, args in transform_regex:
        values = list(map(float, re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', args)))

        if name == "translate":
            dx, dy = values if len(values) == 2 else (values[0], 0)
            path = path.translated(complex(dx, dy))
        elif name == "scale":
            if len(values) == 1:
                sx, sy = values[0], values[0]
            else:
                sx, sy = values
            path = path.scaled(sx, sy)
        elif name == "rotate":
            angle_deg = values[0]
            angle_rad = math.radians(-angle_deg)  # TODO check rotation (if that ever becomes relevant)
            path = path.rotated(angle_rad)

    return path


def parse_coord(coord_str: str) -> tuple:
    x_str, y_str = coord_str.strip().split(",")
    return float(x_str), float(y_str)


def parse_svg_metadata(svg_path: str) -> list:
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = {'svg': 'http://www.w3.org/2000/svg'}
    metadata = root.find('svg:metadata', ns) or root.find('metadata')
    if metadata is None:
        raise ValueError("No <metadata> tag found in SVG")

    # seamdefinition has a weird namespace TODO
    for child in metadata:
        namespace = child.tag[1:].split("}")[0] if child.tag.startswith("{") else None
        if child.tag.endswith('seamdefinition'):
            seamdefinition = child
            break
    else:
        raise ValueError("No <seamdefinition> tag found in metadata")

    ns = f'{{{namespace}}}' if namespace else ''
    seams = []

    for seam_elem in seamdefinition.findall(f'{ns}seam'):
        seam_id = int(seam_elem.find(f'{ns}id').text)
        seamparts = []

        for part_elem in seam_elem.findall(f'{ns}seampart'):
            part = part_elem.find(f'{ns}part').text
            start = parse_coord(part_elem.find(f'{ns}start').text)
            end = parse_coord(part_elem.find(f'{ns}end').text)
            direction = part_elem.find(f'{ns}direction').text.lower() == 'true'  # :/
            seamparts.append(Seampart(part, start, end, direction))

        seams.append(Seam(seam_id, seamparts))

    return seams


if __name__ == "__main__":
    if not os.path.exists(SVG_FILE):
            raise FileNotFoundError(f"SVG file not found: {SVG_FILE}")

    svg_attributes = get_svg_attributes(SVG_FILE)
    height = svg_attributes.get("height")
    unit_scale = 0.1 if "mm" in height else 1

    paths = load_selected_paths(SVG_FILE)
    pieces = []
    for index, path in enumerate(paths):
        pieces.append(Piece(index, path, unit_scale))

    merged_pieces = reindex(merge_pieces_with_common_vertices(pieces)) if MERGE_PIECES else pieces

    seams = parse_svg_metadata(SVG_FILE)
    for seam in seams:
        print(f"Seam ID: {seam.id}")
        for part in seam.seamparts:
            print(f"  Part: {part.part}, Start: {part.start}, End: {part.end}, Direction: {part.direction}")

    full_pattern = Pattern(merged_pieces, seams)

    # print(full_pattern)
    for piece in full_pattern.pieces:
        export_piece_to_svg(piece, f"piece_{piece.index}.svg", svg_attributes)
