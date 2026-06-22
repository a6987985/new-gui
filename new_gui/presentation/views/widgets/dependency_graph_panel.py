"""Embeddable dependency graph panel reused by dialogs and main content views."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence, QPainter
from PyQt5.QtWidgets import (
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from new_gui.shared.config.settings import STATUS_CONFIG
from new_gui.presentation.views.dialogs.dependency_graph_export import DependencyGraphExportMixin
from new_gui.presentation.views.dialogs.dependency_graph_rendering import DependencyGraphRenderingMixin
from new_gui.presentation.views.dialogs.dependency_graph_state import DependencyGraphStateMixin
from new_gui.presentation.styles.dependency_graph_styles import (
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

    def __init__(self, scene, graph_panel, parent=None):
        super().__init__(scene, parent)
        self._graph_panel = graph_panel

    def wheelEvent(self, event):
        """Zoom in on wheel-up and zoom out on wheel-down."""
        delta_y = event.angleDelta().y()
        if delta_y > 0:
            self._graph_panel.zoom_in()
            event.accept()
            return
        if delta_y < 0:
            self._graph_panel.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Swallow view-level double-click handling to avoid dialog-close side effects."""
        event.accept()


class DependencyGraphPanel(
    DependencyGraphExportMixin,
    DependencyGraphRenderingMixin,
    DependencyGraphStateMixin,
    QWidget,
):
    """Embeddable dependency graph widget with toolbar, legend, and metadata."""

    _LEGEND_STATUS_ORDER = ["finish", "running", "failed", "skip", "scheduled", "pending", ""]

    def __init__(
        self,
        graph_data,
        status_colors,
        initial_target=None,
        locate_target_callback=None,
        show_auxiliary_controls=True,
        parent=None,
    ):
        super().__init__(parent)
        self._full_graph_data = graph_data
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.initial_target = initial_target
        self._locate_target_callback = locate_target_callback
        self._show_auxiliary_controls = bool(show_auxiliary_controls)
        self.node_items = {}
        self.edge_items = []
        self.node_rects = {}
        self.node_texts = {}
        self.node_icons = {}
        self.node_levels = {}
        self.level_lane_items = {}
        self.highlighted_nodes = set()
        self.selected_node = None
        self._node_font = QFont("Arial", 9, QFont.Bold)
        self._node_count = 0
        self._edge_count = 0
        self._level_count = 0
        self._search_matches = []
        self._search_match_index = -1
        self._pending_focus_target = initial_target
        self._pending_viewport_state = None
        self._pending_selected_target = None
        self._scope_mode = "full"
        self._scope_target = None
        self._scope_depth = None

        self.setMouseTracking(True)

        self.setup_ui()
        self.draw_graph()

    def _build_toolbar_row(self):
        """Return one compact toolbar row layout."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        return row

    def setup_ui(self):
        """Setup the panel UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.scene = QGraphicsScene()
        self.view = DependencyGraphView(self.scene, self)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setMouseTracking(True)
        self.view.setStyleSheet(build_dependency_graph_view_style())
        layout.addWidget(self.view, 1)

        self._auxiliary_controls_container = QWidget(self)
        auxiliary_layout = QVBoxLayout(self._auxiliary_controls_container)
        auxiliary_layout.setContentsMargins(0, 0, 0, 0)
        auxiliary_layout.setSpacing(4)

        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        btn_style = build_dependency_graph_toolbar_button_style()
        primary_toolbar = self._build_toolbar_row()
        secondary_toolbar = self._build_toolbar_row()
        search_toolbar = self._build_toolbar_row()

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
        locate_btn.setToolTip("Locate the selected target in the main tree and keep the graph open")
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
        auxiliary_layout.addLayout(controls_layout)

        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(6)
        legend_label = QLabel("Legend: ")
        legend_label.setStyleSheet(build_dependency_graph_heading_label_style())
        legend_layout.addWidget(legend_label)

        for status_key in self._iter_legend_status_keys():
            config = STATUS_CONFIG.get(status_key, {})
            text_color = config.get("text_color", "#333333")
            label_text = self._status_label(status_key)
            legend_item = QWidget()
            legend_item.setFocusPolicy(Qt.NoFocus)
            legend_item.setStyleSheet(
                build_dependency_graph_legend_item_style(self._status_color(status_key), text_color)
            )
            legend_item_layout = QHBoxLayout(legend_item)
            legend_item_layout.setContentsMargins(6, 2, 6, 2)
            legend_item_layout.setSpacing(0)

            text_label = QLabel(label_text)
            legend_item_layout.addWidget(text_label)
            legend_layout.addWidget(legend_item)

        legend_layout.addStretch()
        auxiliary_layout.addLayout(legend_layout)

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
        auxiliary_layout.addLayout(meta_layout)

        self._info_label = QLabel("Select a target, then use Trace Up or Trace Down.")
        self._info_label.setStyleSheet(build_dependency_graph_meta_label_style())
        self._info_label.setWordWrap(True)
        auxiliary_layout.addWidget(self._info_label)

        self._auxiliary_controls_container.setVisible(self._show_auxiliary_controls)
        layout.addWidget(self._auxiliary_controls_container)

        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for the panel."""
        shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut_esc.activated.connect(self.clear_highlights)

        shortcut_zoom_in = QShortcut(QKeySequence("Ctrl+="), self)
        shortcut_zoom_in.activated.connect(self.zoom_in)

        shortcut_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        shortcut_zoom_out.activated.connect(self.zoom_out)

        shortcut_fit = QShortcut(QKeySequence("Ctrl+0"), self)
        shortcut_fit.activated.connect(self.fit_view)

        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self._focus_search_input)

    def _capture_viewport_state(self):
        """Capture current graph viewport center and zoom transform."""
        return {
            "transform": self.view.transform(),
            "center": self.view.mapToScene(self.view.viewport().rect().center()),
        }

    def _restore_viewport_state(self, viewport_state) -> bool:
        """Restore graph viewport center and zoom transform."""
        if not viewport_state:
            return False
        transform = viewport_state.get("transform")
        center = viewport_state.get("center")
        if transform is None or center is None:
            return False
        self.view.setTransform(transform)
        self.view.centerOn(center)
        return True

    def set_graph_data(
        self,
        graph_data,
        initial_target=None,
        locate_target_callback=None,
        preserve_viewport: bool = False,
    ) -> None:
        """Replace graph content while preserving the reusable panel widget instance."""
        self._pending_viewport_state = None
        self._pending_selected_target = None
        graph_data_unchanged = graph_data == self._full_graph_data
        self.initial_target = initial_target
        self._locate_target_callback = locate_target_callback
        if graph_data_unchanged and self._scope_mode == "full":
            self._pending_focus_target = initial_target
            focus_node = self._resolve_graph_node(initial_target)
            if focus_node and focus_node in self.node_rects and focus_node != self.selected_node:
                self.select_node(focus_node)
            return
        preserve_current_viewport = preserve_viewport and self._scope_mode == "full"
        if preserve_current_viewport and self.scene.items():
            self._pending_viewport_state = self._capture_viewport_state()
            if self.selected_node:
                self._pending_selected_target = self._node_representative_target(self.selected_node)
        self._full_graph_data = graph_data
        self.graph_data = graph_data
        self._pending_focus_target = initial_target
        self._scope_mode = "full"
        self._scope_target = None
        self._scope_depth = None
        self._depth_combo.setCurrentText("Full")
        self._search_input.setText("")
        self._reset_search_state()
        self.draw_graph()

    def selected_display_target(self) -> str:
        """Return the representative real target for the selected graph node."""
        if not self.selected_node:
            return ""
        representative = str(self._node_representative_target(self.selected_node) or "").strip()
        if representative and not representative.startswith("__group__"):
            return representative

        members = [
            str(name).strip()
            for name in self._node_members(self.selected_node)
            if str(name).strip() and not str(name).strip().startswith("__group__")
        ]
        if members:
            return members[0]

        selected_node = str(self.selected_node or "").strip()
        if selected_node and not selected_node.startswith("__group__"):
            return selected_node
        return ""

    def selected_action_targets(self) -> list:
        """Return actionable real targets represented by the selected graph node."""
        if not self.selected_node:
            return []
        members = [
            str(name).strip()
            for name in self._node_members(self.selected_node)
            if str(name).strip() and not str(name).strip().startswith("__group__")
        ]
        if members:
            return members
        display_target = self.selected_display_target()
        return [display_target] if display_target else []

    def apply_theme(self, theme_name: str) -> None:
        """Apply a lightweight graph-canvas background update for the active theme."""
        normalized_theme = (theme_name or "").strip().lower()
        self.view.setBackgroundBrush(Qt.black if normalized_theme == "dark" else Qt.white)

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
        """Reset zoom and position to default."""
        self.view.resetTransform()
        self.fit_view()
