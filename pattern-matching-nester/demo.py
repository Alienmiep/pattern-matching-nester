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
from svg_helper import *
from ifp import ifp
from nfp import nfp
from helper import INTERSECTION_PRECISION

# "pattern profile"
SVG_FILE = os.path.join(os.getcwd(), "data", "turtleneck_pattern_full.svg")
MERGE_PIECES = True
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
        if not self.current_piece.aabb:
            self.current_piece.aabb = bounding_box_from_polygon(self.current_piece.vertices)
        self.current_piece_vertices_draw = self.current_piece.vertices
        self.current_piece_vertices_calc = self.current_piece.aabb
        self.points_of_interest = [min(self.current_piece.vertices, key=lambda v: (v[0], v[1]))]

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
        self.current_piece.aabb = bounding_box_from_polygon(self.current_piece.vertices)
        self.current_piece_vertices_draw = self.current_piece.vertices
        self.current_piece_vertices_calc = self.current_piece.aabb
        self.shapes[f"piece_{self.current_piece.index}"] = self.current_piece_vertices_draw
        self.points_of_interest = [min(self.current_piece.vertices, key=lambda v: (v[0], v[1]))]

    def show_ifp(self) -> None:
        ifp_vertices = ifp(self.current_piece_vertices_calc, fabric_vertices)
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

        reference_point_piece = min(self.current_piece_vertices_calc, key=lambda v: (v[0], v[1]))
        main_polygon = Polygon(self.shapes["ifp"])
        polygons_to_subtract = [Polygon(x.aabb) for x in self.placed_pieces]

        result = main_polygon
        for index, poly in enumerate(polygons_to_subtract):
            print(poly)
            print(self.current_piece_vertices_calc)
            nfp_poly = nfp(poly, Polygon(self.current_piece_vertices_calc), reference_point_piece)
            self.shapes[f"nfp_{index}"] = list(nfp_poly.exterior.coords)
            self.shapes[f"nfp_{index}_color"] = "#0000FF"
            result_imprecise = result.difference(nfp_poly)
            result = set_precision(result_imprecise, INTERSECTION_PRECISION)
            print(result)

        if FABRIC_STRIPE_SWITCH:
            self.fabric_texture = generate_stripe_segments(result)
            target_point = min(
                (pt for line in self.fabric_texture for pt in line.coords),
                key=lambda p: (p[0], p[1])
            )
            print(target_point)
        else:  # just use IFP corner
            coords = list(result.exterior.coords)[:-1]
            target_point = min(coords, key=lambda p: (p[0], p[1]))

        translation = (target_point[0] - reference_point_piece[0], target_point[1] - reference_point_piece[1])
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
    for index, path in enumerate(paths):
        piece = Piece(index, path, unit_scale)
        piece.aabb = bounding_box_from_polygon(piece.vertices)
        pieces.append(piece)

    merged_pieces = reindex(merge_pieces_with_common_vertices(pieces, unit_scale)) if MERGE_PIECES else pieces
    for p in merged_pieces:
        print(f"Piece {p.index}, Area: {p.area()}")
    print("-------")
    merged_pieces.sort(key=lambda p: p.area(), reverse=True)
    for p in merged_pieces:
        print(f"Piece {p.index}, Area: {p.area()}")

    # seams = parse_svg_metadata(SVG_FILE)
    # for seam in seams:
    #     print(f"Seam ID: {seam.id}")
    #     for part in seam.seamparts:
    #         print(f"  Part: {part.part}, Start: {part.start}, End: {part.end}, Direction: {part.direction}")

    # full_pattern = Pattern(merged_pieces, seams)

    app = QApplication(sys.argv)
    viewer = PolygonViewer(merged_pieces)
    viewer.show()
    sys.exit(app.exec_())
