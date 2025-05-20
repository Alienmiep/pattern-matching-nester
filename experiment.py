import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QPushButton,
    QMainWindow, QFileDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit
)
from PyQt5.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt5.QtCore import Qt
import xml.etree.ElementTree as ET
from svg.path import parse_path
from svg.path.path import Line, CubicBezier, QuadraticBezier, Arc, Move

def svg_path_to_qpainterpath(svg_path_d, arc_segment_steps=20):
    svg_parsed = parse_path(svg_path_d)
    qp_path = QPainterPath()
    current_point = None

    for segment in svg_parsed:
        if isinstance(segment, Move):
            current_point = segment.end
            qp_path.moveTo(current_point.real, current_point.imag)

        elif isinstance(segment, Line):
            current_point = segment.end
            qp_path.lineTo(current_point.real, current_point.imag)

        elif isinstance(segment, QuadraticBezier):
            qp_path.quadTo(
                segment.control.real, segment.control.imag,
                segment.end.real, segment.end.imag
            )
            current_point = segment.end

        elif isinstance(segment, CubicBezier):
            qp_path.cubicTo(
                segment.control1.real, segment.control1.imag,
                segment.control2.real, segment.control2.imag,
                segment.end.real, segment.end.imag
            )
            current_point = segment.end

        elif isinstance(segment, Arc):
            # Approximate the arc with line segments
            for i in range(arc_segment_steps + 1):
                t = i / arc_segment_steps
                point = segment.point(t)
                if i == 0:
                    qp_path.lineTo(point.real, point.imag)
                else:
                    qp_path.lineTo(point.real, point.imag)
            current_point = segment.end

    return qp_path

class PathItem(QGraphicsPathItem):
    def __init__(self, path: QPainterPath, attributes: dict, element=None, viewer=None):
        super().__init__(path)
        self.attributes = attributes
        self.element = element  # <path> XML element
        self.viewer = viewer
        self.setAcceptHoverEvents(True)
        self.setBrush(QColor(100, 200, 255, 80))
        self.setPen(QPen(Qt.black, 1))

    def mousePressEvent(self, event):
        print("Clicked path with attributes:", self.attributes)
        if self.viewer:
            text = "\n".join(f"{k}: {v}" for k, v in self.attributes.items())
            self.viewer.path_info.setPlainText(text)
            self.viewer.current_path_item = self
        event.accept()

    def hoverEnterEvent(self, event):
        self.setBrush(QColor(255, 0, 0, 120))

    def hoverLeaveEvent(self, event):
        self.setBrush(QColor(100, 200, 255, 80))


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


class SvgPathViewer(QMainWindow):
    def __init__(self, svg_path):
        super().__init__()
        self.setWindowTitle("Interactive SVG Path Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.showMaximized()

        # Main widget and layout
        main_widget = QWidget()
        layout = QHBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # --- Side Panel ---
        self.side_panel = QWidget()
        self.side_panel.setMinimumWidth(300)
        side_layout = QVBoxLayout()
        self.side_panel.setLayout(side_layout)

        # Content: path info display
        self.path_info = QTextEdit()
        self.path_info.setReadOnly(False)
        side_layout.addWidget(QLabel("Path Attributes"))
        side_layout.addWidget(self.path_info)

        # Save button
        self.save_button = QPushButton("Save Changes to SVG")
        side_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_svg)

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

        self.current_path_item = None
        self.svg_tree = None
        self.svg_path = svg_path  # Save original file path
        self.load_svg(svg_path)

    def load_svg(self, svg_file):
        self.svg_tree = ET.parse(svg_file)
        root = self.svg_tree.getroot()

        # Handle namespaces
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        ET.register_namespace('', ns['svg'])

        # Extract <path> elements
        for path_elem in root.findall('.//svg:path', ns):
            d_attr = path_elem.attrib.get("d")
            print("Adding path with d:", d_attr[:50])  # preview
            if not d_attr:
                continue
            try:
                painter_path = svg_path_to_qpainterpath(d_attr)
                item = PathItem(painter_path, path_elem.attrib, path_elem, viewer=self)
                self.scene.addItem(item)
            except Exception as e:
                print(f"Error parsing path: {e}")

    def save_svg(self):
        if not self.current_path_item or not self.svg_tree:
            return

        element = self.current_path_item.element
        if element is None:
            return

        # Parse edited text back into attributes
        new_text = self.path_info.toPlainText()
        new_attrs = {}
        for line in new_text.strip().splitlines():
            if ':' not in line:
                continue
            key, value = map(str.strip, line.split(':', 1))
            new_attrs[key] = value

        # Update element attributes
        for key in list(element.attrib.keys()):
            if key not in new_attrs:
                del element.attrib[key]
        for key, value in new_attrs.items():
            element.set(key, value)

        # Ask where to save
        # filename, _ = QFileDialog.getSaveFileName(
        #     self, "Save SVG", self.svg_path, "SVG Files (*.svg)"
        # )
        filename = self.svg_path
        if filename:
            self.svg_tree.write(filename, encoding="utf-8", xml_declaration=True)
            print(f"Saved updated SVG to: {filename}")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load SVG via file dialog
    svg_file, _ = QFileDialog.getOpenFileName(None, "Open SVG File", "", "SVG Files (*.svg)")
    if svg_file:
        viewer = SvgPathViewer(svg_file)
        viewer.show()
        sys.exit(app.exec_())
