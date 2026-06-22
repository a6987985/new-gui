"""View refresh and state orchestration helpers for MainWindow."""

import os

from new_gui.shared.config.settings import STATUS_COLORS, WINDOW_HEIGHT, logger
from new_gui.infrastructure.repositories import run_repository
from new_gui.model.services import run_views
from new_gui.model.services import tree_refresh
from new_gui.model.services import tree_structure
from new_gui.model.services import view_layout
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_modes
from new_gui.model.services import sidebar_view
from new_gui.model.services import view_run_selection as run_selection
from new_gui.model.services import view_state
from new_gui.model.services import view_tabs
from new_gui.presentation.presenters import content_tab_controller
from new_gui.presentation.presenters import runtime_controller
from new_gui.presentation.presenters import view_filter_controller
from new_gui.presentation.presenters import view_run_controller
from new_gui.presentation.presenters.view_window_bridge import ViewWindowBridge


def _bridge(window) -> ViewWindowBridge:
    """Return the narrow MainWindow bridge used by view-controller flows."""
    return ViewWindowBridge(window)


def _apply_active_category_scope(window, targets_by_level):
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
    view_filter_controller.close_tree_view(window)


def filter_tree(window, text, search_options=None) -> None:
    """Filter tree rows using a search-result model built from matching targets."""
    ui = _bridge(window)
    search_text = text or ""
    normalized_options = dict(search_options or ui.header_filter_options() or {})
    logger.debug(f"filter_tree called with text='{search_text}'")

    if ui.is_all_status_view:
        return

    if not search_text:
        view_mode_state.clear_search_state(window)
        ui.populate_data(force_rebuild=True)
        ui.invalidate_search_view_snapshot()
        return

    run_selection.ensure_cached_targets(window, ui.current_run_name())
    if not run_selection.has_cached_targets(window):
        return

    view_mode_state.set_tree_mode_search(window, search_text, normalized_options)
    ui.set_tree_updates_enabled(False)
    try:
        ui.reset_main_tree_model()
        value_matcher = view_state.build_search_value_matcher(search_text, normalized_options)

        scoped_targets_by_level = _apply_active_category_scope(window, window.cached_targets_by_level)
        matching_targets_by_level = {}
        for level, targets in tree_structure.get_level_target_groups(scoped_targets_by_level):
            matching_targets = [target for target in targets if value_matcher(target)]
            if matching_targets:
                matching_targets_by_level[level] = matching_targets

        if matching_targets_by_level:
            display_groups = ui.build_display_level_groups(
                matching_targets_by_level,
                run_name=ui.current_run_name(),
            )
            ui.append_target_groups_to_model(display_groups, run_name=ui.current_run_name())
            ui.expand_tree_all()
    finally:
        ui.set_tree_updates_enabled(True)
        ui.tree.viewport().update()


def filter_tree_by_status_flat(window, status):
    """Show status-filtered targets using the main-view grouped layout."""
    ui = _bridge(window)
    status_key = (status or "").strip().lower()
    if not status_key:
        return 0

    run_selection.ensure_cached_targets(window, ui.current_run_name())
    if not run_selection.has_cached_targets(window):
        return 0

    ui.invalidate_search_view_snapshot()
    ui.set_tree_updates_enabled(False)
    ui.reset_main_tree_model()

    current_run = ui.current_run_name()
    scoped_targets_by_level = _apply_active_category_scope(window, window.cached_targets_by_level)
    matched_groups = tree_structure.filter_level_groups_by_status(
        scoped_targets_by_level,
        lambda target_name: ui.get_target_status(current_run, target_name),
        status_key,
    )
    display_groups = ui.build_display_level_groups(dict(matched_groups), run_name=current_run)
    ui.append_target_groups_to_model(
        display_groups,
        run_name=current_run,
        status_value=status_key,
    )
    matched_count = tree_structure.count_display_targets(display_groups)

    ui.set_tree_updates_enabled(True)
    ui.expand_tree_all()
    return matched_count


def filter_tree_by_targets_flat(window, targets_to_show) -> int:
    """Show only the requested dependency targets using the grouped main-tree layout."""
    ui = _bridge(window)
    if not targets_to_show:
        return 0

    run_selection.ensure_cached_targets(window, ui.current_run_name())
    if not run_selection.has_cached_targets(window):
        return 0

    ui.invalidate_search_view_snapshot()
    ui.set_tree_updates_enabled(False)
    try:
        ui.reset_main_tree_model()
        current_run = ui.current_run_name()
        scoped_targets_by_level = _apply_active_category_scope(window, window.cached_targets_by_level)
        matched_groups = tree_structure.filter_level_groups_by_targets(
            scoped_targets_by_level,
            targets_to_show,
        )
        display_groups = ui.build_display_level_groups(dict(matched_groups), run_name=current_run)
        ui.append_target_groups_to_model(display_groups, run_name=current_run)
        matched_count = tree_structure.count_display_targets(display_groups)
    finally:
        ui.set_tree_updates_enabled(True)

    ui.expand_tree_all()
    return matched_count


def apply_status_filter(window, status, update_tab=True) -> None:
    """Apply an in-place status filter to the main target view."""
    ui = _bridge(window)
    if getattr(window, "_active_content_mode", "main") == "graph" and hasattr(window, "show_main_view_tab"):
        window.show_main_view_tab()
    if view_mode_state.get_tree_mode(window) != view_mode_state.TREE_MODE_STATUS:
        ui.capture_main_view_snapshot()

    matched_count = filter_tree_by_status_flat(window, status)
    if matched_count <= 0:
        ui.show_notification("Status Filter", f"No targets with status: {status}", "info")
        return

    view_mode_state.set_tree_mode_status(window, status)
    if update_tab:
        ui.apply_tab_state(view_tabs.get_status_tab_state(status))


def show_all_status(window) -> None:
    """Show the all-run status overview in the tree view."""
    ui = _bridge(window)
    logger.debug("show_all_status called")
    if getattr(window, "_active_content_mode", "main") == "graph" and hasattr(window, "show_main_view_tab"):
        window.show_main_view_tab()

    ui.invalidate_search_view_snapshot()
    view_mode_state.set_tree_mode_all_status(window)
    ui.set_all_status_tab_state()

    overview_rows = run_repository.collect_all_status_overview(ui.run_base_dir)
    ui.populate_all_status_overview(overview_rows)
    ui.apply_all_status_column_widths()
    ui.update_column_visibility_control_state()
    logger.debug(f"show_all_status completed, showing {len(overview_rows)} runs")


def apply_all_status_column_widths(window) -> None:
    """Apply adaptive widths for the four-column all-status overview."""
    ui = _bridge(window)
    header_min_widths = get_header_min_widths(window)
    view_layout.apply_all_status_column_widths(ui.tree, ui.model, header_min_widths)
    apply_adaptive_target_column_width(window)


def get_header_min_widths(window):
    """Calculate per-column minimum widths to fully show header text."""
    ui = _bridge(window)
    return view_layout.get_header_min_widths(ui.model, ui.tree.header())


def get_main_view_min_column_widths(window):
    """Return main-tree minimum widths, including fixed data-column widths."""
    ui = _bridge(window)
    header_min_widths = get_header_min_widths(window)
    return view_layout.get_main_view_min_column_widths(ui.tree, header_min_widths)


def get_main_view_default_column_widths(window):
    """Return the default width plan for the main tree view."""
    ui = _bridge(window)
    return view_layout.get_main_view_default_column_widths(ui.tree)


def get_main_view_default_window_width(window):
    """Estimate the startup window width from the main-view column defaults."""
    ui = _bridge(window)
    column_widths = get_main_view_default_column_widths(window)
    min_widths = get_main_view_min_column_widths(window)
    effective_widths = {
        column: max(width, min_widths.get(column, 0))
        for column, width in column_widths.items()
    }
    return view_layout.get_main_view_default_window_width(ui.tree, effective_widths)


def apply_adaptive_target_column_width(window, column: int = 1) -> None:
    """Stretch only the target column when the tree viewport width changes."""
    ui = _bridge(window)
    header_min_widths = get_header_min_widths(window)
    target_viewport_width = getattr(window, "_layout_target_viewport_width", None)
    view_layout.apply_adaptive_column_width(
        ui.tree,
        ui.model,
        header_min_widths,
        column=column,
        viewport_width=target_viewport_width,
    )


def fill_trailing_blank_with_last_column(window) -> None:
    """Expand the last visible column to remove right-side blank space."""
    ui = _bridge(window)
    header_min_widths = get_main_view_min_column_widths(window)
    target_viewport_width = getattr(window, "_layout_target_viewport_width", None)
    view_layout.fill_trailing_blank_with_last_column(
        ui.tree,
        ui.model,
        header_min_widths,
        viewport_width=target_viewport_width,
    )


def apply_initial_window_width(window) -> None:
    """Resize the startup window to match the main-view default tree width."""
    ui = _bridge(window)
    sidebar_width = 0
    if bool(getattr(window, "_left_sidebar_visible", True)) and bool(
        getattr(window, "_left_sidebar_content_mode_visible", True)
    ):
        sidebar_width = max(0, int(getattr(window, "_left_sidebar_default_width", 0) or 0))
    desired_width = max(
        get_main_view_default_window_width(window) + sidebar_width,
        ui.minimum_size_hint_width(),
    )
    ui.resize_window(desired_width, WINDOW_HEIGHT)


def restore_normal_view(window) -> None:
    """Restore the normal single-run tree view from the overview."""
    ui = _bridge(window)
    if ui.is_all_status_view:
        ui.activate_selected_run_view(ui.current_run_name(), invalidate_snapshot=True)


def _clear_missing_run_tracking(window) -> None:
    """Clear the remembered missing-run selection marker."""
    window._missing_selected_run_name = ""


def _build_missing_run_message(missing_run_name: str, runs) -> str:
    """Return the notification body for one missing selected run."""
    if runs:
        return (
            f"Selected run '{missing_run_name}' was removed from disk. "
            "The current view is now empty. Choose another run from the selector to continue."
        )
    return (
        f"Selected run '{missing_run_name}' was removed from disk. "
        "The current view is now empty and no other runs are available."
    )


def _enter_missing_run_state(window, missing_run_name: str, runs) -> None:
    """Clear run-bound UI state while keeping the missing run visible in the selector."""
    ui = _bridge(window)
    window._missing_selected_run_name = missing_run_name
    ui.combo_sel = None
    view_mode_state.set_content_mode(window, view_mode_state.CONTENT_MODE_MAIN)
    view_mode_state.set_tree_mode_main(window)
    view_mode_state.clear_category_overlay(window)
    if hasattr(window, "clear_left_sidebar_selection"):
        window.clear_left_sidebar_selection()
    window._pending_tune_refresh = False
    window._pending_dependency_refresh = False
    if hasattr(window, "_cache_manager"):
        window._cache_manager.reset_status_cache()
        window._status_cache = window._cache_manager.status_cache
        window._cache_manager.clear_targets_cache()
        window.cached_targets_by_level = window._state.run_cache.targets_by_level
        window._cached_targets_run = window._state.run_cache.cached_targets_run
        window.cached_collapsible_target_groups = window._state.run_cache.collapsible_target_groups
        window._cached_collapsible_target_groups_run = window._state.run_cache.cached_collapsible_groups_run
    else:
        window._status_cache = {"run": "", "statuses": {}, "times": {}}
        if hasattr(window, "_cache_manager"):
            window._cache_manager.clear_targets_cache()
            window.cached_targets_by_level = window._state.run_cache.targets_by_level
            window._cached_targets_run = window._state.run_cache.cached_targets_run
            window.cached_collapsible_target_groups = window._state.run_cache.collapsible_target_groups
            window._cached_collapsible_target_groups_run = window._state.run_cache.cached_collapsible_groups_run
        else:
            window.cached_targets_by_level = {}
            window._cached_targets_run = ""
            window.cached_collapsible_target_groups = {}
            window._cached_collapsible_target_groups_run = ""
    window._dependency_graph_return_context = {}
    window._main_view_tab_state = view_tabs.get_main_run_tab_state()

    ui.invalidate_main_view_snapshot()
    ui.invalidate_search_view_snapshot()
    if hasattr(window, "_sidebar_filter_snapshot"):
        window._sidebar_filter_snapshot = None

    if hasattr(window, "_reset_main_tree_model"):
        window._reset_main_tree_model()
    elif hasattr(window, "model"):
        window.model.clear()

    if hasattr(window, "refresh_left_sidebar_categories"):
        window.refresh_left_sidebar_categories(None)
    if hasattr(window, "show_main_view_tab"):
        window.show_main_view_tab()
    ui.set_main_run_tab_state()

    if hasattr(window, "setup_status_watcher"):
        window.setup_status_watcher()
    if hasattr(window, "setup_tune_watcher"):
        window.setup_tune_watcher()
    if hasattr(window, "setup_dependency_watcher"):
        window.setup_dependency_watcher()

    if hasattr(window, "set_terminal_follow_run_enabled"):
        window.set_terminal_follow_run_enabled(False)

    terminal = getattr(window, "_embedded_terminal", None)
    if terminal is not None:
        if hasattr(terminal, "stop_terminal"):
            terminal.stop_terminal()
        if hasattr(terminal, "_show_message"):
            terminal._show_message(_build_missing_run_message(missing_run_name, runs))

    ui.update_status_bar()
    ui.update_column_visibility_control_state()
    ui.mark_dependency_graph_dirty()
    runtime_controller.update_backup_timer_state(window)


def refresh_run_list(window, prefer_cwd: bool = False, activate_if_selection_changed: bool = False) -> dict:
    """Re-scan available runs and keep the combo-box entries in sync."""
    ui = _bridge(window)
    runs = run_repository.list_available_runs(ui.run_base_dir)
    existing_entries = run_selection.combo_run_names(window.combo)
    current_entry = ui.current_run_name()
    current_run = run_selection.normalize_run_name(current_entry)
    desired_run = current_run if current_run in runs else ""
    missing_run_name = ""

    if (
        current_entry
        and current_entry != "No runs found"
        and current_run
        and current_run not in runs
    ):
        missing_run_name = current_run

    if prefer_cwd and not desired_run and not missing_run_name:
        cwd_run = run_selection.current_working_run_name()
        if cwd_run in runs:
            desired_run = cwd_run
    if not desired_run and runs and not missing_run_name:
        desired_run = runs[0]

    desired_entries = (
        ["No runs found"]
        if not runs and not missing_run_name
        else run_selection.build_combo_run_entries(runs, missing_run_name=missing_run_name)
    )
    combo_needs_update = (
        existing_entries != desired_entries
        or window.combo.isEnabled() != bool(runs)
        or (not runs and existing_entries != ["No runs found"])
    )
    selection_changed = False
    effective_selection = current_entry

    if combo_needs_update:
        effective_selection = run_selection.set_combo_run_names(
            window.combo,
            runs,
            desired_run,
            missing_run_name=missing_run_name,
        )
        selection_changed = (
            bool(effective_selection)
            and not run_selection.is_missing_run_label(effective_selection)
            and effective_selection != current_entry
        )
        normalized_selection = run_selection.normalize_run_name(effective_selection)
        ui.combo_sel = (
            os.path.join(ui.run_base_dir, normalized_selection)
            if normalized_selection and not run_selection.is_missing_run_label(effective_selection)
            else None
        )

        if activate_if_selection_changed and selection_changed and ui.combo_sel:
            ui.activate_selected_run_view(effective_selection, invalidate_snapshot=True)

    if missing_run_name:
        should_notify = getattr(window, "_missing_selected_run_name", "") != missing_run_name
        _enter_missing_run_state(window, missing_run_name, runs)
        if should_notify:
            ui.show_notification(
                "Run Removed",
                _build_missing_run_message(missing_run_name, runs),
                "warning",
            )
    elif getattr(window, "_missing_selected_run_name", ""):
        _clear_missing_run_tracking(window)

    return {
        "runs": runs,
        "selection_changed": selection_changed,
        "selected_run": (
            missing_run_name
            if missing_run_name
            else ""
            if run_selection.is_unavailable_run_entry(effective_selection or desired_run)
            else run_selection.normalize_run_name(effective_selection or desired_run)
        ),
        "missing_selected_run": bool(missing_run_name),
    }


def on_run_changed(window) -> None:
    """Rebuild the selected run view after combo-box selection changes."""
    ui = _bridge(window)
    presentation_snapshot = None
    if ui.model is not None and ui.model.rowCount() > 0:
        presentation_snapshot = view_state.capture_cross_run_presentation_snapshot(ui.model, ui.tree)
    ui.activate_selected_run_view(
        ui.current_run_name(),
        invalidate_snapshot=True,
        presentation_snapshot=presentation_snapshot,
    )


def build_current_view_restore_plan(window, scroll_value: int) -> dict:
    """Describe the current filtered/tree mode for replay after rebuild."""
    return view_mode_state.build_restore_plan(window, scroll_value)


def restore_view_from_plan(window, restore_plan: dict) -> str:
    """Replay a previously captured filtered/tree mode."""
    ui = _bridge(window)
    plan = dict(restore_plan or {})
    mode = str(plan.get("mode") or "main").strip().lower()

    if mode == "trace":
        target_name = str(plan.get("target_name") or "").strip()
        inout = str(plan.get("inout") or "out").strip().lower() or "out"
        if target_name and inout:
            related_targets = list(ui.get_retrace_target(target_name, inout) or [])
            if target_name not in related_targets:
                if inout == "in":
                    related_targets.append(target_name)
                else:
                    related_targets.insert(0, target_name)
            filter_tree_by_targets_flat(window, set(related_targets))
            direction = "Up" if inout == "in" else "Down"
            view_mode_state.set_tree_mode_trace(window, target_name, inout)
            ui.apply_tab_state(view_tabs.get_trace_tab_state(f"Trace {direction}: {target_name}"))
    elif mode == "status":
        status = str(plan.get("status") or "").strip().lower()
        if status:
            apply_status_filter(window, status, update_tab=True)
    elif mode == "search":
        search_text = str(plan.get("search_text") or "")
        search_options = dict(plan.get("search_options") or {})
        if search_text:
            ui.filter_tree(search_text, search_options=search_options)
        else:
            view_mode_state.set_tree_mode_main(window)
            ui.set_main_run_tab_state()
    elif mode == "category":
        scope = str(plan.get("scope") or "stage")
        category_id = str(plan.get("category_id") or "")
        if category_id:
            sidebar_view.restore_category_view(window, scope, category_id)
    elif mode == "all_status":
        show_all_status(window)
    else:
        view_mode_state.set_tree_mode_main(window)
        ui.set_main_run_tab_state()

    ui.restore_scroll_value(plan.get("scroll", 0))
    return mode


def apply_tab_state(window, tab_state: dict) -> None:
    """Apply a tab label and close-button presentation state."""
    ui = _bridge(window)
    ui.set_tab_label(tab_state.get("text", ""))
    ui.set_tab_label_style(tab_state.get("style", ""))
    ui.set_tab_close_button_visible(bool(tab_state.get("show_close_button")))
    runtime_controller.update_backup_timer_state(window)


def set_main_run_tab_state(window) -> None:
    """Apply the default tab presentation for the main run view."""
    _bridge(window).apply_tab_state(view_tabs.get_main_run_tab_state())


def set_filtered_main_view_tab_state(window) -> None:
    """Reset an in-place filtered view back to the Main View appearance."""
    _bridge(window).apply_tab_state(view_tabs.get_filtered_main_tab_state())


def set_all_status_tab_state(window) -> None:
    """Apply the tab presentation for the all-status overview."""
    _bridge(window).apply_tab_state(view_tabs.get_all_status_tab_state())


def populate_all_status_overview(window, overview_rows) -> None:
    """Populate the model with the four-column all-status overview."""
    ui = _bridge(window)
    ui.invalidate_search_view_snapshot()
    ui.set_tree_updates_enabled(False)
    run_views.reset_all_status_model(ui.model)
    for row in overview_rows:
        ui.model.appendRow(run_views.build_all_status_row_items(row, STATUS_COLORS))
    ui.set_tree_updates_enabled(True)


def activate_selected_run_view(
    window,
    current_run: str,
    invalidate_snapshot: bool = True,
    presentation_snapshot: dict = None,
) -> None:
    """Switch from overview or filtered states back to the selected run view."""
    ui = _bridge(window)
    preserve_graph_mode = str(getattr(window, "_active_content_mode", "main") or "main") == "graph"
    run_state = run_views.build_run_selection_state(current_run, ui.run_base_dir)
    if not run_state:
        return

    _clear_missing_run_tracking(window)
    if invalidate_snapshot:
        ui.invalidate_main_view_snapshot()

    ui.invalidate_search_view_snapshot()
    if hasattr(window, "clear_left_sidebar_selection"):
        window.clear_left_sidebar_selection()
    view_mode_state.clear_category_overlay(window)
    view_mode_state.set_tree_mode_main(window)
    ui.combo_sel = run_state["combo_sel"]
    window._dependency_graph_return_context = {}
    window._main_view_tab_state = view_tabs.get_main_run_tab_state()
    logger.info(f"Run changed to: {ui.combo_sel}")
    if hasattr(window, "refresh_left_sidebar_categories"):
        window.refresh_left_sidebar_categories(ui.combo_sel)
    ui.refresh_xmeta_background(ui.combo_sel)

    if not preserve_graph_mode:
        ui.set_main_run_tab_state()
    ui.build_status_cache(run_state["run_name"])
    ui.invalidate_tune_cache(ui.combo_sel)
    ui.clear_model()
    ui.populate_data()
    ui.apply_main_tree_column_visibility(ui.main_tree_visible_columns, save_state=False)
    if presentation_snapshot:
        view_state.restore_cross_run_presentation_snapshot(
            ui.model,
            ui.tree,
            presentation_snapshot,
        )

    if ui.has_status_watcher():
        ui.setup_status_watcher()
    if ui.has_tune_watcher():
        ui.setup_tune_watcher()
    if ui.has_dependency_watcher():
        ui.setup_dependency_watcher()

    ui.update_status_bar()
    ui.update_column_visibility_control_state()
    ui.mark_dependency_graph_dirty()
    if preserve_graph_mode and hasattr(window, "show_dependency_graph"):
        window.show_dependency_graph()
    runtime_controller.update_backup_timer_state(window)
    if ui.is_terminal_follow_run_enabled():
        ui.sync_embedded_terminal_run_dir(ui.combo_sel)


def populate_data(window, force_rebuild=False) -> None:
    """Populate or refresh the current run view."""
    ui = _bridge(window)
    if ui.model.rowCount() > 0 and not force_rebuild:
        current_run = ui.current_run_name()
        if not current_run:
            return

        refresh_tune = ui.consume_pending_tune_refresh()
        ui.invalidate_bsub_cache(ui.combo_sel)
        if refresh_tune:
            ui.invalidate_tune_cache(ui.combo_sel)
        ui.set_tree_updates_enabled(False)
        try:
            tree_refresh.refresh_tree_rows(
                ui.model,
                current_run=current_run,
                run_dir=ui.combo_sel,
                refresh_tune=refresh_tune,
                colors=STATUS_COLORS,
                preserve_existing_times=True,
                get_target_status=ui.get_target_status,
                get_target_times=ui.get_target_times,
                get_bsub_params=ui.get_bsub_params,
                get_tune_files=ui.get_tune_files,
            )
        finally:
            ui.set_tree_updates_enabled(True)
            ui.tree.viewport().update()
        return

    current_scroll = ui.current_scroll_value()

    ui.set_tree_updates_enabled(False)
    try:
        ui.invalidate_search_view_snapshot()
        ui.reset_main_tree_model()

        current_run = ui.current_run_name()
        if not current_run:
            return

        targets_by_level = ui.parse_dependency_file(current_run)
        collapsible_groups = ui.parse_collapsible_target_groups(current_run)
        ui.set_cached_target_data(current_run, targets_by_level, collapsible_groups)

        if not targets_by_level:
            logger.warning(f"No targets found for {current_run}")
            return

        scoped_targets_by_level = view_filter_controller.apply_active_category_scope(window, targets_by_level)
        if not scoped_targets_by_level:
            return

        ui.append_target_groups_to_model(
            ui.build_display_level_groups(scoped_targets_by_level, run_name=current_run),
            run_name=current_run,
        )

        restore_plan = ui.build_current_view_restore_plan(current_scroll)
        if restore_plan.get("mode") == "main":
            ui.expand_tree_default()
            ui.restore_scroll_value(current_scroll)
        else:
            ui.restore_view_from_plan(restore_plan)
    finally:
        ui.set_tree_updates_enabled(True)
        ui.tree.viewport().update()
        ui.apply_adaptive_target_column_width()


def change_run(window) -> None:
    """Refresh visible row status and time fields for the active run."""
    view_run_controller.refresh_current_run(window)
