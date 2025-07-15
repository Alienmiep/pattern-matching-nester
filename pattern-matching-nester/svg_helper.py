import re
import math
from dataclasses import dataclass
from svgpathtools import Path, parse_path
import lxml.etree as ETree
import xml.etree.ElementTree as ET

from models.piece import Piece
from demo import ALLOWED_CLASS_LISTS, MERGE_SLEEVES


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


def merge_pieces_with_common_vertices(pieces: list, unit_scale: float) -> list:
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
                merged_pieces.append(Piece(-1, new_path, unit_scale))
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
    sleeve_paths = []
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

        # sort out sleeves to merge them (if needed)
        if MERGE_SLEEVES:
            name_attr = elem.attrib.get('name')
            if name_attr and 'sleeve' in name_attr.lower():
                sleeve_paths.append(path_data)
                continue
        selected_paths.append(path)

    if sleeve_paths:
        sleeve_paths = prepare_sleeve_paths_for_merge(sleeve_paths)

    selected_paths.extend(sleeve_paths)
    return selected_paths



def prepare_sleeve_paths_for_merge(path_strs: list) -> list:
    if len(path_strs) not in (2, 4):
        raise ValueError(f"Expected 2 or 4 sleeve paths, got {len(path_strs)}")

    # Get min and max x for each path
    bounds = [(i, *get_path_extreme_x(d)) for i, d in enumerate(path_strs)]

    # Find the outermost paths
    min_x_idx = min(bounds, key=lambda b: b[1])[0]
    max_x_idx = max(bounds, key=lambda b: b[2])[0]

    # Get their path strings
    min_path_str = path_strs[min_x_idx]
    max_path_str = path_strs[max_x_idx]

    merged_paths = align_sleeve_halves(min_path_str, max_path_str)

    # If we have 4 paths, merge the remaining pair
    if len(path_strs) == 4:
        remaining_indices = set(range(4)) - {min_x_idx, max_x_idx}
        i1, i2 = list(remaining_indices)
        p1, p2 = path_strs[i1], path_strs[i2]

        # Decide which of the two remaining has the lower min-x
        min_x1, _ = get_path_extreme_x(p1)
        min_x2, _ = get_path_extreme_x(p2)

        if min_x1 <= min_x2:
            merged_paths.extend(align_sleeve_halves(p2, p1, 20))
        else:
            merged_paths.extend(align_sleeve_halves(p1, p2, 20))

    return merged_paths


def get_path_extreme_x(path_str):
    path = parse_path(path_str)
    xs = [seg.start.real for seg in path] + [seg.end.real for seg in path]
    return min(xs), max(xs)


def align_sleeve_halves(min_path_str: str, max_path_str: str, offset: int=0):
    min_path = parse_path(min_path_str)
    max_path = parse_path(max_path_str)
    v1, n1 = get_sleeve_edge_vertices(min_path, mode='min')
    v2, n2 = get_sleeve_edge_vertices(max_path, mode='max')
    min_path_rotated = rotate_path_to_horizontal(min_path, v1, n1)
    max_path_rotated = rotate_path_to_horizontal(max_path, v2, n2)

    midpoint = (v1 + v2) / 2 + offset
    min_offset = midpoint - v1
    max_offset = midpoint - v2
    aligned_min_path = min_path_rotated.translated(min_offset)
    aligned_max_path = max_path_rotated.translated(max_offset)

    return [aligned_min_path, aligned_max_path]


def get_sleeve_edge_vertices(path, mode='min'):
    """
    Given a Path object and mode ('min' or 'max'), returns the target edge as (vertex, neighbor),
    where:
        - vertex is the extreme-x point (min or max)
        - neighbor is the adjacent point with the lowest y
    The "target edge" in this context is essentially the fold line of the sleeve, the one where GarmentCode makes a cut
    """
    # Convert to a flat list of points
    points = []
    for seg in path:
        points.append(seg.start)

    # Find index of extreme x point
    if mode == 'min':
        index = min(range(len(points)), key=lambda i: points[i].real)
    elif mode == 'max':
        index = max(range(len(points)), key=lambda i: points[i].real)
    else:
        raise ValueError("mode must be 'min' or 'max'")

    current = points[index]
    prev = points[index - 1 if index > 0 else -1]
    next = points[(index + 1) % len(points)]

    # Choose neighbor with lowest y
    neighbor = prev if prev.imag < next.imag else next

    return current, neighbor


def rotate_path_to_horizontal(path: Path, edge_start, edge_end):
    dx = edge_end.real - edge_start.real
    dy = edge_end.imag - edge_start.imag

    angle = math.degrees(-math.atan2(dy, dx) - math.pi / 2)  # negative to rotate toward +x axis

    # Translate so edge_start is at origin
    translated = path.translated(-edge_start)

    # Rotate path around origin
    rotated = translated.rotated(angle, 0)

    # Translate back to original position
    restored = rotated.translated(edge_start)

    # save_debug_svg(
    #     [path, restored],
    #     filename=f"rotated_test_{angle}.svg",
    #     colors=["red", "blue"]
    # )

    return restored


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

