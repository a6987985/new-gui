import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QKeySequence, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QShortcut,
    QVBoxLayout,
)

from new_gui.config.settings import STATUS_CONFIG, logger


class DependencyGraphDialog(QDialog):
    """Enhanced dialog for displaying dependency graph visualization with interactive features."""

    def __init__(self, graph_data, status_colors, parent=None):
        """
        Args:
            graph_data: dict with 'nodes' (list of (name, status)) and 'edges' (list of (source, target))
            status_colors: dict mapping status to color hex codes
        """
        super().__init__(parent)
        self.setWindowTitle("Dependency Graph")
        self.resize(1200, 800)
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.node_items = {}  # Store node positions for edge drawing
        self.edge_items = []  # Store edge items for highlighting
        self.node_rects = {}  # Store node rect items for interaction
        self.node_texts = {}  # Store node text items
        self.highlighted_nodes = set()  # Currently highlighted nodes
        self.selected_node = None  # Currently selected node

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Setup UI
        self.setup_ui()

        # Draw the graph
        self.draw_graph()

    def setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Graphics View with enhanced interaction
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setMouseTracking(True)
        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: #fafafa;
                border: 1px solid #cccccc;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.view)

        # Toolbar with enhanced buttons
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
                border: 1px solid #4A90D9;
            }
            QPushButton:pressed {
                background-color: #cce5ff;
            }
        """

        # Navigation buttons
        zoom_in_btn = QPushButton("🔍+ Zoom In")
        zoom_in_btn.setStyleSheet(btn_style)
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("🔍- Zoom Out")
        zoom_out_btn.setStyleSheet(btn_style)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)

        fit_btn = QPushButton("⊞ Fit View")
        fit_btn.setStyleSheet(btn_style)
        fit_btn.setToolTip("Fit all nodes in view")
        fit_btn.clicked.connect(self.fit_view)
        toolbar.addWidget(fit_btn)

        reset_btn = QPushButton("↺ Reset")
        reset_btn.setStyleSheet(btn_style)
        reset_btn.setToolTip("Reset zoom and position")
        reset_btn.clicked.connect(self.reset_view)
        toolbar.addWidget(reset_btn)

        toolbar.addSpacing(20)

        # Path highlighting buttons
        highlight_up_btn = QPushButton("⬆ Trace Up")
        highlight_up_btn.setStyleSheet(btn_style)
        highlight_up_btn.setToolTip("Highlight upstream dependencies (select a node first)")
        highlight_up_btn.clicked.connect(self.highlight_upstream)
        toolbar.addWidget(highlight_up_btn)

        highlight_down_btn = QPushButton("⬇ Trace Down")
        highlight_down_btn.setStyleSheet(btn_style)
        highlight_down_btn.setToolTip("Highlight downstream dependencies (select a node first)")
        highlight_down_btn.clicked.connect(self.highlight_downstream)
        toolbar.addWidget(highlight_down_btn)

        clear_btn = QPushButton("✕ Clear")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.setToolTip("Clear all highlights")
        clear_btn.clicked.connect(self.clear_highlights)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        # Export button
        export_btn = QPushButton("📷 Export PNG")
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(self.export_png)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Legend with icons
        legend_layout = QHBoxLayout()
        legend_label = QLabel("Legend: ")
        legend_label.setStyleSheet("font-weight: bold; color: #333;")
        legend_layout.addWidget(legend_label)

        for status, color in [("finish", "#98FB98"), ("running", "#FFFF00"),
                               ("failed", "#FF9999"), ("skip", "#FFDAB9"), ("pending", "#87CEEB")]:
            config = STATUS_CONFIG.get(status, {})
            icon = config.get("icon", "")
            legend_item = QLabel(f" {icon} {status} ")
            legend_item.setStyleSheet(f"background-color: {color}; border: 1px solid #999; border-radius: 3px; padding: 2px 6px;")
            legend_layout.addWidget(legend_item)

        legend_layout.addStretch()

        # Info label
        self._info_label = QLabel("Click a node to select. Use toolbar to trace dependencies.")
        self._info_label.setStyleSheet("color: #666; font-size: 11px;")
        legend_layout.addWidget(self._info_label)

        layout.addLayout(legend_layout)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for the dialog"""
        # Escape to clear selection
        shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut_esc.activated.connect(self.clear_highlights)

        # Ctrl+Plus for zoom in
        shortcut_zoom_in = QShortcut(QKeySequence("Ctrl+="), self)
        shortcut_zoom_in.activated.connect(self.zoom_in)

        # Ctrl+Minus for zoom out
        shortcut_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        shortcut_zoom_out.activated.connect(self.zoom_out)

        # Ctrl+0 for fit view
        shortcut_fit = QShortcut(QKeySequence("Ctrl+0"), self)
        shortcut_fit.activated.connect(self.fit_view)

    def draw_graph(self):
        """Draw the dependency graph using hierarchical layout."""
        nodes = self.graph_data.get('nodes', [])
        edges = self.graph_data.get('edges', [])
        levels = self.graph_data.get('levels', {})  # level -> [targets]

        if not nodes:
            text = QGraphicsTextItem("No dependency data found")
            text.setFont(QFont("Arial", 14))
            self.scene.addItem(text)
            return

        # Calculate positions using level-based layout
        node_positions = {}

        # Spacing
        level_height = 100
        node_width = 180

        y_offset = 50
        max_x = 0

        # Sort levels
        sorted_levels = sorted(levels.keys())

        for level in sorted_levels:
            level_targets = levels[level]
            num_nodes = len(level_targets)

            # Calculate starting x to center the level
            total_width = num_nodes * node_width
            start_x = -total_width / 2 + node_width / 2

            for i, target in enumerate(level_targets):
                x = start_x + i * node_width
                y = y_offset
                node_positions[target] = (x, y)
                max_x = max(max_x, abs(x) + node_width)

            y_offset += level_height

        # Draw edges first (so they appear behind nodes)
        self._draw_edges(edges, node_positions)

        # Draw nodes
        self._draw_nodes(nodes, node_positions)

        # Fit view after drawing
        self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))

    def _draw_nodes(self, nodes, node_positions):
        """Draw all nodes with interactive elements"""
        for node_name, status in nodes:
            if node_name not in node_positions:
                continue
            x, y = node_positions[node_name]
            self._draw_node(node_name, status, x, y)

    def _draw_node(self, name, status, x, y):
        """Draw a single interactive node at the specified position."""
        width = 150
        height = 40

        # Get color based on status
        color_hex = self.status_colors.get(status.lower(), "#87CEEB")
        color = QColor(color_hex)

        # Create node rect with hover effect
        rect_item = InteractiveNodeItem(x - width/2, y - height/2, width, height, name, self)
        rect_item.setPen(QPen(QColor("#333333"), 2))
        rect_item.setBrush(QBrush(color))
        rect_item.setToolTip(f"Target: {name}\nStatus: {status or 'pending'}\n\nClick to select")
        rect_item.setCursor(Qt.PointingHandCursor)

        self.scene.addItem(rect_item)
        self.node_rects[name] = rect_item

        # Add status icon
        config = STATUS_CONFIG.get(status.lower() if status else "", {})
        icon = config.get("icon", "")
        if icon:
            icon_item = QGraphicsTextItem(icon)
            icon_item.setFont(QFont("Arial", 10, QFont.Bold))
            icon_item.setDefaultTextColor(QColor(config.get("text_color", "#333333")))
            icon_item.setPos(x - width/2 + 5, y - icon_item.boundingRect().height()/2)
            self.scene.addItem(icon_item)

        # Add text label
        text_item = QGraphicsTextItem(name)
        text_item.setFont(QFont("Arial", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#000000"))
        text_rect = text_item.boundingRect()
        text_item.setPos(x - text_rect.width()/2, y - text_rect.height()/2)
        self.scene.addItem(text_item)
        self.node_texts[name] = text_item

        # Store position
        self.node_items[name] = (x, y)

    def _draw_edges(self, edges, node_positions):
        """Draw all edges between nodes"""
        for source, target in edges:
            if source in node_positions and target in node_positions:
                x1, y1 = node_positions[source]
                x2, y2 = node_positions[target]
                self._draw_arrow(source, target, x1, y1 + 20, x2, y2 - 20)

    def _draw_arrow(self, source, target, x1, y1, x2, y2):
        """Draw an arrow from (x1,y1) to (x2,y2) with metadata for highlighting."""
        # Draw line
        line_item = QGraphicsLineItem(x1, y1, x2, y2)
        line_item.setPen(QPen(QColor("#666666"), 1.5))
        line_item.setData(0, "edge")  # Mark as edge for identification
        line_item.setData(1, source)  # Store source
        line_item.setData(2, target)  # Store target
        self.scene.addItem(line_item)
        self.edge_items.append(line_item)

        # Calculate arrow head
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10

        # Arrow head points
        p1 = QPointF(x2 - arrow_size * math.cos(angle - math.pi/6),
                     y2 - arrow_size * math.sin(angle - math.pi/6))
        p2 = QPointF(x2 - arrow_size * math.cos(angle + math.pi/6),
                     y2 - arrow_size * math.sin(angle + math.pi/6))
        p3 = QPointF(x2, y2)

        # Draw arrow head
        arrow_head = QPolygonF([p1, p2, p3])
        arrow_item = QGraphicsPolygonItem(arrow_head)
        arrow_item.setBrush(QBrush(QColor("#666666")))
        arrow_item.setPen(QPen(QColor("#666666"), 1))
        arrow_item.setData(0, "arrow")
        arrow_item.setData(1, source)
        arrow_item.setData(2, target)
        self.scene.addItem(arrow_item)
        self.edge_items.append(arrow_item)

    def highlight_upstream(self):
        """Highlight upstream dependencies of selected node"""
        if not self.selected_node:
            self._info_label.setText("Please select a node first by clicking on it.")
            return
        self._trace_dependencies(self.selected_node, "upstream")

    def highlight_downstream(self):
        """Highlight downstream dependencies of selected node"""
        if not self.selected_node:
            self._info_label.setText("Please select a node first by clicking on it.")
            return
        self._trace_dependencies(self.selected_node, "downstream")

    def _trace_dependencies(self, node, direction):
        """Trace and highlight dependencies"""
        self.clear_highlights()

        nodes_to_highlight = set()
        nodes_to_highlight.add(node)

        edges = self.graph_data.get('edges', [])

        # Build adjacency list
        if direction == "downstream":
            # Find all nodes reachable from this node
            queue = [node]
            visited = set()
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                for source, target in edges:
                    if source == current and target not in visited:
                        nodes_to_highlight.add(target)
                        queue.append(target)
        else:
            # Find all nodes that can reach this node (upstream)
            queue = [node]
            visited = set()
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                for source, target in edges:
                    if target == current and source not in visited:
                        nodes_to_highlight.add(source)
                        queue.append(source)

        self.highlighted_nodes = nodes_to_highlight

        # Apply highlights
        for name, rect_item in self.node_rects.items():
            if name in nodes_to_highlight:
                rect_item.setPen(QPen(QColor("#ff6600"), 3))
                rect_item.setZValue(100)
            else:
                rect_item.setPen(QPen(QColor("#333333"), 1))
                rect_item.setBrush(QBrush(QColor(rect_item.brush().color().red(),
                                                   rect_item.brush().color().green(),
                                                   rect_item.brush().color().blue(), 128)))
                rect_item.setZValue(0)

        # Highlight edges
        for edge_item in self.edge_items:
            source = edge_item.data(1)
            target = edge_item.data(2)
            if source in nodes_to_highlight and target in nodes_to_highlight:
                if isinstance(edge_item, QGraphicsLineItem):
                    edge_item.setPen(QPen(QColor("#ff6600"), 2.5))
                else:
                    edge_item.setBrush(QBrush(QColor("#ff6600")))
                    edge_item.setPen(QPen(QColor("#ff6600"), 1))
                edge_item.setZValue(100)
            else:
                if isinstance(edge_item, QGraphicsLineItem):
                    edge_item.setPen(QPen(QColor("#cccccc"), 1))
                else:
                    edge_item.setBrush(QBrush(QColor("#cccccc")))
                    edge_item.setPen(QPen(QColor("#cccccc"), 1))
                edge_item.setZValue(0)

        self._info_label.setText(f"Highlighted {len(nodes_to_highlight)} nodes for {direction} trace from '{node}'")

    def clear_highlights(self):
        """Clear all highlights and restore original colors"""
        self.selected_node = None
        self.highlighted_nodes.clear()

        # Restore nodes
        nodes = self.graph_data.get('nodes', [])
        for name, status in nodes:
            if name in self.node_rects:
                color_hex = self.status_colors.get(status.lower(), "#87CEEB")
                self.node_rects[name].setPen(QPen(QColor("#333333"), 2))
                self.node_rects[name].setBrush(QBrush(QColor(color_hex)))
                self.node_rects[name].setZValue(0)

        # Restore edges
        for edge_item in self.edge_items:
            if isinstance(edge_item, QGraphicsLineItem):
                edge_item.setPen(QPen(QColor("#666666"), 1.5))
            else:
                edge_item.setBrush(QBrush(QColor("#666666")))
                edge_item.setPen(QPen(QColor("#666666"), 1))
            edge_item.setZValue(0)

        self._info_label.setText("Click a node to select. Use toolbar to trace dependencies.")

    def select_node(self, node_name):
        """Select a node for dependency tracing"""
        self.clear_highlights()
        self.selected_node = node_name

        if node_name in self.node_rects:
            rect_item = self.node_rects[node_name]
            rect_item.setPen(QPen(QColor("#4A90D9"), 3))
            rect_item.setZValue(100)

        self._info_label.setText(f"Selected: {node_name}. Click 'Trace Up' or 'Trace Down' to see dependencies.")

    def zoom_in(self):
        """Zoom in the view."""
        self.view.scale(1.2, 1.2)

    def zoom_out(self):
        """Zoom out the view."""
        self.view.scale(0.8, 0.8)

    def fit_view(self):
        """Fit the entire graph in the view."""
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def reset_view(self):
        """Reset zoom and position to default"""
        self.view.resetTransform()
        self.fit_view()

    def export_png(self):
        """Export the graph to a PNG file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Graph", "dependency_graph.png", "PNG Files (*.png)"
        )
        if file_path:
            from PyQt5.QtGui import QImage
            rect = self.scene.itemsBoundingRect()
            image = QImage(int(rect.width()) + 100, int(rect.height()) + 100, QImage.Format_ARGB32)
            image.fill(Qt.white)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            self.scene.render(painter)
            painter.end()

            image.save(file_path)
            logger.info(f"Graph exported to: {file_path}")


class InteractiveNodeItem(QGraphicsRectItem):
    """Interactive node item that responds to clicks and hovers"""

    def __init__(self, x, y, width, height, name, dialog, parent=None):
        super().__init__(x, y, width, height, parent)
        self.name = name
        self.dialog = dialog
        self.setAcceptHoverEvents(True)
        self._original_brush = None

    def mousePressEvent(self, event):
        """Handle mouse click to select node"""
        if event.button() == Qt.LeftButton:
            self.dialog.select_node(self.name)
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        """Handle mouse hover to show highlight"""
        self._original_brush = self.brush()
        # Create a slightly brighter version of the current color
        color = self.brush().color()
        lighter = color.lighter(110)
        self.setBrush(QBrush(lighter))
        self.setPen(QPen(QColor("#4A90D9"), 2))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle mouse leave to restore original color"""
        if self._original_brush:
            self.setBrush(self._original_brush)
        # Restore pen based on selection state
        if self.name == self.dialog.selected_node:
            self.setPen(QPen(QColor("#4A90D9"), 3))
        elif self.name in self.dialog.highlighted_nodes:
            self.setPen(QPen(QColor("#ff6600"), 3))
        else:
            self.setPen(QPen(QColor("#333333"), 2))
        super().hoverLeaveEvent(event)


