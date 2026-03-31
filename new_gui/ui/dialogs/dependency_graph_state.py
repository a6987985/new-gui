"""State, search, and scope helpers for the dependency graph dialog."""

from __future__ import annotations

from collections import deque

from PyQt5.QtCore import QTimer

from new_gui.config.settings import STATUS_CONFIG


class DependencyGraphStateMixin:
    """Provide stateful behavior shared by the dependency graph dialog shell."""

    def _node_meta(self, node_name):
        """Return metadata for the requested graph node."""
        return (self.graph_data.get("node_meta", {}) or {}).get(node_name, {})

    def _node_display_name(self, node_name):
        """Return the display label for the requested graph node."""
        return self._node_meta(node_name).get("display_name") or node_name

    def _node_members(self, node_name):
        """Return real target members represented by the requested graph node."""
        metadata = self._node_meta(node_name)
        members = list(metadata.get("members", []) or [])
        return members or ([node_name] if node_name else [])

    def _node_representative_target(self, node_name):
        """Return the real target used for locate-in-tree actions."""
        metadata = self._node_meta(node_name)
        return metadata.get("representative_target") or node_name

    def _resolve_graph_node(self, node_or_target_name):
        """Resolve a real target name to its graph-node id when grouped."""
        if not node_or_target_name:
            return node_or_target_name
        target_to_node = self.graph_data.get("target_to_node", {}) or {}
        return target_to_node.get(node_or_target_name, node_or_target_name)

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

        message = "Select a target to reveal connected edges, then use Trace Up or Trace Down."
        if self._scope_mode == "local":
            message = (
                "Local view active. Select a target to reveal connected edges, "
                "then use Trace Up or Trace Down. "
            )
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
            return "Click to select\nUse Locate In Tree to jump back"
        return "Click to select"

    def _update_scope_label(self):
        """Update the scope label shown next to the graph summary."""
        if self._scope_mode == "local" and self._scope_target:
            depth_text = "Full" if self._scope_depth is None else str(self._scope_depth)
            self._scope_label.setText(
                f"Scope: Local ({self._node_display_name(self._scope_target)}, Depth {depth_text}, Trace in scope)"
            )
            return
        self._scope_label.setText("Scope: Full graph")

    def _normalize_search_text(self, text):
        """Return normalized text used for target search."""
        return (text or "").strip().lower()

    def _matching_targets(self, search_text):
        """Return matching graph node ids for a search query."""
        normalized_text = self._normalize_search_text(search_text)
        if not normalized_text:
            return []
        ordered_targets = [
            target_name
            for target_name, _ in self.graph_data.get("nodes", [])
            if target_name in self.node_rects
        ]
        matches = []
        for target_name in ordered_targets:
            display_name = self._node_display_name(target_name).lower()
            member_names = [member.lower() for member in self._node_members(target_name)]
            if normalized_text in display_name or any(
                normalized_text in member_name for member_name in member_names
            ):
                matches.append(target_name)
        return matches

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
            f"Search match {self._search_match_index + 1}/{len(self._search_matches)}: "
            f"{self._node_display_name(target_name)}"
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
        focus_target = self._resolve_graph_node(self._pending_focus_target)
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

        target_name = self._node_representative_target(self.selected_node)
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
            "node_meta": {
                target_name: metadata
                for target_name, metadata in (self._full_graph_data.get("node_meta", {}) or {}).items()
                if target_name in local_targets
            },
            "target_to_node": {
                target_name: node_name
                for target_name, node_name in (self._full_graph_data.get("target_to_node", {}) or {}).items()
                if node_name in local_targets
            },
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
