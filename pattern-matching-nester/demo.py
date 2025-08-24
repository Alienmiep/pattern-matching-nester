import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QPushButton,
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QGraphicsItem, QGraphicsEllipseItem
)
from PyQt5.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt5.QtCore import Qt, QPointF

from shapely import Polygon, LineString, MultiLineString, set_precision
from shapely.geometry import box

from models.piece import Piece
from models.pattern import Pattern
from svg_helper import *
from ifp import ifp
from nfp import nfp
from helper import INTERSECTION_PRECISION, find_valid_starting_position


# "pattern profile"
SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_with_seams.svg")
MERGE_PIECES = True  # TODO ensure piece names are read even when not merging
MERGE_SLEEVES = True
ALLOWED_CLASS_LISTS = []

fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]
stripe_spacing = 10
FABRIC_STRIPE_SWITCH = True


def vertices_to_qpainterpath(vertices: list) -> QPainterPath:
    qp_path = QPainterPath()
    first_x, first_y = vertices[0]
    qp_path.moveTo(first_x, first_y)
    for vertex in vertices:
        qp_path.lineTo(vertex[0], vertex[1])
    # close polygon
    qp_path.lineTo(first_x, first_y)
    return qp_path


def linestrings_to_qpainterpath(lines: list) -> QPainterPath:
    path = QPainterPath()
    for line in lines:
        coords = list(line.coords)
        if not coords:
            continue
        path.moveTo(*coords[0])
        for x, y in coords[1:]:
            path.lineTo(x, y)
    return path


def bounding_box_from_polygon(poly_vertices: list) -> list:
    poly = Polygon(poly_vertices)
    minx, miny, maxx, maxy = poly.bounds
    bbox = box(minx, miny, maxx, maxy)
    return list(bbox.exterior.coords)[:-1]  # cut off duplicate closing point


def generate_stripe_segments(ifp: Polygon) -> list:
    if ifp is None:
        ifp = Polygon(fabric_vertices)

    x_min, y_min, x_max, y_max = ifp.bounds

     # Generate horizontal stripe lines
    stripe_lines = [
        LineString([(x_min, y), (x_max, y)])
        for y in range(int(y_min), int(y_max) + 1, stripe_spacing)
    ]

    # Intersect each line with the IFP and flatten results
    result = []
    for line in stripe_lines:
        intersection = ifp.intersection(line)
        if not intersection.is_empty:
            if isinstance(intersection, LineString):
                result.append(intersection)
            elif isinstance(intersection, MultiLineString):
                result.extend(intersection.geoms)

    return result


def stretch_rectangle(rect: Polygon, offsets: tuple) -> Polygon:
    """
    Stretches an axis-aligned rectangle on the given axis.

    Parameters:
    - rect: A shapely Polygon representing a rectangle.
    - offsets: amount to move the corresponding side (min_x, max_x, min_y, max_y).

    Returns:
    - A new Polygon with the stretched shape.
    """
    coords = list(rect.exterior.coords)[:-1]
    minx, miny, maxx, maxy = rect.bounds
    new_coords = []

    for x, y in coords:
        if x == maxx:
            x += offsets[1]
        if x == minx:
            x -= offsets[0]
        if y == maxy:
            y += offsets[3]
        if y == miny:
            y -= offsets[2]
        new_coords.append((x, y))
    new_coords.append(new_coords[0])

    return Polygon(new_coords)


def simple_nfp(static_poly: Polygon, orbiting_poly: Polygon, reference_point: tuple) -> Polygon:
    # assumption: 2 rectangles and reference point is on a corner
    minx, miny, maxx, maxy = orbiting_poly.bounds
    max_x_offset = reference_point[0] - minx  # the offset FOR max x
    min_x_offset = maxx - reference_point[0]
    max_y_offset = reference_point[1] - miny
    min_y_offset = maxy - reference_point[1]
    static_poly = stretch_rectangle(static_poly, (min_x_offset, max_x_offset, min_y_offset, max_y_offset))
    return static_poly


def get_shared_seams_with_placed_pieces(current_piece: Piece, placed_pieces: list) -> list:
    affected_seams = []
    if placed_pieces:
        for placed_piece in placed_pieces:
            affected_seams.extend(full_pattern.find_seams_by_pair(current_piece.name, placed_piece.name))
        print(f"Found {len(affected_seams)} affected seam(s)")
    return affected_seams

# seams between the first two parts:
# [Seam(id=9, seamparts=[Seampart(part='left_ftorso', start=(17.0, 1.6751059804269488), end=(7.499999999999997, 0.0)), Seampart(part='left_btorso', start=(7.499999999999995, 0.0), end=(17.0, 1.6751068138012997))]),
#  Seam(id=10, seamparts=[Seampart(part='left_ftorso', start=(25.0, 44.204087141094675), end=(25.0, 21.69877899971849)), Seampart(part='left_btorso', start=(20.0, 21.698779833092836), end=(20.0, 44.20408749919405))]),
#  Seam(id=19, seamparts=[Seampart(part='right_ftorso', start=(17.500000000000004, 0.0), end=(8.0, 1.6751059804269488)), Seampart(part='right_btorso', start=(3.0, 1.6751068138012997), end=(12.500000000000005, 0.0))]),
#  Seam(id=20, seamparts=[Seampart(part='right_ftorso', start=(0.0, 21.69877899971849), end=(0.0, 44.204087141094675)), Seampart(part='right_btorso', start=(0.0, 44.20408749919405), end=(0.0, 21.698779833092836))])]


def select_reference_point(rp_candidates: list, current_piece: Piece, placed_pieces: list) -> tuple:
    # idea: assume the first candidate (start of seam)
    # check if a valid starting position can be found for each already placed piece
    # if not, try again for the other candidate
    # and if that one *also* doesn't work somehow, return an error so the program can try again with a different seam
    for candidate in rp_candidates:
        candidate_is_valid = True
        for piece in placed_pieces:
            candidate_is_valid = candidate_is_valid and bool(find_valid_starting_position(candidate, current_piece, piece))
        if candidate_is_valid:
            return candidate
    raise NotImplementedError("Neither of the reference point candidates are valid")


class PathItem(QGraphicsPathItem):
    def __init__(self, path: QPainterPath, attributes: dict, element=None, viewer=None):
        super().__init__(path)
        self.attributes = attributes
        self.element = element
        self.viewer = viewer
        self.setAcceptHoverEvents(True)
        color = QColor(attributes.get("color", "#000000"))
        self.setPen(QPen(color, 0.5))

    def get_points(self):
        """Extract individual vertex positions from the QPainterPath."""
        path = self.path()
        points = []
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            points.append(QPointF(el.x, el.y))
        return points

class VertexItem(QGraphicsEllipseItem):
    def __init__(self, point: QPointF, radius=1, parent=None):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.setPos(point)
        self.setBrush(QColor(255, 100, 100))
        self.setPen(QPen(Qt.black, 0.5))
        self.setZValue(1)  # Appear on top
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setToolTip(f"({point.x():.1f}, {point.y():.1f})")

    def mousePressEvent(self, event):
        print(f"Clicked vertex at: ({self.pos().x():.1f}, {self.pos().y():.1f})")
        super().mousePressEvent(event)


class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_factor = 1.15  # How fast zooming happens
        self.zoom_level = 0

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            zoom = self.zoom_factor
            self.zoom_level += 1
        else:
            zoom = 1 / self.zoom_factor
            self.zoom_level -= 1
        self.scale(zoom, zoom)


class PolygonViewer(QMainWindow):
    def __init__(self, pieces: list):
        super().__init__()
        self.pieces = pieces
        self.placed_pieces = []
        self.setWindowTitle("Interactive Algorithm Demo")
        self.setGeometry(100, 100, 800, 600)
        self.showMaximized()

        # Main widget and layout
        main_widget = QWidget()
        layout = QHBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # --- Side Panel ---
        self.side_panel = QWidget()
        self.side_panel.setMinimumWidth(200)
        side_layout = QVBoxLayout()
        self.side_panel.setLayout(side_layout)

        # --- Graphics View ---
        self.view = ZoomableGraphicsView(self)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # Add to layout: left = side panel, right = view
        layout.addWidget(self.side_panel, 1)   # 1 part
        layout.addWidget(self.view, 2)         # 2 parts

        # Buttons (to be pressed in order)
        self.fit_all_button = QPushButton("Fit all pieces :)")
        side_layout.addWidget(self.fit_all_button)
        self.fit_all_button.clicked.connect(self.fit_all)

        self.advance_piece_button = QPushButton("1) Show next piece")
        side_layout.addWidget(self.advance_piece_button)
        self.advance_piece_button.clicked.connect(self.advance_piece)

        self.show_ifp_button = QPushButton("2) Show IFP")
        side_layout.addWidget(self.show_ifp_button)
        self.show_ifp_button.clicked.connect(self.show_ifp)

        self.fit_piece_button = QPushButton("3) Translate piece")
        side_layout.addWidget(self.fit_piece_button)
        self.fit_piece_button.clicked.connect(self.fit_piece)

        self.clear_ifp_nfp_button = QPushButton("Remove IFP and NFPs")
        side_layout.addWidget(self.clear_ifp_nfp_button)
        self.clear_ifp_nfp_button.clicked.connect(self.clear_ifp_nfp)

        # set up data structures
        self.shapes = {
            "fabric": fabric_vertices
        }
        self.points_of_interest = []

        self.fabric_texture = generate_stripe_segments(None) if FABRIC_STRIPE_SWITCH else None
        self.draw_everything()

    def fit_all(self) -> None:
        while self.pieces:
            self.advance_piece()
            self.show_ifp()
            self.fit_piece()

    def clear_ifp_nfp(self) -> None:
        self.__clear_ifp_nfp()
        if FABRIC_STRIPE_SWITCH:
            self.fabric_texture = generate_stripe_segments(None)
        self.draw_everything()

    def __clear_ifp_nfp(self) -> None:
        self.shapes.pop("ifp", "")
        keys_to_remove = []
        for key in self.shapes:
            if "nfp" in key:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self.shapes.pop(key)
        self.points_of_interest = []

    def advance_piece(self) -> None:
        if not self.pieces:
            return

        self.__clear_ifp_nfp()  # remove previous polygons, if needed
        self.current_piece: Piece = self.pieces.pop(0)
        self.current_piece_vertices_draw = self.current_piece.vertices
        self.current_piece_vertices_calc = self.current_piece.vertices
        if not self.placed_pieces:
            self.current_piece.reference_point = min(self.current_piece.vertices, key=lambda v: (v[0], v[1]))
            self.points_of_interest = [self.current_piece.reference_point]

        self.shapes[f"piece_{self.current_piece.index}"] = self.current_piece_vertices_draw

        if FABRIC_STRIPE_SWITCH:
            self.fabric_texture = generate_stripe_segments(None)
        self.draw_everything()

    def draw_everything(self) -> None:
        self.scene.clear()
        if self.fabric_texture:
            self.draw_texture()
        for key, shape in self.shapes.items():
            if "color" in key:
                continue
            shape_path = vertices_to_qpainterpath(shape)
            attributes = {"color": self.shapes[f"{key}_color"]} if f"{key}_color" in self.shapes else {}
            item = PathItem(shape_path, attributes, viewer=self)
            self.scene.addItem(item)

        # Add vertex dot for interesting points
        for point in self.points_of_interest:
            dot = VertexItem(QPointF(point[0], point[1]))
            self.scene.addItem(dot)

    def draw_texture(self):
        texture_path = linestrings_to_qpainterpath(self.fabric_texture)
        item = PathItem(texture_path, {"color": "#bbbbbb"}, viewer=self)
        self.scene.addItem(item)

    def translate_current_piece(self, translation) -> None:
        self.current_piece.vertices = [(x[0] + translation[0], x[1] + translation[1]) for x in self.current_piece.vertices]
        self.current_piece_vertices_draw = self.current_piece.vertices
        self.current_piece_vertices_calc = self.current_piece.vertices
        self.shapes[f"piece_{self.current_piece.index}"] = self.current_piece_vertices_draw
        self.points_of_interest = [min(self.current_piece.vertices, key=lambda v: (v[0], v[1]))]

    def show_ifp(self) -> None:
        ifp_vertices = ifp(self.current_piece, fabric_vertices)
        if FABRIC_STRIPE_SWITCH:
            self.fabric_texture = generate_stripe_segments(Polygon(ifp_vertices))
        self.shapes["ifp"] = ifp_vertices
        self.shapes["ifp_color"] = "#FF0000"  # TODO rework this, the _color thing is a bit silly
        self.draw_everything()

    def fit_first_piece(self) -> None:
        reference_point = min(self.current_piece.vertices, key=lambda v: (v[0], v[1]))
        ifp_vertices_sorted_by_appeal = list(sorted(self.shapes["ifp"]))
        target_point = ifp_vertices_sorted_by_appeal[0]
        translation = (target_point[0] - reference_point[0], target_point[1] - reference_point[1])
        self.translate_current_piece(translation)
        self.placed_pieces.append(self.current_piece)
        self.draw_everything()

    def fit_piece(self) -> None:
        if not self.placed_pieces:
            self.fit_first_piece()
            return

        # see if the current piece shares any seams with previously placed pieces
        # prioritize matchable seams
        # select first seam, get 2 reference point pairs from it
        # test both for viability (throw error if neither of them are AND we have a matchable seam)
        # if there are no viable ones, find a different vertex on placed piece
        # reference points are relative to the NFP and one piece can have multiple for the different NFPs

        affected_seams = get_shared_seams_with_placed_pieces(self.current_piece, self.placed_pieces)
        if any([x.matchable for x in affected_seams]):
            # TODO get first matchable seam
            pass
        else:
            current_seam = affected_seams[0]

        # TODO move this to before the IFP is created (for all pieces, not just the second and beyond)
        # goal here: select a good reference point on the current (= orbiting) piece
        seampart_current_piece = current_seam.seamparts[0] if self.current_piece.name in current_seam.seamparts[0].part else current_seam.seamparts[1]
        reference_point_candidates = [self.current_piece.vertices[seampart_current_piece.start], self.current_piece.vertices[seampart_current_piece.end]]
        self.current_piece.reference_point = select_reference_point(reference_point_candidates, self.current_piece, self.placed_pieces)
        print("current piece vertices", self.current_piece.vertices)
        print("current piece reference point", self.current_piece.reference_point)

        # reference_point_piece = min(self.current_piece_vertices_calc, key=lambda v: (v[0], v[1]))
        main_polygon = Polygon(self.shapes["ifp"])
        # polygons_to_subtract = [Polygon(x.vertices) for x in self.placed_pieces]

        result = main_polygon
        for index, p in enumerate(self.placed_pieces):
            nfp_poly = nfp(p, self.current_piece, self.current_piece.reference_point)  # b_poly used to be Polygon(self.current_piece_vertices_calc)
            self.shapes[f"nfp_{index}"] = list(nfp_poly.exterior.coords)
            self.shapes[f"nfp_{index}_color"] = "#0000FF"
            result_imprecise = result.difference(nfp_poly)
            result = set_precision(result_imprecise, INTERSECTION_PRECISION)

        if FABRIC_STRIPE_SWITCH:
            self.fabric_texture = generate_stripe_segments(result)
            target_point = min(
                (pt for line in self.fabric_texture for pt in line.coords),
                key=lambda p: (p[0], p[1])
            )
        else:  # just use IFP corner
            coords = list(result.exterior.coords)[:-1]
            target_point = min(coords, key=lambda p: (p[0], p[1]))

        translation = (target_point[0] - self.current_piece.reference_point[0], target_point[1] - self.current_piece.reference_point[1])
        self.translate_current_piece(translation)
        self.placed_pieces.append(self.current_piece)
        self.draw_everything()

if __name__ == '__main__':
    if not os.path.exists(SVG_FILE):
            raise FileNotFoundError(f"SVG file not found: {SVG_FILE}")

    svg_attributes = get_svg_attributes(SVG_FILE)
    height = svg_attributes.get("height")
    unit_scale = 0.1 if "mm" in height else 1

    paths = load_selected_paths(SVG_FILE)

    pieces = []
    for index, path_tuple in enumerate(paths):
        name, path = path_tuple
        piece = Piece(index, name, path, unit_scale)
        pieces.append(piece)

    # for p in pieces:
    #     print(p)

    seams_raw = parse_svg_metadata(SVG_FILE)
    seams = correct_vertex_indices(seams_raw, pieces)
    # for seam in seams:
    #     print(f"Seam ID: {seam.id}")
    #     for part in seam.seamparts:
    #         print(f"  Part: {part.part}, Start: {part.start}, End: {part.end}")

    if MERGE_PIECES:
        unindexed_merged_pieces, index_mappings, merged_names = merge_pieces_with_common_vertices(pieces, unit_scale)
        merged_pieces = reindex(unindexed_merged_pieces)
        reduced_seams = reduce_seams(merged_pieces, seams)
        final_seams = remap_seams(reduced_seams, index_mappings, merged_names)
    else:
        merged_pieces = pieces
        final_seams = seams

    merged_pieces.sort(key=lambda p: p.area(), reverse=True)
    full_pattern = Pattern(merged_pieces, final_seams)

    app = QApplication(sys.argv)
    viewer = PolygonViewer(merged_pieces)
    viewer.show()
    sys.exit(app.exec_())
