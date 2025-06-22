import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QPushButton,
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QGraphicsItem, QGraphicsEllipseItem
)
from PyQt5.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt5.QtCore import Qt, QPointF

from shapely import MultiPolygon, Polygon
from shapely.geometry import box
from shapely.ops import unary_union

from ifp import ifp

input_points = [(14.2, 147.0), (14.2, 154.0), (0.0, 154.0), (-14.2, 154.0), (-14.2, 147.0), (0.0, 147.0)]
reference_point = input_points[0]
fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]

remaining_pieces = [
    [(180.1, 147.0), (170.3, 147.0), (160.5, 147.0), (160.5, 154.0), (170.3, 154.0), (180.1, 154.0)],
    [(80.1, 111.0), (35.4, 148.6), (33.3, 145.3), (31.9, 142.1), (31.2, 139.1), (30.9, 136.2), (30.9, 133.3), (31.0, 130.5), (31.1, 127.6), (31.0, 124.8), (30.5, 121.8), (69.5, 98.3)],
    [(-80.1, 111.0), (-69.5, 98.3), (-30.5, 121.8), (-31.0, 124.8), (-31.1, 127.6), (-31.0, 130.5), (-30.9, 133.3), (-30.9, 136.2), (-31.2, 139.1), (-31.9, 142.1), (-33.3, 145.3), (-35.4, 148.6)],
    [(0.0, 94.8), (28.2, 94.8), (36.5, 94.8), (36.5, 129.3), (33.2, 128.9), (30.5, 129.2), (28.1, 130.2), (26.1, 131.8), (24.3, 133.9), (22.7, 136.6), (21.3, 139.8), (19.9, 143.4), (18.4, 147.4), (18.0, 148.8), (17.5, 150.1), (17.0, 151.5), (9.3, 153.3), (8.5, 149.9), (6.4, 147.0), (3.5, 145.1), (0.0, 144.4), (-3.5, 145.1), (-6.4, 147.0), (-8.5, 149.9), (-9.3, 153.3), (-17.0, 151.5), (-17.5, 150.1), (-18.0, 148.8), (-18.4, 147.4), (-19.9, 143.4), (-21.3, 139.8), (-22.7, 136.6), (-24.3, 133.9), (-26.1, 131.8), (-28.1, 130.2), (-30.5, 129.2), (-33.2, 128.9), (-36.5, 129.3), (-36.5, 94.8), (-28.2, 94.8)],
    [(170.3, 147.0), (173.5, 147.3), (176.7, 148.1), (179.6, 149.5), (187.3, 147.7), (186.2, 143.5), (185.3, 139.8), (184.7, 136.4), (184.5, 133.5), (184.9, 130.9), (185.9, 128.7), (187.6, 126.9), (190.3, 125.5), (190.3, 91.0), (170.3, 91.0), (150.3, 91.0), (150.3, 125.5), (152.9, 126.9), (154.7, 128.7), (155.7, 130.9), (156.0, 133.5), (155.8, 136.4), (155.2, 139.8), (154.3, 143.5), (153.3, 147.7), (160.9, 149.5), (163.9, 148.1), (167.0, 147.3)],
    [(250.4, 111.0), (239.8, 98.3), (200.7, 121.8), (200.8, 124.6), (200.6, 127.4), (200.2, 130.3), (199.9, 133.1), (199.8, 136.1), (200.2, 139.1), (201.2, 142.2), (203.1, 145.3), (203.9, 146.5), (204.8, 147.6), (205.7, 148.6)],
    [(90.1, 111.0), (134.9, 148.6), (135.8, 147.6), (136.6, 146.5), (137.5, 145.3), (139.3, 142.2), (140.3, 139.1), (140.7, 136.1), (140.7, 133.1), (140.4, 130.3), (140.0, 127.4), (139.8, 124.6), (139.8, 121.8), (100.8, 98.3)],
]
remaining_piece_count = 7

# convert to shapely shape
# get aabb
# find reference point
# draw reference point
# find IFP
# draw IFP
# find viable area
# translate piece

def vertices_to_qpainterpath(vertices: list):
    qp_path = QPainterPath()
    first_x, first_y = vertices[0]
    qp_path.moveTo(first_x, first_y)
    for vertex in vertices:
        qp_path.lineTo(vertex[0], vertex[1])
    # close polygon
    qp_path.lineTo(first_x, first_y)
    return qp_path

def bounding_box_from_polygon(poly_vertices: list) -> list:
    poly = Polygon(poly_vertices)
    minx, miny, maxx, maxy = poly.bounds
    bbox = box(minx, miny, maxx, maxy)
    return list(bbox.exterior.coords)[:-1]  # cut off duplicate closing point


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
    def __init__(self):
        super().__init__()
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
        self.show_ifp_button = QPushButton("Show IFP")
        side_layout.addWidget(self.show_ifp_button)
        self.show_ifp_button.clicked.connect(self.show_ifp)

        self.translate_piece_button = QPushButton("Translate pattern piece")
        side_layout.addWidget(self.translate_piece_button)
        self.translate_piece_button.clicked.connect(self.translate_piece)

        self.remove_ifp_rp_button = QPushButton("Remove IFP and reference point")
        side_layout.addWidget(self.remove_ifp_rp_button)
        self.remove_ifp_rp_button.clicked.connect(self.remove_ifp_rp)

        self.next_ifp_button = QPushButton("1) Show IFP for next piece")
        side_layout.addWidget(self.next_ifp_button)
        self.next_ifp_button.clicked.connect(self.next_ifp)

        self.fit_next_button = QPushButton("2) Fit next piece")
        side_layout.addWidget(self.fit_next_button)
        self.fit_next_button.clicked.connect(self.fit_next)

        self.advance_piece_button = QPushButton("3) Next piece")
        side_layout.addWidget(self.advance_piece_button)
        self.advance_piece_button.clicked.connect(self.advance_piece)

        # set up data structures
        self.shapes = {
            "fabric": fabric_vertices,
            "initial_piece": input_points
        }
        self.points_of_interest = [reference_point]
        self.advance_piece()

    def advance_piece(self) -> None:
        if not remaining_pieces:
            return

        # remove previous polygons, if needed
        self.shapes.pop("ifp", "")
        keys_to_remove = []
        for key in self.shapes:
            if "nfp" in key:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self.shapes.pop(key)
        self.points_of_interest = []

        self.current_piece = remaining_pieces.pop(0)
        self.current_piece_vertices = bounding_box_from_polygon(self.current_piece)
        self.piece_no = len(remaining_pieces) - remaining_piece_count + 1

        self.draw_everything()

    def draw_everything(self) -> None:
        self.scene.clear()
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

    def show_ifp(self) -> None:
        ifp_vertices = ifp(input_points, fabric_vertices)
        self.shapes["ifp"] = ifp_vertices
        self.shapes["ifp_color"] = "#FF0000"  # TODO rework this, the _color thing is a bit silly
        self.draw_everything()

    def translate_piece(self) -> None:
        ifp_vertices_sorted_by_appeal = list(sorted(self.shapes["ifp"]))
        target_point = ifp_vertices_sorted_by_appeal[0]
        translation = (target_point[0] - reference_point[0], target_point[1] - reference_point[1])
        self.shapes["initial_piece"] = [(x[0] + translation[0], x[1] + translation[1]) for x in input_points]
        # translate reference point as well
        self.points_of_interest = [(reference_point[0] + translation[0], reference_point[1] + translation[1])]
        self.draw_everything()

    def remove_ifp_rp(self) -> None:
        self.shapes.pop("ifp", "")
        keys_to_remove = []
        for key in self.shapes:
            if "nfp" in key:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self.shapes.pop(key)
        self.points_of_interest = []
        self.draw_everything()

    def next_ifp(self) -> None:
        self.shapes[f"piece_{self.piece_no}"] = self.current_piece_vertices
        self.points_of_interest = [self.current_piece_vertices[0]]
        ifp_vertices = ifp(self.current_piece_vertices, fabric_vertices)
        self.shapes["ifp"] = ifp_vertices
        self.draw_everything()

    def fit_next(self) -> None:
        reference_point_piece = self.current_piece_vertices[0]
        main_polygon = Polygon(self.shapes["ifp"])
        polygons_to_subtract = [Polygon(x) for key, x in self.shapes.items() if key not in ["fabric", "ifp", f"piece_{self.piece_no}"] and not "_color" in key]

        result = main_polygon
        for index, poly in enumerate(polygons_to_subtract):
            nfp = simple_nfp(poly, Polygon(self.current_piece_vertices), reference_point_piece)
            self.shapes[f"nfp_{index}"] = list(nfp.exterior.coords)
            self.shapes[f"nfp_{index}_color"] = "#0000FF"
            result = result.difference(nfp)

        coords = list(result.exterior.coords)[:-1]
        target_point = min(coords, key=lambda p: (p[0], p[1]))

        translation = (target_point[0] - reference_point_piece[0], target_point[1] - reference_point_piece[1])
        self.shapes[f"piece_{self.piece_no}"] = [(x[0] + translation[0], x[1] + translation[1]) for x in self.current_piece_vertices]
        # translate reference point as well
        self.points_of_interest = [(reference_point_piece[0] + translation[0], reference_point_piece[1] + translation[1])]
        self.draw_everything()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = PolygonViewer()
    viewer.show()
    sys.exit(app.exec_())
