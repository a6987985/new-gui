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

    def _set_node_opacity(self, node_name, opacity):
        """Apply one opacity value across the node visuals."""
        if node_name in self.node_rects:
            self.node_rects[node_name].setOpacity(opacity)
        if node_name in self.node_texts:
            self.node_texts[node_name].setOpacity(opacity)
        if node_name in self.node_icons:
            self.node_icons[node_name].setOpacity(opacity)

    def _set_node_scale(self, node_name, scale):
        """Apply one scale value to the node body, text, and icon."""
        if node_name in self.node_rects:
            self.node_rects[node_name].setScale(scale)
        if node_name in self.node_texts:
            self.node_texts[node_name].setScale(scale)
        if node_name in self.node_icons:
            self.node_icons[node_name].setScale(scale)

    def _restore_level_lanes(self):
        """Restore all level-lane visuals to their default state."""
        for lane_item in self.level_lane_items.values():
            default_fill = lane_item.data(0)
            default_border = lane_item.data(1)
            lane_item.setBrush(QBrush(QColor(default_fill)))
            lane_item.setPen(QPen(QColor(default_border), 1))

    def _highlight_selected_level_lane(self, node_name):
        """Highlight the level lane containing the selected node."""
        selected_level = self.node_levels.get(node_name)
        lane_item = self.level_lane_items.get(selected_level)
        if lane_item is None:
            return
        lane_item.setBrush(QBrush(QColor("#dcebfa")))
        lane_item.setPen(QPen(QColor("#97bbe0"), 1.5))

    def _apply_deemphasis_to_other_nodes(self, active_nodes):
        """Fade non-active nodes slightly into the background."""
        active_node_set = set(active_nodes or [])
        for node_name in self.node_rects.keys():
            self._set_node_opacity(node_name, 1.0 if node_name in active_node_set else 0.74)

    def _apply_selected_node_visual(self, node_name):
        """Apply the focused visual treatment for the selected node."""
        if node_name not in self.node_rects:
            return

        rect_item = self.node_rects[node_name]
        rect_item.setPen(QPen(QColor("#2F80ED"), 3))
        rect_item.setBrush(QBrush(rect_item.brush().color().lighter(106)))
        rect_item.setZValue(120)
        self._set_node_opacity(node_name, 1.0)
        self._set_node_scale(node_name, 1.15)

        if node_name in self.node_texts:
            self.node_texts[node_name].setDefaultTextColor(QColor("#16324f"))
            self.node_texts[node_name].setZValue(125)
        if node_name in self.node_icons:
            self.node_icons[node_name].setZValue(125)

    def _reset_node_visuals(self):
        """Restore node visuals to their default unselected state."""
        for name, status in self.graph_data.get("nodes", []):
            if name not in self.node_rects:
                continue
            color_hex = self._status_color(status)
            self.node_rects[name].setPen(QPen(QColor("#333333"), 2))
            self.node_rects[name].setBrush(QBrush(QColor(color_hex)))
            self.node_rects[name].setZValue(0)
            self._set_node_opacity(name, 1.0)
            self._set_node_scale(name, 1.0)
            if name in self.node_texts:
                self.node_texts[name].setDefaultTextColor(QColor("#000000"))
                self.node_texts[name].setZValue(0)
            if name in self.node_icons:
                self.node_icons[name].setZValue(0)

    def _set_edge_item_hidden(self, edge_item):
        """Hide one edge item from the default graph view."""
        edge_item.setVisible(False)
        edge_item.setZValue(-50)

    def _set_edge_item_color(self, edge_item, color_hex, width=1.5):
        """Apply one color treatment to an edge line or arrow item."""
        color = QColor(color_hex)
        edge_item.setVisible(True)
        if isinstance(edge_item, QGraphicsLineItem):
            edge_item.setPen(QPen(color, width))
        else:
            edge_item.setBrush(QBrush(color))
            edge_item.setPen(QPen(color, 1))

    def _hide_all_edges(self):
        """Hide all graph edges in the default unselected state."""
        for edge_item in self.edge_items:
            self._set_edge_item_hidden(edge_item)

    def _edge_touches_node(self, edge_item, node_name):
        """Return whether the edge item connects to the requested node."""
        source = edge_item.data(1)
        target = edge_item.data(2)
        return source == node_name or target == node_name

    def _show_selected_node_edges(self, node_name):
        """Show only the direct edges connected to the selected node."""
        for edge_item in self.edge_items:
            if self._edge_touches_node(edge_item, node_name):
                self._set_edge_item_color(edge_item, "#4A90D9", 2.2)
                edge_item.setZValue(80)
            else:
                self._set_edge_item_hidden(edge_item)

    def _node_tooltip_text(self, node_name, status_label):
        """Return the tooltip text for a dependency node."""
        display_name = self._node_display_name(node_name)
        members = self._node_members(node_name)
        interaction_hint = self._node_interaction_hint()
        if len(members) <= 1:
            return f"Target: {display_name}\nStatus: {status_label}\n\n{interaction_hint}"

        preview_members = ", ".join(members[:4])
        remaining_count = len(members) - 4
        if remaining_count > 0:
            preview_members += f", and {remaining_count} more"
        return (
            f"Generic Group: {display_name}\n"
            f"Status: {status_label}\n"
            f"Members: {len(members)}\n"
            f"Includes: {preview_members}\n\n"
            f"{interaction_hint}"
        )

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
        lane_height = 52
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
            lane_item.setData(0, lane_color.name())
            lane_item.setData(1, lane_border.name())
            self.scene.addItem(lane_item)
            self.level_lane_items[level] = lane_item

            label_item = QGraphicsTextItem(f"Level {level}")
            label_item.setFont(label_font)
            label_item.setDefaultTextColor(QColor("#5b6b7c"))
            label_item.setPos(lane_left + 12, lane_top + 4)
            label_item.setZValue(-150)
            self.scene.addItem(label_item)

            target_count = len(level_targets)
            count_text = f"{target_count} node" if target_count == 1 else f"{target_count} nodes"
            count_item = QGraphicsTextItem(count_text)
            count_item.setFont(meta_font)
            count_item.setDefaultTextColor(QColor("#7a8794"))
            count_item.setPos(lane_left + 12, lane_top + 21)
            count_item.setZValue(-150)
            self.scene.addItem(count_item)

    def draw_graph(self):
        """Draw the dependency graph using hierarchical layout."""
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self.node_rects.clear()
        self.node_texts.clear()
        self.node_icons.clear()
        self.node_levels.clear()
        self.level_lane_items.clear()
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
        level_height = 76
        node_width = 180
        y_offset = 42
        sorted_levels = sorted(levels.keys())

        for level in sorted_levels:
            level_targets = levels[level]
            num_nodes = len(level_targets)
            total_width = num_nodes * node_width
            start_x = -total_width / 2 + node_width / 2

            for index, target_name in enumerate(level_targets):
                node_positions[target_name] = (start_x + index * node_width, y_offset)
                self.node_levels[target_name] = level

            y_offset += level_height

        self._draw_level_guides(sorted_levels, levels, node_positions)
        self._draw_edges(edges, node_positions)
        self._draw_nodes(nodes, node_positions)
        self._hide_all_edges()

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
        display_name = self._node_display_name(name)

        rect_item = InteractiveNodeItem(x_pos - width / 2, y_pos - height / 2, width, height, name, self)
        rect_item.setPen(QPen(QColor("#333333"), 2))
        rect_item.setBrush(QBrush(color))
        rect_item.setToolTip(self._node_tooltip_text(name, status_label))
        rect_item.setCursor(Qt.PointingHandCursor)
        rect_item.setTransformOriginPoint(rect_item.rect().center())

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
            icon_item.setTransformOriginPoint(icon_item.boundingRect().center())
            self.scene.addItem(icon_item)
            icon_reserved_width = 18
            self.node_icons[name] = icon_item

        available_text_width = max(40, width - 16 - icon_reserved_width)
        display_text = QFontMetrics(self._node_font).elidedText(
            display_name,
            Qt.ElideRight,
            available_text_width,
        )
        text_item = QGraphicsTextItem(display_text)
        text_item.setFont(self._node_font)
        text_item.setDefaultTextColor(QColor("#000000"))
        if display_text != display_name:
            text_item.setToolTip(display_name)
        elif len(self._node_members(name)) > 1:
            text_item.setToolTip(self._node_tooltip_text(name, status_label))
        text_rect = text_item.boundingRect()
        text_center_x = x_pos + (icon_reserved_width / 2)
        text_item.setPos(text_center_x - text_rect.width() / 2, y_pos - text_rect.height() / 2)
        text_item.setTransformOriginPoint(text_item.boundingRect().center())
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
        self.selected_node = node

        related_targets = self._get_trace_targets(node, direction)
        related_node_set = set(related_targets)
        nodes_to_highlight = {node, *related_node_set}
        self.highlighted_nodes = nodes_to_highlight
        self._apply_deemphasis_to_other_nodes(nodes_to_highlight)
        self._highlight_selected_level_lane(node)
        self._apply_selected_node_visual(node)

        for name in related_node_set:
            if name not in self.node_rects:
                continue
            self.node_rects[name].setPen(QPen(QColor("#ff8a3d"), 3))
            self.node_rects[name].setZValue(100)
            if name in self.node_texts:
                self.node_texts[name].setDefaultTextColor(QColor("#6a2e00"))
                self.node_texts[name].setZValue(105)
            if name in self.node_icons:
                self.node_icons[name].setZValue(105)

        for edge_item in self.edge_items:
            source = edge_item.data(1)
            target = edge_item.data(2)
            highlighted = source in nodes_to_highlight and target in nodes_to_highlight
            if highlighted and isinstance(edge_item, QGraphicsLineItem):
                self._set_edge_item_color(edge_item, "#ff6600", 2.5)
            elif highlighted:
                self._set_edge_item_color(edge_item, "#ff6600", 2.5)
            else:
                self._set_edge_item_hidden(edge_item)
            edge_item.setZValue(100 if highlighted else -50)

        action_label = self._trace_action_label(direction)
        message = (
            f"{action_label} highlighted {len(nodes_to_highlight)} nodes from "
            f"'{self._node_display_name(node)}'."
        )
        if self._scope_mode == "local":
            message += " Results are limited to the current local scope."
        self._set_info_message(message)

    def clear_highlights(self):
        """Clear all highlights and restore original colors."""
        self.selected_node = None
        self.highlighted_nodes.clear()
        self._reset_node_visuals()
        self._restore_level_lanes()
        self._hide_all_edges()

        self._set_info_message()

    def select_node(self, node_name):
        """Select a node for dependency tracing."""
        self.clear_highlights()
        self.selected_node = node_name
        self._apply_deemphasis_to_other_nodes({node_name})
        self._highlight_selected_level_lane(node_name)
        self._apply_selected_node_visual(node_name)
        self._show_selected_node_edges(node_name)
        self._set_info_message(
            f"Selected target: {self._node_display_name(node_name)}. Use Trace Up or Trace Down."
        )


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
        """Handle double-click without closing the graph dialog."""
        if event.button() == Qt.LeftButton:
            self.dialog.select_node(self.name)
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
            self.setPen(QPen(QColor("#2F80ED"), 3))
        elif self.name in self.dialog.highlighted_nodes:
            self.setPen(QPen(QColor("#ff8a3d"), 3))
        else:
            self.setPen(QPen(QColor("#333333"), 2))
        super().hoverLeaveEvent(event)
