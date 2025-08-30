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
    # direction: bool


@dataclass
class Seam:
    id: int
    seamparts: list
    matchable: bool = False

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


def merge_pieces_with_common_vertices(pieces: list, unit_scale: float) -> tuple:
    merged_pieces = []
    index_mappings = {}   # {old_piece_name: {old_index: new_index}}
    merged_names = {}     # {old_piece_name: new_piece_name}

    while pieces:
        piece = pieces.pop(0)
        match_found = False
        for p in pieces:
            merged_vertex_list = list(dict.fromkeys(piece.vertices + p.vertices))
            # preserve order, remove duplicates

            if len(merged_vertex_list) <= len(piece.vertices) + len(p.vertices) - 2:
                match_found = True
                pieces.remove(p)

                new_path = combine_paths(piece.path, p.path)
                new_name = f"{piece.name}+{p.name}"
                new_piece = Piece(-1, new_name, new_path, unit_scale, _original_pieces=[piece, p])

                # Build index mappings
                mapping_piece = {i: new_piece.vertices.index(v) for i, v in enumerate(piece.vertices)}
                mapping_p     = {i: new_piece.vertices.index(v) for i, v in enumerate(p.vertices)}

                index_mappings[piece.name] = mapping_piece
                index_mappings[p.name] = mapping_p
                merged_names[piece.name] = new_name
                merged_names[p.name] = new_name

                merged_pieces.append(new_piece)

        if not match_found:
            merged_pieces.append(piece)

    return merged_pieces, index_mappings, merged_names


def remap_seams(seams: list, index_mappings: dict, merged_names: dict) -> list:
    updated_seams = []

    for seam in seams:
        new_seamparts = []
        for sp in seam.seamparts:
            if sp.part in index_mappings:
                mapping = index_mappings[sp.part]
                new_start = mapping.get(sp.start, sp.start)
                new_end   = mapping.get(sp.end, sp.end)
                new_part_name = merged_names.get(sp.part, sp.part)
                new_seamparts.append(
                    Seampart(new_part_name, new_start, new_end)
                )
            else:
                new_seamparts.append(sp)
        updated_seams.append(Seam(seam.id, new_seamparts, seam.matchable))
    return updated_seams


def correct_vertex_indices(seams: list, pieces: list) -> list:
    """
    Rewrite seam vertex indices so they point into the polygon vertices
    (Piece.vertices) instead of original SVG indices.
    """
    # Build quick lookup by piece name
    piece_lookup = {p.name: p for p in pieces}
    corrected_seams = []

    for seam in seams:
        new_seamparts = []
        for sp in seam.seamparts:
            if sp.part not in piece_lookup:
                # seam references a missing piece -> leave unchanged
                new_seamparts.append(sp)
                continue

            piece = piece_lookup[sp.part]

            # Map original indices to polygon indices
            start_new = piece.vertex_mapping.get(sp.start, sp.start)
            end_new   = piece.vertex_mapping.get(sp.end, sp.end)

            new_sp = Seampart(
                part=sp.part,
                start=start_new,
                end=end_new
            )
            new_seamparts.append(new_sp)

        corrected_seams.append(
            Seam(seam.id, new_seamparts, seam.matchable)
        )

    return corrected_seams


def reduce_seams(merged_pieces: list, seams: list) -> list:
    seam_idx_to_keep = [1] * len(seams)
    for piece in merged_pieces:
        if "+" in piece.name:
            part_names = piece.name.split("+")
            if len(part_names) > 2:
                raise NotImplementedError("More than 3 pieces merged into one")
            part_1 = part_names[0]
            part_2 = part_names[1]

            for i, seam in enumerate(seams):
                seam: Seam
                if len(seam.seamparts) < 2:
                    continue
                if len(seam.seamparts) > 2:
                    raise NotImplementedError("Seam with more than 3 parts")
                seampart_names = [x.part for x in seam.seamparts]
                if part_1 in seampart_names and part_2 in seampart_names:
                    seam_idx_to_keep[i] = 0

    reduced_seams = []
    for i, seam in enumerate(seams):
        if seam_idx_to_keep[i]:
           reduced_seams.append(seam)

    print("no of seams left: ", len(reduced_seams))
    return reduced_seams


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


def load_selected_paths(svg_file: str) -> tuple:
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
        sleeve_piece_modifiers = {}
        name_attr = elem.attrib.get('name')
        if MERGE_SLEEVES:
            if name_attr and 'sleeve' in name_attr.lower():
                sleeve_paths.append((name_attr.lower(), path_data))
                continue
        selected_paths.append((name_attr.lower(), path))

    if sleeve_paths:
        sleeve_paths, sleeve_piece_modifiers = prepare_sleeve_paths_for_merge(sleeve_paths)

    selected_paths.extend(sleeve_paths)
    return selected_paths, sleeve_piece_modifiers



def prepare_sleeve_paths_for_merge(path_tuples: list) -> tuple:
    if len(path_tuples) not in (2, 4):
        raise ValueError(f"Expected 2 or 4 sleeve paths, got {len(path_tuples)}")

    all_sleeve_piece_modifiers = {}

    # Get min and max x for each path
    path_names = [x[0] for x in path_tuples]
    path_strs = [x[1] for x in path_tuples]
    bounds = [(i, *get_path_extreme_x(d)) for i, d in enumerate(path_strs)]

    # Find the outermost paths
    min_x_idx = min(bounds, key=lambda b: b[1])[0]
    max_x_idx = max(bounds, key=lambda b: b[2])[0]

    # Get their path strings
    min_path_str = path_strs[min_x_idx]
    max_path_str = path_strs[max_x_idx]
    min_path_name = path_names[min_x_idx]
    max_path_name = path_names[max_x_idx]

    aligned_min_path, aligned_max_path, sleeve_piece_modifiers = align_sleeve_halves(min_path_str, min_path_name, max_path_str, max_path_name)
    all_sleeve_piece_modifiers.update(sleeve_piece_modifiers)
    merged_paths = [(min_path_name, aligned_min_path), (max_path_name, aligned_max_path)]

    # If we have 4 paths, merge the remaining pair
    if len(path_strs) == 4:
        remaining_indices = set(range(4)) - {min_x_idx, max_x_idx}
        i1, i2 = list(remaining_indices)
        p1, p2 = path_strs[i1], path_strs[i2]
        path_name_1 = path_names[i1]
        path_name_2 = path_names[i2]

        # Decide which of the two remaining has the lower min-x
        min_x1, _ = get_path_extreme_x(p1)
        min_x2, _ = get_path_extreme_x(p2)

        if min_x1 <= min_x2:
            aligned_min_path, aligned_max_path, sleeve_piece_modifiers = align_sleeve_halves(p2, path_name_2, p1, path_name_1, 20)
            merged_paths.extend([(path_name_2, aligned_min_path), (path_name_1, aligned_max_path)])
            all_sleeve_piece_modifiers.update(sleeve_piece_modifiers)
        else:
            aligned_min_path, aligned_max_path, sleeve_piece_modifiers = align_sleeve_halves(p1, path_name_1, p2, path_name_2, 20)
            merged_paths.extend([(path_name_1, aligned_min_path), (path_name_2, aligned_max_path)])
            all_sleeve_piece_modifiers.update(sleeve_piece_modifiers)

    return merged_paths, all_sleeve_piece_modifiers


def get_path_extreme_x(path_str):
    path = parse_path(path_str)
    xs = [seg.start.real for seg in path] + [seg.end.real for seg in path]
    return min(xs), max(xs)


def align_sleeve_halves(min_path_str: str, min_path_name: str, max_path_str: str, max_path_name: str, offset: int=0) -> tuple:
    sleeve_piece_modifiers = {}
    min_path = parse_path(min_path_str)
    max_path = parse_path(max_path_str)
    v1, n1 = get_sleeve_edge_vertices(min_path, mode='min')
    v2, n2 = get_sleeve_edge_vertices(max_path, mode='max')
    min_path_rotated, min_angle = rotate_path_to_horizontal(min_path, v1, n1)
    max_path_rotated, max_angle = rotate_path_to_horizontal(max_path, v2, n2)

    midpoint = (v1 + v2) / 2 + offset
    min_offset = midpoint - v1
    max_offset = midpoint - v2
    aligned_min_path = min_path_rotated.translated(min_offset)
    aligned_max_path = max_path_rotated.translated(max_offset)

    sleeve_piece_modifiers[min_path_name] = {"translation": (min_offset.real, min_offset.imag), "rotation": round(min_angle, 2)}
    sleeve_piece_modifiers[max_path_name] = {"translation": (max_offset.real, max_offset.imag), "rotation": round(max_angle, 2)}

    return aligned_min_path, aligned_max_path, sleeve_piece_modifiers


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


def rotate_path_to_horizontal(path: Path, edge_start, edge_end) -> tuple:
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

    return restored, angle


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
        if child.tag.endswith('seams'):
            seamdefinition = child
            break
    else:
        raise ValueError("No <seams> tag found in metadata")

    ns = f'{{{namespace}}}' if namespace else ''
    seams = []

    for seam_elem in seamdefinition.findall(f'{ns}seam'):
        seam_id = int(seam_elem.find(f'{ns}id').text)
        seamparts = []

        for part_elem in seam_elem.findall(f'{ns}seampart'):
            part = part_elem.find(f'{ns}part').text
            start = int(part_elem.find(f'{ns}start').text)
            end = int(part_elem.find(f'{ns}end').text)
            # direction = part_elem.find(f'{ns}direction').text.lower() == 'true'  # :/
            seamparts.append(Seampart(part, start, end))

        seams.append(Seam(seam_id, seamparts))

    return seams

