"""Rendering and highlight helpers for the dependency graph dialog."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QFontMetrics, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)

from new_gui.config.settings import STATUS_CONFIG


class DependencyGraphRenderingMixin:
    """Provide scene drawing and highlight behavior for the dependency graph dialog."""

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

        nodes = self.graph_data.get("nodes", [])
        edges = self.graph_data.get("edges", [])
        levels = self.graph_data.get("levels", {})
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

        node_positions = {}
        level_height = 100
        node_width = 180
        y_offset = 50
        sorted_levels = sorted(levels.keys())

        for level in sorted_levels:
            level_targets = levels[level]
            num_nodes = len(level_targets)
            total_width = num_nodes * node_width
            start_x = -total_width / 2 + node_width / 2

            for index, target_name in enumerate(level_targets):
                node_positions[target_name] = (start_x + index * node_width, y_offset)

            y_offset += level_height

        self._draw_level_guides(sorted_levels, levels, node_positions)
        self._draw_edges(edges, node_positions)
        self._draw_nodes(nodes, node_positions)

        self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self._set_info_message()
        QTimer.singleShot(0, self._apply_initial_view_state)

    def _draw_nodes(self, nodes, node_positions):
        """Draw all nodes with interactive elements."""
        for node_name, status in nodes:
            if node_name not in node_positions:
                continue
            x_pos, y_pos = node_positions[node_name]
            self._draw_node(node_name, status, x_pos, y_pos)

    def _draw_node(self, name, status, x_pos, y_pos):
        """Draw one interactive node at the specified position."""
        width = 150
        height = 40

        status_key = self._normalize_status_key(status)
        status_label = self._status_label(status)
        color_hex = self._status_color(status)
        color = QColor(color_hex)

        rect_item = InteractiveNodeItem(x_pos - width / 2, y_pos - height / 2, width, height, name, self)
        rect_item.setPen(QPen(QColor("#333333"), 2))
        rect_item.setBrush(QBrush(color))
        rect_item.setToolTip(
            f"Target: {name}\nStatus: {status_label}\n\n{self._node_interaction_hint()}"
        )
        rect_item.setCursor(Qt.PointingHandCursor)

        self.scene.addItem(rect_item)
        self.node_rects[name] = rect_item

        config = STATUS_CONFIG.get(status_key, {})
        icon = config.get("icon", "")
        icon_reserved_width = 0
        if icon:
            icon_item = QGraphicsTextItem(icon)
            icon_item.setFont(QFont("Arial", 10, QFont.Bold))
            icon_item.setDefaultTextColor(QColor(config.get("text_color", "#333333")))
            icon_item.setPos(x_pos - width / 2 + 5, y_pos - icon_item.boundingRect().height() / 2)
            self.scene.addItem(icon_item)
            icon_reserved_width = 18

        available_text_width = max(40, width - 16 - icon_reserved_width)
        display_name = QFontMetrics(self._node_font).elidedText(name, Qt.ElideRight, available_text_width)
        text_item = QGraphicsTextItem(display_name)
        text_item.setFont(self._node_font)
        text_item.setDefaultTextColor(QColor("#000000"))
        if display_name != name:
            text_item.setToolTip(name)
        text_rect = text_item.boundingRect()
        text_center_x = x_pos + (icon_reserved_width / 2)
        text_item.setPos(text_center_x - text_rect.width() / 2, y_pos - text_rect.height() / 2)
        self.scene.addItem(text_item)
        self.node_texts[name] = text_item
        self.node_items[name] = (x_pos, y_pos)

    def _draw_edges(self, edges, node_positions):
        """Draw all edges between nodes."""
        for source, target in edges:
            if source in node_positions and target in node_positions:
                x1, y1 = node_positions[source]
                x2, y2 = node_positions[target]
                self._draw_arrow(source, target, x1, y1 + 20, x2, y2 - 20)

    def _draw_arrow(self, source, target, x1, y1, x2, y2):
        """Draw one directional edge and keep its metadata for highlighting."""
        line_item = QGraphicsLineItem(x1, y1, x2, y2)
        line_item.setPen(QPen(QColor("#666666"), 1.5))
        line_item.setData(0, "edge")
        line_item.setData(1, source)
        line_item.setData(2, target)
        self.scene.addItem(line_item)
        self.edge_items.append(line_item)

        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10
        p1 = QPointF(
            x2 - arrow_size * math.cos(angle - math.pi / 6),
            y2 - arrow_size * math.sin(angle - math.pi / 6),
        )
        p2 = QPointF(
            x2 - arrow_size * math.cos(angle + math.pi / 6),
            y2 - arrow_size * math.sin(angle + math.pi / 6),
        )
        p3 = QPointF(x2, y2)

        arrow_item = QGraphicsPolygonItem(QPolygonF([p1, p2, p3]))
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
        """Highlight upstream dependencies of the selected node."""
        if not self.selected_node:
            self._set_info_message("Select a target first, then use Trace Up.")
            return
        self._trace_dependencies(self.selected_node, "upstream")

    def highlight_downstream(self):
        """Highlight downstream dependencies of the selected node."""
        if not self.selected_node:
            self._set_info_message("Select a target first, then use Trace Down.")
            return
        self._trace_dependencies(self.selected_node, "downstream")

    def _trace_dependencies(self, node, direction):
        """Trace and highlight dependencies from the selected node."""
        self.clear_highlights()

        related_targets = self._get_trace_targets(node, direction)
        nodes_to_highlight = {node, *related_targets}
        self.highlighted_nodes = nodes_to_highlight

        for name, rect_item in self.node_rects.items():
            if name in nodes_to_highlight:
                rect_item.setPen(QPen(QColor("#ff6600"), 3))
                rect_item.setZValue(100)
                continue

            base_color = rect_item.brush().color()
            rect_item.setPen(QPen(QColor("#333333"), 1))
            rect_item.setBrush(QBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 128)))
            rect_item.setZValue(0)

        for edge_item in self.edge_items:
            source = edge_item.data(1)
            target = edge_item.data(2)
            highlighted = source in nodes_to_highlight and target in nodes_to_highlight
            if highlighted and isinstance(edge_item, QGraphicsLineItem):
                edge_item.setPen(QPen(QColor("#ff6600"), 2.5))
            elif highlighted:
                edge_item.setBrush(QBrush(QColor("#ff6600")))
                edge_item.setPen(QPen(QColor("#ff6600"), 1))
            elif isinstance(edge_item, QGraphicsLineItem):
                edge_item.setPen(QPen(QColor("#cccccc"), 1))
            else:
                edge_item.setBrush(QBrush(QColor("#cccccc")))
                edge_item.setPen(QPen(QColor("#cccccc"), 1))
            edge_item.setZValue(100 if highlighted else 0)

        action_label = self._trace_action_label(direction)
        message = f"{action_label} highlighted {len(nodes_to_highlight)} targets from '{node}'."
        if self._scope_mode == "local":
            message += " Results are limited to the current local scope."
        self._set_info_message(message)

    def clear_highlights(self):
        """Clear all highlights and restore original colors."""
        self.selected_node = None
        self.highlighted_nodes.clear()

        for name, status in self.graph_data.get("nodes", []):
            if name not in self.node_rects:
                continue
            color_hex = self._status_color(status)
            self.node_rects[name].setPen(QPen(QColor("#333333"), 2))
            self.node_rects[name].setBrush(QBrush(QColor(color_hex)))
            self.node_rects[name].setZValue(0)

        for edge_item in self.edge_items:
            if isinstance(edge_item, QGraphicsLineItem):
                edge_item.setPen(QPen(QColor("#666666"), 1.5))
            else:
                edge_item.setBrush(QBrush(QColor("#666666")))
                edge_item.setPen(QPen(QColor("#666666"), 1))
            edge_item.setZValue(0)

        self._set_info_message()

    def select_node(self, node_name):
        """Select a node for dependency tracing."""
        self.clear_highlights()
        self.selected_node = node_name

        if node_name in self.node_rects:
            rect_item = self.node_rects[node_name]
            rect_item.setPen(QPen(QColor("#4A90D9"), 3))
            rect_item.setZValue(100)

        self._set_info_message(f"Selected target: {node_name}. Use Trace Up or Trace Down.")


class InteractiveNodeItem(QGraphicsRectItem):
    """Interactive node item that responds to clicks and hovers."""

    def __init__(self, x, y, width, height, name, dialog, parent=None):
        super().__init__(x, y, width, height, parent)
        self.name = name
        self.dialog = dialog
        self.setAcceptHoverEvents(True)
        self._original_brush = None

    def mousePressEvent(self, event):
        """Handle mouse click to select a node."""
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
        """Handle mouse hover to show a lighter preview."""
        self._original_brush = self.brush()
        self.setBrush(QBrush(self.brush().color().lighter(110)))
        self.setPen(QPen(QColor("#4A90D9"), 2))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle mouse leave and restore the current selection/highlight pen."""
        if self._original_brush:
            self.setBrush(self._original_brush)
        if self.name == self.dialog.selected_node:
            self.setPen(QPen(QColor("#4A90D9"), 3))
        elif self.name in self.dialog.highlighted_nodes:
            self.setPen(QPen(QColor("#ff6600"), 3))
        else:
            self.setPen(QPen(QColor("#333333"), 2))
        super().hoverLeaveEvent(event)
