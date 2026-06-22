from PyQt5.QtWidgets import QDialog, QVBoxLayout

from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel


class DependencyGraphDialog(QDialog):
    """Dialog wrapper around the embeddable dependency graph panel."""

    _FORWARDED_PANEL_ATTRS = {
        "_depth_combo",
        "_edge_count",
        "_find_btn",
        "_full_graph_data",
        "_info_label",
        "_level_count",
        "_locate_target_callback",
        "_node_count",
        "_node_font",
        "_pending_focus_target",
        "_scope_depth",
        "_scope_label",
        "_scope_mode",
        "_scope_target",
        "_search_input",
        "_search_match_index",
        "_search_matches",
        "_summary_label",
        "edge_items",
        "graph_data",
        "highlighted_nodes",
        "initial_target",
        "level_lane_items",
        "node_icons",
        "node_items",
        "node_levels",
        "node_rects",
        "node_texts",
        "scene",
        "selected_node",
        "status_colors",
        "view",
    }

    def __init__(self, graph_data, status_colors, initial_target=None, locate_target_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dependency Graph")
        self.resize(920, 980)
        self.graph_panel = DependencyGraphPanel(
            graph_data,
            status_colors,
            initial_target=initial_target,
            locate_target_callback=locate_target_callback,
            parent=self,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graph_panel)

    def __getattr__(self, name):
        """Delegate graph-panel API and state for backward compatibility."""
        graph_panel = self.__dict__.get("graph_panel")
        if graph_panel is not None:
            return getattr(graph_panel, name)
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def __setattr__(self, name, value):
        """Delegate legacy graph-state writes to the embedded panel when present."""
        graph_panel = self.__dict__.get("graph_panel")
        if graph_panel is not None and name in self._FORWARDED_PANEL_ATTRS:
            setattr(graph_panel, name, value)
            return
        super().__setattr__(name, value)
