import svgwrite
from svgpathtools import wsvg

def export_piece_to_svg(piece, filename, original_svg_attrs=None):
    """Export a Piece object directly to an SVG file using its existing Path."""
    dwg = svgwrite.Drawing(filename, profile='tiny')

    # Use svgpathtools to get the SVG path string
    svg_path_str = piece.path.d() + "Z"

    # for i, seg in enumerate(piece.path):
    #     print(f"Segment {i}: start={seg.start}, end={seg.end}")

    # for i in range(len(piece.path) - 1):
    #     if not abs(piece.path[i].end - piece.path[i+1].start) < 1e-5:
    #         print(f"Gap between segment {i} and {i+1}")

    if original_svg_attrs:
        for k, v in original_svg_attrs.items():
            dwg.attribs[k] = v

    dwg.add(dwg.path(d=svg_path_str, fill="none", stroke="black", stroke_width=0.2))
    dwg.save()



def save_debug_svg(paths, filename="debug.svg", colors=None):
    """
    Save a list of svgpathtools.Path objects to an SVG file for inspection.

    Arguments:
        paths: list of Path objects
        filename: string (output path)
        colors: list of stroke colors (optional)
    """
    if colors is None:
        # Default to black strokes
        colors = ["black"] * len(paths)

    wsvg(paths, filename=filename, stroke_widths=[1]*len(paths), colors=colors)
