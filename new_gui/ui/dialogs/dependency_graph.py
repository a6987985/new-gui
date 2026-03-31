from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence, QPainter
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QShortcut,
    QVBoxLayout,
)

from new_gui.config.settings import STATUS_CONFIG
from new_gui.ui.dialogs.dependency_graph_export import DependencyGraphExportMixin
from new_gui.ui.dialogs.dependency_graph_rendering import DependencyGraphRenderingMixin
from new_gui.ui.dialogs.dependency_graph_state import DependencyGraphStateMixin
from new_gui.ui.dependency_graph_styles import (
    build_dependency_graph_depth_combo_style,
    build_dependency_graph_heading_label_style,
    build_dependency_graph_legend_item_style,
    build_dependency_graph_meta_label_style,
    build_dependency_graph_search_input_style,
    build_dependency_graph_toolbar_button_style,
    build_dependency_graph_toolbar_label_style,
    build_dependency_graph_view_style,
)


class DependencyGraphView(QGraphicsView):
    """Graphics view with wheel-based zoom behavior."""

    def __init__(self, scene, dialog, parent=None):
        super().__init__(scene, parent)
        self._dialog = dialog

    def wheelEvent(self, event):
        """Zoom in on wheel-up and zoom out on wheel-down."""
        delta_y = event.angleDelta().y()
        if delta_y > 0:
            self._dialog.zoom_in()
            event.accept()
            return
        if delta_y < 0:
            self._dialog.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Swallow view-level double-click handling to avoid dialog-close side effects."""
        event.accept()


class DependencyGraphDialog(
    DependencyGraphExportMixin,
    DependencyGraphRenderingMixin,
    DependencyGraphStateMixin,
    QDialog,
):
    """Enhanced dialog for displaying dependency graph visualization with interactive features."""

    _LEGEND_STATUS_ORDER = ["finish", "running", "failed", "skip", "scheduled", "pending", ""]

    def _build_toolbar_row(self):
        """Return one compact toolbar row layout."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        return row

    def __init__(self, graph_data, status_colors, initial_target=None, locate_target_callback=None, parent=None):
        """
        Args:
            graph_data: dict with 'nodes' (list of (name, status)) and 'edges' (list of (source, target))
            status_colors: dict mapping status to color hex codes
            initial_target: optional target name to focus when the dialog opens
            locate_target_callback: optional callback used to locate a target in the main tree
        """
        super().__init__(parent)
        self.setWindowTitle("Dependency Graph")
        self.resize(920, 980)
        self._full_graph_data = graph_data
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.initial_target = initial_target
        self._locate_target_callback = locate_target_callback
        self.node_items = {}  # Store node positions for edge drawing
        self.edge_items = []  # Store edge items for highlighting
        self.node_rects = {}  # Store node rect items for interaction
        self.node_texts = {}  # Store node text items
        self.node_icons = {}  # Store node icon items
        self.node_levels = {}  # Store node-to-level mapping
        self.level_lane_items = {}  # Store level lane background items
        self.highlighted_nodes = set()  # Currently highlighted nodes
        self.selected_node = None  # Currently selected node
        self._node_font = QFont("Arial", 9, QFont.Bold)
        self._node_count = 0
        self._edge_count = 0
        self._level_count = 0
        self._search_matches = []
        self._search_match_index = -1
        self._pending_focus_target = initial_target
        self._scope_mode = "full"
        self._scope_target = None
        self._scope_depth = None

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
        self.view = DependencyGraphView(self.scene, self)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setMouseTracking(True)
        self.view.setStyleSheet(build_dependency_graph_view_style())
        layout.addWidget(self.view)

        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        btn_style = build_dependency_graph_toolbar_button_style()
        primary_toolbar = self._build_toolbar_row()
        secondary_toolbar = self._build_toolbar_row()
        search_toolbar = self._build_toolbar_row()

        # Navigation buttons
        zoom_in_btn = QPushButton("🔍+ Zoom In")
        zoom_in_btn.setStyleSheet(btn_style)
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        primary_toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("🔍- Zoom Out")
        zoom_out_btn.setStyleSheet(btn_style)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        primary_toolbar.addWidget(zoom_out_btn)

        fit_btn = QPushButton("⊞ Fit View")
        fit_btn.setStyleSheet(btn_style)
        fit_btn.setToolTip("Fit all nodes in view")
        fit_btn.clicked.connect(self.fit_view)
        primary_toolbar.addWidget(fit_btn)

        reset_btn = QPushButton("↺ Reset")
        reset_btn.setStyleSheet(btn_style)
        reset_btn.setToolTip("Reset zoom and position")
        reset_btn.clicked.connect(self.reset_view)
        primary_toolbar.addWidget(reset_btn)

        # Path highlighting buttons
        highlight_up_btn = QPushButton("⬆ Trace Up")
        highlight_up_btn.setStyleSheet(btn_style)
        highlight_up_btn.setToolTip("Trace Up from the selected target within the current scope")
        highlight_up_btn.clicked.connect(self.highlight_upstream)
        primary_toolbar.addWidget(highlight_up_btn)

        highlight_down_btn = QPushButton("⬇ Trace Down")
        highlight_down_btn.setStyleSheet(btn_style)
        highlight_down_btn.setToolTip("Trace Down from the selected target within the current scope")
        highlight_down_btn.clicked.connect(self.highlight_downstream)
        primary_toolbar.addWidget(highlight_down_btn)

        clear_btn = QPushButton("✕ Clear")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.setToolTip("Clear all highlights")
        clear_btn.clicked.connect(self.clear_highlights)
        primary_toolbar.addWidget(clear_btn)
        primary_toolbar.addStretch()

        depth_label = QLabel("Depth:")
        depth_label.setStyleSheet(build_dependency_graph_toolbar_label_style())
        secondary_toolbar.addWidget(depth_label)

        self._depth_combo = QComboBox()
        self._depth_combo.addItems(["Full", "1", "2", "3"])
        self._depth_combo.setCurrentText("Full")
        self._depth_combo.setToolTip("Depth limits the visible local subgraph around the selected target")
        self._depth_combo.setStyleSheet(build_dependency_graph_depth_combo_style())
        secondary_toolbar.addWidget(self._depth_combo)

        focus_local_btn = QPushButton("Focus Local")
        focus_local_btn.setStyleSheet(btn_style)
        focus_local_btn.setToolTip(
            "Show a local subgraph around the selected target. "
            "Trace actions stay within the current scope."
        )
        focus_local_btn.clicked.connect(self.show_local_subgraph)
        secondary_toolbar.addWidget(focus_local_btn)

        show_full_btn = QPushButton("Show Full")
        show_full_btn.setStyleSheet(btn_style)
        show_full_btn.setToolTip("Restore the full dependency graph")
        show_full_btn.clicked.connect(self.show_full_graph)
        secondary_toolbar.addWidget(show_full_btn)

        locate_btn = QPushButton("Locate In Tree")
        locate_btn.setStyleSheet(btn_style)
        locate_btn.setToolTip("Close the graph and locate the selected target in the main tree")
        locate_btn.clicked.connect(self.locate_selected_target_in_tree)
        locate_btn.setEnabled(self._locate_target_callback is not None)
        secondary_toolbar.addWidget(locate_btn)

        export_btn = QPushButton("📷 Export PNG")
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(self.export_png)
        secondary_toolbar.addWidget(export_btn)
        secondary_toolbar.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search targets...")
        self._search_input.setMinimumWidth(160)
        self._search_input.setMaximumWidth(280)
        self._search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet(build_dependency_graph_search_input_style())
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.returnPressed.connect(self.find_next_target)
        search_toolbar.addWidget(self._search_input)

        self._find_btn = QPushButton("Find Next")
        self._find_btn.setStyleSheet(btn_style)
        self._find_btn.setToolTip("Find the next target matching the search text")
        self._find_btn.clicked.connect(self.find_next_target)
        search_toolbar.addWidget(self._find_btn)
        search_toolbar.addStretch()

        controls_layout.addLayout(primary_toolbar)
        controls_layout.addLayout(secondary_toolbar)
        controls_layout.addLayout(search_toolbar)
        layout.addLayout(controls_layout)

        # Legend with icons
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(6)
        legend_label = QLabel("Legend: ")
        legend_label.setStyleSheet(build_dependency_graph_heading_label_style())
        legend_layout.addWidget(legend_label)

        for status_key in self._iter_legend_status_keys():
            config = STATUS_CONFIG.get(status_key, {})
            icon = config.get("icon", "")
            text_color = config.get("text_color", "#333333")
            label_text = self._status_label(status_key)
            icon_prefix = f"{icon} " if icon else ""
            legend_item = QLabel(f" {icon_prefix}{label_text} ")
            legend_item.setStyleSheet(
                build_dependency_graph_legend_item_style(self._status_color(status_key), text_color)
            )
            legend_layout.addWidget(legend_item)

        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(10)

        self._scope_label = QLabel("Scope: Full graph")
        self._scope_label.setStyleSheet(build_dependency_graph_meta_label_style())
        meta_layout.addWidget(self._scope_label)

        self._summary_label = QLabel("Nodes: 0 | Edges: 0 | Levels: 0")
        self._summary_label.setStyleSheet(build_dependency_graph_meta_label_style())
        meta_layout.addWidget(self._summary_label)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Info label
        self._info_label = QLabel("Select a target, then use Trace Up or Trace Down.")
        self._info_label.setStyleSheet(build_dependency_graph_meta_label_style())
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

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

        # Ctrl+F to focus graph search
        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self._focus_search_input)

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
