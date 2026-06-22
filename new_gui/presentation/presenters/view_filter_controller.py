"""Tree filtering flows extracted from the main view controller."""

from __future__ import annotations

from new_gui.model.services import run_views
from new_gui.model.services import tree_structure
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_modes
from new_gui.presentation.presenters import content_tab_controller
from new_gui.presentation.presenters.view_window_bridge import ViewWindowBridge


def bridge(window) -> ViewWindowBridge:
    """Return the narrow MainWindow bridge used by filtering flows."""
    return ViewWindowBridge(window)


def apply_active_category_scope(window, targets_by_level):
    """Apply the active sidebar category filter to one level-target mapping."""
    if not targets_by_level:
        return {}

    if not hasattr(window, "get_active_category_target_set"):
        return dict(targets_by_level)

    allowed_targets = window.get_active_category_target_set()
    if allowed_targets is None:
        return dict(targets_by_level)

    scoped_targets = {}
    for level, targets in tree_structure.get_level_target_groups(targets_by_level):
        filtered = [target for target in targets if target in allowed_targets]
        if filtered:
            scoped_targets[level] = filtered
    return scoped_targets


def close_tree_view(window) -> None:
    """Close the tree view or clear the active filtered state."""
    ui = bridge(window)
    if view_mode_state.is_category_overlay_active(window):
        return_restore_plan = view_mode_state.get_category_return_restore_plan(window)
        current_content_mode = view_mode_state.get_visible_content_mode(window)

        if hasattr(window, "clear_left_sidebar_selection"):
            window.clear_left_sidebar_selection()
        view_mode_state.clear_category_overlay(window)
        if current_content_mode == "graph":
            if hasattr(window, "_mark_dependency_graph_dirty"):
                window._mark_dependency_graph_dirty()
            if hasattr(window, "show_dependency_graph"):
                window.show_dependency_graph(preserve_viewport=True)
            content_tab_controller.sync_active_mode_top_tab_state(window)
        else:
            if hasattr(window, "show_main_view_tab"):
                window.show_main_view_tab()
            if hasattr(window, "show_full_target_view"):
                window.show_full_target_view(force_rebuild=False)
            if return_restore_plan.get("mode") not in {"", "main"}:
                window._restore_view_from_plan(return_restore_plan)
            else:
                ui.set_main_run_tab_state()
        return

    mode = view_modes.get_active_view_mode(window)

    if mode == "all_status":
        ui.restore_normal_view()
        return

    if mode == "status":
        view_mode_state.set_tree_mode_main(window)
        ui.set_filtered_main_view_tab_state()
        if not ui.restore_main_view_snapshot():
            ui.populate_data(force_rebuild=True)
        return

    if mode == "trace":
        view_mode_state.set_tree_mode_main(window)
        trace_return_scroll = getattr(window, "_trace_return_scroll_value", None)
        ui.set_filtered_main_view_tab_state()
        ui.populate_data(force_rebuild=True)
        if trace_return_scroll is not None and hasattr(window, "tree"):
            window.tree.verticalScrollBar().setValue(trace_return_scroll)
        window._trace_return_scroll_value = None
        return

    if mode == "category":
        if hasattr(window, "clear_left_sidebar_selection"):
            window.clear_left_sidebar_selection()
        view_mode_state.clear_category_overlay(window)
        if getattr(window, "_active_content_mode", "main") == "graph":
            if hasattr(window, "_mark_dependency_graph_dirty"):
                window._mark_dependency_graph_dirty()
            if hasattr(window, "show_dependency_graph"):
                window.show_dependency_graph(preserve_viewport=True)
            content_tab_controller.sync_active_mode_top_tab_state(window)
            return
        if hasattr(window, "show_full_target_view"):
            window.show_full_target_view(force_rebuild=False)
        return

    ui.hide_tree()
    ui.hide_tab_bar()


def filter_tree(window, text, search_options=None) -> None:
    """Filter tree rows using a search-result model built from matching targets."""
    ui = bridge(window)
    search_text = text or ""
    normalized_options = dict(search_options or ui.header_filter_options() or {})

    result = run_views.build_search_view_result(
        run_base_dir=ui.run_base_dir,
        current_run=ui.current_run_name(),
        search_text=search_text,
        search_options=normalized_options,
        targets_by_level=ui.cached_targets_by_level,
        get_target_status=ui.get_target_status,
        get_target_times=ui.get_target_times,
        get_bsub_params=ui.get_bsub_params,
        get_tune_files=ui.get_tune_files,
    )

    if not result.should_filter:
        close_tree_view(window)
        return

    ui.capture_main_view_snapshot()
    ui.set_search_mode(True)
    ui.set_tree_updates_enabled(False)
    try:
        ui.clear_model()
        ui.append_search_rows(result.grouped_rows)
        ui.show_tree_and_tab_bar()
        ui.set_filtered_main_view_tab_state()
    finally:
        ui.set_tree_updates_enabled(True)
        ui.tree.viewport().update()
        ui.apply_adaptive_target_column_width()


def filter_tree_by_targets_flat(window, targets_to_show) -> None:
    """Filter tree to show only a supplied flat target set."""
    ui = bridge(window)
    filtered_targets = set(targets_to_show or [])
    current_run = ui.current_run_name()
    if not current_run or not filtered_targets:
        close_tree_view(window)
        return

    ui.capture_main_view_snapshot()
    view_mode_state.set_tree_mode_trace(window)
    ui.set_tree_updates_enabled(False)
    try:
        ui.clear_model()
        targets_by_level = ui.parse_dependency_file(current_run)
        scoped_targets_by_level = apply_active_category_scope(window, targets_by_level)
        trace_targets_by_level = {}
        for level, targets in scoped_targets_by_level.items():
            matching_targets = [target for target in targets if target in filtered_targets]
            if matching_targets:
                trace_targets_by_level[level] = matching_targets

        if trace_targets_by_level:
            ui.append_target_groups_to_model(
                ui.build_display_level_groups(trace_targets_by_level, run_name=current_run),
                run_name=current_run,
            )
        ui.show_tree_and_tab_bar()
        ui.set_filtered_main_view_tab_state()
    finally:
        ui.set_tree_updates_enabled(True)
        ui.tree.viewport().update()
        ui.apply_adaptive_target_column_width()
