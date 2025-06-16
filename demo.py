import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QPushButton,
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QGraphicsItem, QGraphicsEllipseItem
)
from PyQt5.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt5.QtCore import Qt, QPointF

from ifp import ifp

input_points = [(14.2, 147.0), (14.2, 154.0), (0.0, 154.0), (-14.2, 154.0), (-14.2, 147.0), (0.0, 147.0)]
reference_point = input_points[0]
fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]

def vertices_to_qpainterpath(vertices: list):
    qp_path = QPainterPath()
    first_x, first_y = vertices[0]
    qp_path.moveTo(first_x, first_y)
    for vertex in vertices:
        qp_path.lineTo(vertex[0], vertex[1])
    # close polygon
    qp_path.lineTo(first_x, first_y)
    return qp_path

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

        # set up data structures
        self.shapes = {
            "fabric": fabric_vertices,
            "initial_piece": input_points
        }
        self.points_of_interest = [reference_point]

        # draw pattern pieces and any highlighted vertices
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = PolygonViewer()
    viewer.show()
    sys.exit(app.exec_())
