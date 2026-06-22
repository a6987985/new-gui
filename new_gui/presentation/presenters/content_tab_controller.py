"""Content-tab orchestration for main view and embedded dependency graph."""

from __future__ import annotations

from new_gui.model.services import status_summary
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_run_selection as run_selection
from new_gui.model.services import view_tabs
from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel
from new_gui.presentation.presenters import external_scrollbar_controller


def _build_locate_target_callback(window, return_context: dict):
    """Build one locate callback bound to the captured return context."""
    return lambda target_name, context=return_context: window.locate_target_in_tree(
        target_name,
        context,
    )


def _current_run_name(window) -> str:
    """Return the current combo-selected run name."""
    if not hasattr(window, "combo"):
        return ""
    run_name = window.combo.currentText()
    if run_selection.is_unavailable_run_entry(run_name):
        return ""
    return run_selection.normalize_run_name(run_name)


def _empty_graph_data() -> dict:
    """Return a minimal empty graph payload used when no run is selected."""
    return {
        "nodes": [],
        "edges": [],
        "levels": {},
        "trace_targets": {
            "upstream": {},
            "downstream": {},
        },
    }


def _apply_category_scope_to_graph_data(graph_data: dict, allowed_targets) -> dict:
    """Filter graph payload by the active sidebar category target set."""
    if allowed_targets is None:
        return graph_data

    allowed = {str(name).strip() for name in (allowed_targets or set()) if str(name).strip()}
    if not allowed:
        return _empty_graph_data()

    nodes = list(graph_data.get("nodes", []) or [])
    edges = list(graph_data.get("edges", []) or [])
    levels = dict(graph_data.get("levels", {}) or {})
    trace_targets = dict(graph_data.get("trace_targets", {}) or {})
    node_meta = dict(graph_data.get("node_meta", {}) or {})
    target_to_node = dict(graph_data.get("target_to_node", {}) or {})

    included_nodes = set()
    for node_id, _status in nodes:
        metadata = node_meta.get(node_id, {}) or {}
        members = list(metadata.get("members", []) or [])
        if not members:
            members = [node_id]
        if any(member in allowed for member in members):
            included_nodes.add(node_id)

    for target_name, node_id in target_to_node.items():
        if target_name in allowed:
            included_nodes.add(node_id)

    if not included_nodes:
        return _empty_graph_data()

    original_node_statuses = {
        node_id: status
        for node_id, status in nodes
    }
    filtered_levels = {}
    for level, level_nodes in levels.items():
        scoped_nodes = [node_id for node_id in level_nodes if node_id in included_nodes]
        if scoped_nodes:
            filtered_levels[level] = scoped_nodes

    filtered_edges = [
        (source, target)
        for source, target in edges
        if source in included_nodes and target in included_nodes
    ]

    filtered_trace_targets = {"upstream": {}, "downstream": {}}
    for direction_key in ("upstream", "downstream"):
        direction_lookup = (trace_targets.get(direction_key, {}) or {})
        for node_id, related_nodes in direction_lookup.items():
            if node_id not in included_nodes:
                continue
            scoped_related = [name for name in related_nodes if name in included_nodes]
            filtered_trace_targets[direction_key][node_id] = scoped_related

    filtered_nodes = []
    filtered_node_meta = {}
    for node_id in included_nodes:
        original_status = original_node_statuses.get(node_id, "")
        filtered_status = original_status
        if node_id not in node_meta:
            filtered_nodes.append((node_id, filtered_status))
            continue
        metadata = dict(node_meta[node_id] or {})
        members = list(metadata.get("members", []) or [])
        if members:
            metadata["members"] = [member for member in members if member in allowed]
        member_statuses = dict(metadata.get("member_statuses", {}) or {})
        if member_statuses:
            metadata["member_statuses"] = {
                member: status
                for member, status in member_statuses.items()
                if member in metadata.get("members", [])
            }
        if metadata.get("members") and metadata.get("member_statuses"):
            status_text, filtered_status = status_summary.summarize_group_status(
                metadata["members"],
                lambda member_name: metadata["member_statuses"].get(member_name, ""),
            )
            metadata["status_text"] = status_text
        representative = str(metadata.get("representative_target") or "")
        if representative and representative not in allowed and metadata.get("members"):
            metadata["representative_target"] = metadata["members"][0]
        filtered_node_meta[node_id] = metadata
        filtered_nodes.append((node_id, filtered_status))

    filtered_target_to_node = {
        target_name: node_id
        for target_name, node_id in target_to_node.items()
        if target_name in allowed and node_id in included_nodes
    }

    filtered_graph = {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "levels": filtered_levels,
        "trace_targets": filtered_trace_targets,
    }
    if filtered_node_meta:
        filtered_graph["node_meta"] = filtered_node_meta
    if filtered_target_to_node:
        filtered_graph["target_to_node"] = filtered_target_to_node
    return filtered_graph


def _sync_dependency_graph_toggle(window, is_graph_active: bool) -> None:
    """Sync the sidebar-left dependency-graph switch with active content page."""
    toggle = getattr(window, "dependency_graph_toggle", None)
    label = getattr(window, "_dependency_graph_toggle_label", None)
    if toggle is None:
        return
    blocked = toggle.blockSignals(True)
    toggle.setChecked(bool(is_graph_active))
    toggle.blockSignals(blocked)
    if label is not None:
        label.setStyleSheet(
            "color: #2f7adf; font-size: 12px; font-weight: 700;"
            if is_graph_active
            else "color: #51697f; font-size: 12px; font-weight: 600;"
        )


def _capture_current_tab_state(window) -> dict:
    """Capture the visible top tab presentation for later restore."""
    text = ""
    style = ""
    show_close_button = False
    if hasattr(window, "tab_label"):
        text = window.tab_label.text()
        style = window.tab_label.styleSheet()
    if hasattr(window, "tab_close_btn"):
        show_close_button = window.tab_close_btn.isVisible()
    return {
        "text": text,
        "style": style,
        "show_close_button": show_close_button,
    }


def _apply_graph_mode_tab_state(window) -> None:
    """Render the top tab as the active graph-mode tab."""
    if hasattr(window, "_apply_tab_state"):
        window._apply_tab_state(view_tabs.get_graph_tab_state())


def _current_main_mode_tab_state(window) -> dict:
    """Return the canonical top-tab state for the currently active main-tree mode."""
    state = view_mode_state.ensure_window_view_state(window)
    if state.category_overlay.active:
        return view_tabs.get_category_tab_state(
            state.category_overlay.scope,
            state.category_overlay.category_label,
        )

    if state.tree.mode == view_mode_state.TREE_MODE_ALL_STATUS:
        return view_tabs.get_all_status_tab_state()
    if state.tree.mode == view_mode_state.TREE_MODE_STATUS and state.tree.status_filter:
        return view_tabs.get_status_tab_state(state.tree.status_filter)
    if state.tree.mode == view_mode_state.TREE_MODE_TRACE and state.tree.trace_target:
        direction = "Up" if state.tree.trace_direction == "in" else "Down"
        return view_tabs.get_trace_tab_state(f"Trace {direction}: {state.tree.trace_target}")

    restore_state = getattr(window, "_main_view_tab_state", None)
    if restore_state:
        return restore_state
    return view_tabs.get_main_run_tab_state()


def _apply_active_mode_tab_state(window) -> None:
    """Render the top tab from explicit content/tree/overlay state."""
    content_mode = view_mode_state.get_visible_content_mode(window)
    overlay_active = view_mode_state.is_category_overlay_active(window)

    if overlay_active and hasattr(window, "_apply_tab_state"):
        window._apply_tab_state(_current_main_mode_tab_state(window))
    elif content_mode == "graph":
        _apply_graph_mode_tab_state(window)
    elif hasattr(window, "_apply_tab_state"):
        window._apply_tab_state(_current_main_mode_tab_state(window))

    if hasattr(window, "tab_label"):
        window.tab_label.set_custom_tooltip(
            "Double-click to Fit Graph View"
            if content_mode == "graph"
            else "Double-click to Expand/Collapse All"
        )


def ensure_dependency_graph_panel(window, preserve_viewport: bool = False) -> None:
    """Ensure an embedded graph panel exists and is up to date when marked dirty."""
    current_run = _current_run_name(window)
    panel = getattr(window, "_dependency_graph_panel", None)
    dirty = bool(getattr(window, "_dependency_graph_dirty", True))
    if panel is not None and not dirty:
        return

    if current_run and current_run != "No runs found":
        graph_data = window.build_dependency_graph(current_run)
        if hasattr(window, "get_active_category_target_set"):
            graph_data = _apply_category_scope_to_graph_data(
                graph_data,
                window.get_active_category_target_set(),
            )
        initial_target = window._resolve_dependency_graph_initial_target()
        return_context = window._build_dependency_graph_return_context(current_run)
    else:
        graph_data = _empty_graph_data()
        initial_target = None
        return_context = {}
    locate_callback = _build_locate_target_callback(window, return_context)

    if panel is None:
        panel = DependencyGraphPanel(
            graph_data,
            window.colors,
            initial_target=initial_target,
            locate_target_callback=locate_callback,
            show_auxiliary_controls=False,
            parent=window._graph_view_page,
        )
        window._graph_view_layout.addWidget(panel)
        window._dependency_graph_panel = panel
        window._dependency_graph_initialized = True
        external_scrollbar_controller.connect_graph_scrollbar(window)
    else:
        panel.set_graph_data(
            graph_data,
            initial_target=initial_target,
            locate_target_callback=locate_callback,
            preserve_viewport=preserve_viewport,
        )
        external_scrollbar_controller.connect_graph_scrollbar(window)

    window._dependency_graph_dirty = False
    window._dependency_graph_return_context = return_context
    external_scrollbar_controller.sync_external_scrollbar(window)


def activate_dependency_graph_tab(window, preserve_viewport: bool = False) -> None:
    """Activate the graph content tab and lazily initialize the graph panel."""
    if hasattr(window, "_content_mode_tabs"):
        window._content_mode_tabs.setTabEnabled(1, True)
    ensure_dependency_graph_panel(window, preserve_viewport=preserve_viewport)
    if hasattr(window, "_content_mode_tabs") and hasattr(window, "_graph_view_page"):
        window._content_mode_tabs.setCurrentWidget(window._graph_view_page)
    _apply_active_mode_tab_state(window)


def activate_main_view_tab(window) -> None:
    """Activate the main content tab."""
    if hasattr(window, "_content_mode_tabs") and hasattr(window, "_main_view_page"):
        window._content_mode_tabs.setCurrentWidget(window._main_view_page)
    _apply_active_mode_tab_state(window)


def on_content_tab_changed(window, index: int) -> None:
    """Update content mode state and sidebar visibility for the active content tab."""
    if not hasattr(window, "_content_mode_tabs"):
        return
    previous_mode = view_mode_state.get_content_mode(window)
    is_graph_view = window._content_mode_tabs.widget(index) is getattr(window, "_graph_view_page", None)
    view_mode_state.set_content_mode(window, "graph" if is_graph_view else "main")
    _sync_dependency_graph_toggle(window, is_graph_view)
    if is_graph_view:
        if previous_mode != "graph":
            window._main_view_tab_state = _capture_current_tab_state(window)
        _apply_active_mode_tab_state(window)
        ensure_dependency_graph_panel(window)
    elif previous_mode == "graph":
        _apply_active_mode_tab_state(window)
    if hasattr(window, "set_left_sidebar_content_mode_visible"):
        window.set_left_sidebar_content_mode_visible(True)
    external_scrollbar_controller.sync_external_scrollbar(window)


def on_top_tab_label_clicked(window) -> None:
    """Route the top tab label click to the currently active content mode."""
    if view_mode_state.get_content_mode(window) == "graph":
        activate_dependency_graph_tab(window, preserve_viewport=True)
        return
    activate_main_view_tab(window)


def on_top_tab_label_double_clicked(window) -> None:
    """Route top tab double-click behavior to the currently active content mode."""
    if view_mode_state.get_content_mode(window) == "graph":
        panel = getattr(window, "_dependency_graph_panel", None)
        if panel is not None and hasattr(panel, "fit_view"):
            panel.fit_view()
        return
    if hasattr(window, "toggle_tree_expansion"):
        window.toggle_tree_expansion()


def sync_active_mode_top_tab_state(window) -> None:
    """Re-apply canonical top-tab state for the current active content mode."""
    _apply_active_mode_tab_state(window)
