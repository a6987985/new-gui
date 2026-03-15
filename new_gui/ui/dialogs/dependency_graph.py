import math
from collections import deque

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QFontMetrics, QKeySequence, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QComboBox,
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
    QLineEdit,
    QPushButton,
    QShortcut,
    QVBoxLayout,
)

from new_gui.config.settings import STATUS_CONFIG, logger


class DependencyGraphDialog(QDialog):
    """Enhanced dialog for displaying dependency graph visualization with interactive features."""

    _LEGEND_STATUS_ORDER = ["finish", "running", "failed", "skip", "scheduled", "pending", ""]

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
        self.resize(1200, 800)
        self._full_graph_data = graph_data
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.initial_target = initial_target
        self._locate_target_callback = locate_target_callback
        self.node_items = {}  # Store node positions for edge drawing
        self.edge_items = []  # Store edge items for highlighting
        self.node_rects = {}  # Store node rect items for interaction
        self.node_texts = {}  # Store node text items
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

    def _normalize_status_key(self, status):
        """Return a normalized status key used by graph styling."""
        return (status or "").strip().lower()

    def _status_label(self, status):
        """Return a user-facing status label."""
        return self._normalize_status_key(status) or "unknown"

    def _status_color(self, status):
        """Return the display color for a status or its fallback."""
        status_key = self._normalize_status_key(status)
        return self.status_colors.get(status_key, self.status_colors.get("", "#88D0EC"))

    def _iter_legend_status_keys(self):
        """Yield status keys in the preferred legend order."""
        for status_key in self._LEGEND_STATUS_ORDER:
            if status_key in STATUS_CONFIG:
                yield status_key

    def _trace_action_label(self, direction):
        """Return the user-facing action label for a trace direction."""
        return "Trace Down" if direction == "downstream" else "Trace Up"

    def _trace_direction_key(self, direction):
        """Return the canonical trace-target key for a direction."""
        return "downstream" if direction == "downstream" else "upstream"

    def _local_scope_semantics_message(self):
        """Return the user-facing description of local-scope trace behavior."""
        return (
            "Depth limits the visible local subgraph. "
            "Trace Up and Trace Down stay within the current local scope."
        )

    def _update_graph_metrics(self, nodes, edges, levels):
        """Update graph metrics shown in the dialog summary."""
        self._node_count = len(nodes)
        self._edge_count = len(edges)
        self._level_count = len(levels)
        self._summary_label.setText(
            f"Nodes: {self._node_count} | Edges: {self._edge_count} | Levels: {self._level_count}"
        )

    def _default_info_message(self):
        """Return the default message shown in the dialog info area."""
        if not self._node_count:
            return "No dependency data found for the current run."

        message = "Select a target, then use Trace Up or Trace Down."
        if self._scope_mode == "local":
            message = "Local view active. Select a target, then use Trace Up or Trace Down. "
            message += self._local_scope_semantics_message()
            message += " Use Show Full to restore the full graph."
        if self._node_count >= 80 or self._edge_count >= 160 or self._level_count >= 12:
            message += " Dense graph: zoom or trace a target to inspect details."
        return message

    def _set_info_message(self, message=None):
        """Set the action hint text shown in the dialog info area."""
        self._info_label.setText(message or self._default_info_message())

    def _node_interaction_hint(self):
        """Return the node interaction hint shown in tooltips."""
        if self._locate_target_callback is not None:
            return "Click to select\nDouble-click to locate in tree"
        return "Click to select"

    def _update_scope_label(self):
        """Update the scope label shown next to the graph summary."""
        if self._scope_mode == "local" and self._scope_target:
            depth_text = "Full" if self._scope_depth is None else str(self._scope_depth)
            self._scope_label.setText(
                f"Scope: Local ({self._scope_target}, Depth {depth_text}, Trace in scope)"
            )
            return
        self._scope_label.setText("Scope: Full graph")

    def _normalize_search_text(self, text):
        """Return normalized text used for target search."""
        return (text or "").strip().lower()

    def _matching_targets(self, search_text):
        """Return matching target names for a search query."""
        normalized_text = self._normalize_search_text(search_text)
        if not normalized_text:
            return []
        ordered_targets = [
            target_name
            for target_name, _ in self.graph_data.get("nodes", [])
            if target_name in self.node_rects
        ]
        return [
            target_name
            for target_name in ordered_targets
            if normalized_text in target_name.lower()
        ]

    def _reset_search_state(self):
        """Reset cached search navigation state."""
        self._search_matches = []
        self._search_match_index = -1

    def _focus_search_input(self):
        """Focus the in-graph search input."""
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _on_search_text_changed(self, text):
        """Update search state when the query changes."""
        self._reset_search_state()
        normalized_text = self._normalize_search_text(text)
        if not normalized_text:
            self._set_info_message()
            return

        self._search_matches = self._matching_targets(text)
        if not self._search_matches:
            self._set_info_message(f"No target matches '{text.strip()}'.")
            return

        self._set_info_message(
            f"Search found {len(self._search_matches)} target(s). Press Enter or click Find Next."
        )

    def _activate_search_match(self):
        """Select and center the current search match."""
        if not self._search_matches:
            return

        target_name = self._search_matches[self._search_match_index]
        self.select_node(target_name)
        self.view.centerOn(self.node_rects[target_name])
        self._set_info_message(
            f"Search match {self._search_match_index + 1}/{len(self._search_matches)}: {target_name}"
        )

    def find_next_target(self):
        """Find and focus the next matching target in the graph."""
        search_text = self._search_input.text()
        normalized_text = self._normalize_search_text(search_text)
        if not normalized_text:
            self._set_info_message("Enter a target name to search the graph.")
            self._focus_search_input()
            return

        current_matches = self._matching_targets(search_text)
        if not current_matches:
            self._reset_search_state()
            self._set_info_message(f"No target matches '{search_text.strip()}'.")
            return

        if current_matches != self._search_matches:
            self._search_matches = current_matches
            self._search_match_index = -1

        self._search_match_index = (self._search_match_index + 1) % len(self._search_matches)
        self._activate_search_match()

    def _apply_initial_view_state(self):
        """Fit the graph once shown and optionally focus the initial target."""
        if not self.scene.items():
            return

        self.fit_view()
        focus_target = self._pending_focus_target
        if focus_target and focus_target in self.node_rects:
            self.select_node(focus_target)
            self.view.centerOn(self.node_rects[focus_target])
        self._pending_focus_target = None

    def locate_selected_target_in_tree(self):
        """Close the dialog and locate the selected target in the main tree."""
        if not self.selected_node:
            self._set_info_message("Select a target first, then use Locate In Tree.")
            return
        if not self._locate_target_callback:
            self._set_info_message("Locate In Tree is not available in this context.")
            return

        target_name = self.selected_node
        self.accept()
        QTimer.singleShot(0, lambda: self._locate_target_callback(target_name))

    def _direct_adjacency(self, direction):
        """Return direct adjacency for the full graph in the requested direction."""
        adjacency = {}
        for source, target in self._full_graph_data.get("edges", []):
            key = source if direction == "downstream" else target
            value = target if direction == "downstream" else source
            adjacency.setdefault(key, []).append(value)
            adjacency.setdefault(value, adjacency.get(value, []))
        return adjacency

    def _collect_depth_limited_targets(self, start_target, adjacency, max_depth):
        """Collect targets reachable within the specified edge depth."""
        if max_depth is None:
            return set()

        reachable_targets = set()
        visited = {start_target}
        queue = deque([(start_target, 0)])

        while queue:
            current_target, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for next_target in adjacency.get(current_target, []):
                if next_target in visited:
                    continue
                visited.add(next_target)
                reachable_targets.add(next_target)
                queue.append((next_target, depth + 1))

        return reachable_targets

    def _build_local_subgraph(self, focus_target, depth_limit):
        """Build a local subgraph around the selected target."""
        local_targets = {focus_target}
        if depth_limit is None:
            full_trace_targets = self._full_graph_data.get("trace_targets", {})
            local_targets.update(full_trace_targets.get("upstream", {}).get(focus_target, []))
            local_targets.update(full_trace_targets.get("downstream", {}).get(focus_target, []))
        else:
            local_targets.update(
                self._collect_depth_limited_targets(focus_target, self._direct_adjacency("upstream"), depth_limit)
            )
            local_targets.update(
                self._collect_depth_limited_targets(focus_target, self._direct_adjacency("downstream"), depth_limit)
            )

        full_nodes = self._full_graph_data.get("nodes", [])
        full_edges = self._full_graph_data.get("edges", [])
        full_levels = self._full_graph_data.get("levels", {})
        full_trace_targets = self._full_graph_data.get("trace_targets", {})

        local_nodes = [
            (target_name, status)
            for target_name, status in full_nodes
            if target_name in local_targets
        ]
        local_edges = [
            (source, target)
            for source, target in full_edges
            if source in local_targets and target in local_targets
        ]
        local_levels = {}
        for level, targets in full_levels.items():
            scoped_targets = [target for target in targets if target in local_targets]
            if scoped_targets:
                local_levels[level] = scoped_targets

        local_trace_targets = {"upstream": {}, "downstream": {}}
        for direction_key in ("upstream", "downstream"):
            direction_targets = full_trace_targets.get(direction_key, {})
            local_trace_targets[direction_key] = {
                target_name: [
                    related_target
                    for related_target in direction_targets.get(target_name, [])
                    if related_target in local_targets
                ]
                for target_name in local_targets
            }

        return {
            "nodes": local_nodes,
            "edges": local_edges,
            "levels": local_levels,
            "trace_targets": local_trace_targets,
        }

    def show_local_subgraph(self):
        """Render a local dependency subgraph around the selected target."""
        focus_target = self.selected_node
        if not focus_target:
            self._set_info_message("Select a target first, then use Focus Local.")
            return

        depth_text = self._depth_combo.currentText()
        depth_limit = None if depth_text == "Full" else int(depth_text)
        self.graph_data = self._build_local_subgraph(focus_target, depth_limit)
        self._scope_mode = "local"
        self._scope_target = focus_target
        self._scope_depth = depth_limit
        self._pending_focus_target = focus_target
        self._update_scope_label()
        self._reset_search_state()
        self.draw_graph()

    def show_full_graph(self):
        """Restore the full graph after a local focus view."""
        focus_target = self.selected_node or self._scope_target or self.initial_target
        self.graph_data = self._full_graph_data
        self._scope_mode = "full"
        self._scope_target = None
        self._scope_depth = None
        self._pending_focus_target = focus_target
        self._update_scope_label()
        self._reset_search_state()
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
        highlight_up_btn.setToolTip("Trace Up from the selected target within the current scope")
        highlight_up_btn.clicked.connect(self.highlight_upstream)
        toolbar.addWidget(highlight_up_btn)

        highlight_down_btn = QPushButton("⬇ Trace Down")
        highlight_down_btn.setStyleSheet(btn_style)
        highlight_down_btn.setToolTip("Trace Down from the selected target within the current scope")
        highlight_down_btn.clicked.connect(self.highlight_downstream)
        toolbar.addWidget(highlight_down_btn)

        clear_btn = QPushButton("✕ Clear")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.setToolTip("Clear all highlights")
        clear_btn.clicked.connect(self.clear_highlights)
        toolbar.addWidget(clear_btn)

        toolbar.addSpacing(20)

        depth_label = QLabel("Depth:")
        depth_label.setStyleSheet("color: #555555; font-weight: 600;")
        toolbar.addWidget(depth_label)

        self._depth_combo = QComboBox()
        self._depth_combo.addItems(["Full", "1", "2", "3"])
        self._depth_combo.setCurrentText("Full")
        self._depth_combo.setToolTip("Depth limits the visible local subgraph around the selected target")
        self._depth_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px 10px;
                color: #333333;
                min-width: 72px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        toolbar.addWidget(self._depth_combo)

        focus_local_btn = QPushButton("Focus Local")
        focus_local_btn.setStyleSheet(btn_style)
        focus_local_btn.setToolTip(
            "Show a local subgraph around the selected target. "
            "Trace actions stay within the current scope."
        )
        focus_local_btn.clicked.connect(self.show_local_subgraph)
        toolbar.addWidget(focus_local_btn)

        show_full_btn = QPushButton("Show Full")
        show_full_btn.setStyleSheet(btn_style)
        show_full_btn.setToolTip("Restore the full dependency graph")
        show_full_btn.clicked.connect(self.show_full_graph)
        toolbar.addWidget(show_full_btn)

        toolbar.addSpacing(20)

        locate_btn = QPushButton("Locate In Tree")
        locate_btn.setStyleSheet(btn_style)
        locate_btn.setToolTip("Close the graph and locate the selected target in the main tree")
        locate_btn.clicked.connect(self.locate_selected_target_in_tree)
        locate_btn.setEnabled(self._locate_target_callback is not None)
        toolbar.addWidget(locate_btn)

        toolbar.addSpacing(20)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search targets...")
        self._search_input.setMinimumWidth(220)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 6px 10px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 1px solid #4A90D9;
            }
        """)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.returnPressed.connect(self.find_next_target)
        toolbar.addWidget(self._search_input)

        self._find_btn = QPushButton("Find Next")
        self._find_btn.setStyleSheet(btn_style)
        self._find_btn.setToolTip("Find the next target matching the search text")
        self._find_btn.clicked.connect(self.find_next_target)
        toolbar.addWidget(self._find_btn)

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

        for status_key in self._iter_legend_status_keys():
            config = STATUS_CONFIG.get(status_key, {})
            icon = config.get("icon", "")
            text_color = config.get("text_color", "#333333")
            label_text = self._status_label(status_key)
            icon_prefix = f"{icon} " if icon else ""
            legend_item = QLabel(f" {icon_prefix}{label_text} ")
            legend_item.setStyleSheet(
                f"background-color: {self._status_color(status_key)}; "
                f"color: {text_color}; border: 1px solid #999; border-radius: 3px; padding: 2px 6px;"
            )
            legend_layout.addWidget(legend_item)

        self._scope_label = QLabel("Scope: Full graph")
        self._scope_label.setStyleSheet("color: #666; font-size: 11px;")
        legend_layout.addWidget(self._scope_label)

        self._summary_label = QLabel("Nodes: 0 | Edges: 0 | Levels: 0")
        self._summary_label.setStyleSheet("color: #666; font-size: 11px;")
        legend_layout.addWidget(self._summary_label)

        legend_layout.addStretch()

        # Info label
        self._info_label = QLabel("Select a target, then use Trace Up or Trace Down.")
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

        # Ctrl+F to focus graph search
        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self._focus_search_input)

    def _draw_level_guides(self, sorted_levels, levels, node_positions):
        """Draw background bands and labels to make level structure explicit."""
        if not sorted_levels or not node_positions:
            return

        x_positions = [x_pos for x_pos, _ in node_positions.values()]
        if not x_positions:
            return

        lane_left = min(x_positions) - 220
        lane_right = max(x_positions) + 120
        lane_width = lane_right - lane_left
        lane_height = 68
        label_font = QFont("Arial", 10, QFont.Bold)
        meta_font = QFont("Arial", 8)
        lane_colors = ["#f4f8fc", "#edf4f9"]

        for lane_index, level in enumerate(sorted_levels):
            level_targets = [target_name for target_name in levels.get(level, []) if target_name in node_positions]
            if not level_targets:
                continue

            y_center = sum(node_positions[target_name][1] for target_name in level_targets) / len(level_targets)
            lane_top = y_center - lane_height / 2
            lane_color = QColor(lane_colors[lane_index % len(lane_colors)])
            lane_border = QColor("#d8e3ec")

            lane_item = QGraphicsRectItem(lane_left, lane_top, lane_width, lane_height)
            lane_item.setBrush(QBrush(lane_color))
            lane_item.setPen(QPen(lane_border, 1))
            lane_item.setZValue(-200)
            self.scene.addItem(lane_item)

            label_item = QGraphicsTextItem(f"Level {level}")
            label_item.setFont(label_font)
            label_item.setDefaultTextColor(QColor("#5b6b7c"))
            label_item.setPos(lane_left + 12, lane_top + 6)
            label_item.setZValue(-150)
            self.scene.addItem(label_item)

            target_count = len(level_targets)
            count_text = f"{target_count} target" if target_count == 1 else f"{target_count} targets"
            count_item = QGraphicsTextItem(count_text)
            count_item.setFont(meta_font)
            count_item.setDefaultTextColor(QColor("#7a8794"))
            count_item.setPos(lane_left + 12, lane_top + 26)
            count_item.setZValue(-150)
            self.scene.addItem(count_item)

    def draw_graph(self):
        """Draw the dependency graph using hierarchical layout."""
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self.node_rects.clear()
        self.node_texts.clear()
        self.highlighted_nodes.clear()
        self.selected_node = None

        nodes = self.graph_data.get('nodes', [])
        edges = self.graph_data.get('edges', [])
        levels = self.graph_data.get('levels', {})  # level -> [targets]
        self._update_graph_metrics(nodes, edges, levels)
        self._update_scope_label()

        if not nodes:
            text = QGraphicsTextItem("No dependency data found")
            text.setFont(QFont("Arial", 14))
            self.scene.addItem(text)
            self._search_input.setEnabled(False)
            self._find_btn.setEnabled(False)
            self._set_info_message()
            return

        self._search_input.setEnabled(True)
        self._find_btn.setEnabled(True)

        # Calculate positions using level-based layout
        node_positions = {}

        # Spacing
        level_height = 100
        node_width = 180

        y_offset = 50

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

            y_offset += level_height

        self._draw_level_guides(sorted_levels, levels, node_positions)

        # Draw edges first (so they appear behind nodes)
        self._draw_edges(edges, node_positions)

        # Draw nodes
        self._draw_nodes(nodes, node_positions)

        # Fit view after drawing
        self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self._set_info_message()
        QTimer.singleShot(0, self._apply_initial_view_state)

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
        status_key = self._normalize_status_key(status)
        status_label = self._status_label(status)
        color_hex = self._status_color(status)
        color = QColor(color_hex)

        # Create node rect with hover effect
        rect_item = InteractiveNodeItem(x - width/2, y - height/2, width, height, name, self)
        rect_item.setPen(QPen(QColor("#333333"), 2))
        rect_item.setBrush(QBrush(color))
        rect_item.setToolTip(
            f"Target: {name}\nStatus: {status_label}\n\n{self._node_interaction_hint()}"
        )
        rect_item.setCursor(Qt.PointingHandCursor)

        self.scene.addItem(rect_item)
        self.node_rects[name] = rect_item

        # Add status icon
        config = STATUS_CONFIG.get(status_key, {})
        icon = config.get("icon", "")
        icon_reserved_width = 0
        if icon:
            icon_item = QGraphicsTextItem(icon)
            icon_item.setFont(QFont("Arial", 10, QFont.Bold))
            icon_item.setDefaultTextColor(QColor(config.get("text_color", "#333333")))
            icon_item.setPos(x - width/2 + 5, y - icon_item.boundingRect().height()/2)
            self.scene.addItem(icon_item)
            icon_reserved_width = 18

        # Add text label
        available_text_width = max(40, width - 16 - icon_reserved_width)
        display_name = QFontMetrics(self._node_font).elidedText(name, Qt.ElideRight, available_text_width)
        text_item = QGraphicsTextItem(display_name)
        text_item.setFont(self._node_font)
        text_item.setDefaultTextColor(QColor("#000000"))
        if display_name != name:
            text_item.setToolTip(name)
        text_rect = text_item.boundingRect()
        text_center_x = x + (icon_reserved_width / 2)
        text_item.setPos(text_center_x - text_rect.width()/2, y - text_rect.height()/2)
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

    def _collect_trace_targets_from_edges(self, node, direction):
        """Collect trace targets from graph edges as a runtime fallback."""
        reachable_targets = []
        visited = set()
        queue = [node]
        edges = self.graph_data.get("edges", [])

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for source, target in edges:
                next_target = None
                if direction == "downstream" and source == current and target not in visited:
                    next_target = target
                elif direction != "downstream" and target == current and source not in visited:
                    next_target = source
                if next_target is None:
                    continue
                reachable_targets.append(next_target)
                queue.append(next_target)

        return reachable_targets

    def _get_trace_targets(self, node, direction):
        """Return canonical trace targets for a node and direction."""
        trace_targets = self.graph_data.get("trace_targets", {})
        direction_key = self._trace_direction_key(direction)
        direction_targets = trace_targets.get(direction_key, {})
        if node in direction_targets:
            return list(direction_targets.get(node) or [])
        return self._collect_trace_targets_from_edges(node, direction)

    def highlight_upstream(self):
        """Highlight upstream dependencies of selected node"""
        if not self.selected_node:
            self._set_info_message("Select a target first, then use Trace Up.")
            return
        self._trace_dependencies(self.selected_node, "upstream")

    def highlight_downstream(self):
        """Highlight downstream dependencies of selected node"""
        if not self.selected_node:
            self._set_info_message("Select a target first, then use Trace Down.")
            return
        self._trace_dependencies(self.selected_node, "downstream")

    def _trace_dependencies(self, node, direction):
        """Trace and highlight dependencies"""
        self.clear_highlights()

        related_targets = self._get_trace_targets(node, direction)
        nodes_to_highlight = {node, *related_targets}

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

        action_label = self._trace_action_label(direction)
        message = f"{action_label} highlighted {len(nodes_to_highlight)} targets from '{node}'."
        if self._scope_mode == "local":
            message += " Results are limited to the current local scope."
        self._set_info_message(message)

    def clear_highlights(self):
        """Clear all highlights and restore original colors"""
        self.selected_node = None
        self.highlighted_nodes.clear()

        # Restore nodes
        nodes = self.graph_data.get('nodes', [])
        for name, status in nodes:
            if name in self.node_rects:
                color_hex = self._status_color(status)
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

        self._set_info_message()

    def select_node(self, node_name):
        """Select a node for dependency tracing"""
        self.clear_highlights()
        self.selected_node = node_name

        if node_name in self.node_rects:
            rect_item = self.node_rects[node_name]
            rect_item.setPen(QPen(QColor("#4A90D9"), 3))
            rect_item.setZValue(100)

        self._set_info_message(f"Selected target: {node_name}. Use Trace Up or Trace Down.")

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

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to locate the node in the main tree."""
        if event.button() == Qt.LeftButton:
            self.dialog.select_node(self.name)
            self.dialog.locate_selected_target_in_tree()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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
