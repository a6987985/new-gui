"""View refresh and state orchestration helpers for MainWindow."""

import os

from new_gui.config.settings import STATUS_COLORS, WINDOW_HEIGHT, logger
from new_gui.services import run_repository
from new_gui.services import run_views
from new_gui.services import tree_refresh
from new_gui.services import tree_structure
from new_gui.services import view_layout
from new_gui.services import view_modes
from new_gui.services import view_restore
from new_gui.services import view_run_selection as run_selection
from new_gui.services import view_state
from new_gui.services import view_tabs
from new_gui.ui.controllers.view_window_bridge import ViewWindowBridge


def _bridge(window) -> ViewWindowBridge:
    """Return the narrow MainWindow bridge used by view-controller flows."""
    return ViewWindowBridge(window)


def close_tree_view(window) -> None:
    """Close the tree view or clear the active filtered state."""
    ui = _bridge(window)
    mode = view_modes.get_active_view_mode(
        ui.is_all_status_view,
        ui.tab_label_text(),
    )

    if mode == "all_status":
        ui.restore_normal_view()
        return

    if mode == "status":
        ui.set_filtered_main_view_tab_state()
        if not ui.restore_main_view_snapshot():
            ui.populate_data(force_rebuild=True)
        return

    if mode == "trace":
        ui.clear_trace_filter()
        ui.set_filtered_main_view_tab_state()
        return

    ui.hide_tree()
    ui.hide_tab_bar()


def filter_tree(window, text) -> None:
    """Filter tree items by text using the main-view grouped layout."""
    ui = _bridge(window)
    logger.debug(f"filter_tree called with text='{text}'")
    ui.set_search_mode(bool(text))

    if not text:
        ui.clear_model()
        ui.populate_data()
        return

    run_selection.ensure_cached_targets(window, ui.current_run_name())
    if not run_selection.has_cached_targets(window):
        return

    ui.set_tree_updates_enabled(False)
    ui.reset_main_tree_model()

    matching_groups = tree_structure.filter_level_groups_by_text(window.cached_targets_by_level, text)
    display_groups = ui.build_display_level_groups(dict(matching_groups))
    ui.append_target_groups_to_model(display_groups)

    ui.expand_tree_all()

    ui.set_tree_updates_enabled(True)


def filter_tree_by_status_flat(window, status):
    """Show status-filtered targets using the main-view grouped layout."""
    ui = _bridge(window)
    status_key = (status or "").strip().lower()
    if not status_key:
        return 0

    run_selection.ensure_cached_targets(window, ui.current_run_name())
    if not run_selection.has_cached_targets(window):
        return 0

    ui.set_tree_updates_enabled(False)
    ui.reset_main_tree_model()

    current_run = ui.current_run_name()
    matched_groups = tree_structure.filter_level_groups_by_status(
        window.cached_targets_by_level,
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


def apply_status_filter(window, status, update_tab=True) -> None:
    """Apply an in-place status filter to the main target view."""
    ui = _bridge(window)
    if not ui.tab_label_text().startswith("Status: "):
        ui.capture_main_view_snapshot()

    matched_count = filter_tree_by_status_flat(window, status)
    if matched_count <= 0:
        ui.show_notification("Status Filter", f"No targets with status: {status}", "info")
        return

    if update_tab:
        ui.apply_tab_state(view_tabs.get_status_tab_state(status))


def show_all_status(window) -> None:
    """Show the all-run status overview in the tree view."""
    ui = _bridge(window)
    logger.debug("show_all_status called")

    ui.is_all_status_view = True
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


def get_main_view_default_column_widths(window):
    """Return the default width plan for the main tree view."""
    ui = _bridge(window)
    return view_layout.get_main_view_default_column_widths(ui.tree)


def get_main_view_default_window_width(window):
    """Estimate the startup window width from the main-view column defaults."""
    ui = _bridge(window)
    column_widths = get_main_view_default_column_widths(window)
    return view_layout.get_main_view_default_window_width(ui.tree, column_widths)


def apply_adaptive_target_column_width(window, column: int = 1) -> None:
    """Stretch only the target column when the tree viewport width changes."""
    ui = _bridge(window)
    header_min_widths = get_header_min_widths(window)
    view_layout.apply_adaptive_column_width(
        ui.tree,
        ui.model,
        header_min_widths,
        column=column,
    )


def fill_trailing_blank_with_last_column(window) -> None:
    """Expand the last visible column to remove right-side blank space."""
    ui = _bridge(window)
    header_min_widths = get_header_min_widths(window)
    view_layout.fill_trailing_blank_with_last_column(ui.tree, ui.model, header_min_widths)


def apply_initial_window_width(window) -> None:
    """Resize the startup window to match the main-view default tree width."""
    ui = _bridge(window)
    desired_width = max(
        get_main_view_default_window_width(window),
        ui.minimum_size_hint_width(),
    )
    ui.resize_window(desired_width, WINDOW_HEIGHT)


def restore_normal_view(window) -> None:
    """Restore the normal single-run tree view from the overview."""
    ui = _bridge(window)
    if ui.is_all_status_view:
        ui.activate_selected_run_view(ui.current_run_name(), invalidate_snapshot=True)


def refresh_run_list(window, prefer_cwd: bool = False, activate_if_selection_changed: bool = False) -> dict:
    """Re-scan available runs and keep the combo-box entries in sync."""
    ui = _bridge(window)
    runs = run_repository.list_available_runs(ui.run_base_dir)
    existing_entries = run_selection.combo_run_names(window.combo)
    current_run = ui.current_run_name()
    existing_runs = [] if existing_entries == ["No runs found"] else existing_entries

    desired_run = current_run if current_run in runs else ""
    if prefer_cwd and not desired_run:
        cwd_run = run_selection.current_working_run_name()
        if cwd_run in runs:
            desired_run = cwd_run
    if not desired_run and runs:
        desired_run = runs[0]

    combo_needs_update = (
        existing_runs != runs
        or window.combo.isEnabled() != bool(runs)
        or (not runs and existing_entries != ["No runs found"])
    )
    selection_changed = False

    if combo_needs_update:
        effective_selection = run_selection.set_combo_run_names(window.combo, runs, desired_run)
        selection_changed = bool(effective_selection) and effective_selection != current_run
        ui.combo_sel = os.path.join(ui.run_base_dir, effective_selection) if effective_selection else None

        if activate_if_selection_changed and selection_changed:
            ui.activate_selected_run_view(effective_selection, invalidate_snapshot=True)

    return {
        "runs": runs,
        "selection_changed": selection_changed,
        "selected_run": desired_run,
    }


def on_run_changed(window) -> None:
    """Rebuild the selected run view after combo-box selection changes."""
    ui = _bridge(window)
    ui.activate_selected_run_view(ui.current_run_name(), invalidate_snapshot=True)


def build_current_view_restore_plan(window, scroll_value: int) -> dict:
    """Describe the current filtered/tree mode for replay after rebuild."""
    ui = _bridge(window)
    return view_restore.build_restore_plan(ui.tab_label_text(), ui.header_filter_text(), scroll_value)


def restore_view_from_plan(window, restore_plan: dict) -> str:
    """Replay a previously captured filtered/tree mode."""
    ui = _bridge(window)

    return view_restore.apply_restore_plan(
        restore_plan,
        ui.get_retrace_target,
        lambda targets_to_show: ui.filter_tree_by_targets(set(targets_to_show)),
        lambda status: ui.apply_status_filter(status),
        ui.filter_tree,
        ui.restore_scroll_value,
        ui.tab_close_show_callback(),
    )


def apply_tab_state(window, tab_state: dict) -> None:
    """Apply a tab label and close-button presentation state."""
    ui = _bridge(window)
    ui.set_tab_label(tab_state.get("text", ""))
    ui.set_tab_label_style(tab_state.get("style", ""))
    ui.set_tab_close_button_visible(bool(tab_state.get("show_close_button")))


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
    ui.set_tree_updates_enabled(False)
    run_views.reset_all_status_model(ui.model)
    for row in overview_rows:
        ui.model.appendRow(run_views.build_all_status_row_items(row, STATUS_COLORS))
    ui.set_tree_updates_enabled(True)


def activate_selected_run_view(window, current_run: str, invalidate_snapshot: bool = True) -> None:
    """Switch from overview or filtered states back to the selected run view."""
    ui = _bridge(window)
    run_state = run_views.build_run_selection_state(current_run, ui.run_base_dir)
    if not run_state:
        return

    if invalidate_snapshot:
        ui.invalidate_main_view_snapshot()

    ui.is_all_status_view = False
    ui.combo_sel = run_state["combo_sel"]
    logger.info(f"Run changed to: {ui.combo_sel}")
    ui.refresh_xmeta_background(ui.combo_sel)

    ui.set_main_run_tab_state()
    ui.build_status_cache(run_state["run_name"])
    ui.invalidate_tune_cache(ui.combo_sel)
    ui.clear_model()
    ui.populate_data()
    ui.apply_main_tree_column_visibility(ui.main_tree_visible_columns, save_state=False)

    if ui.has_status_watcher():
        ui.setup_status_watcher()
    if ui.has_tune_watcher():
        ui.setup_tune_watcher()

    ui.update_status_bar()
    ui.update_column_visibility_control_state()
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

        ui.append_target_groups_to_model(
            ui.build_display_level_groups(targets_by_level, run_name=current_run),
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
    refresh_state = refresh_run_list(window, activate_if_selection_changed=True)
    if refresh_state["selection_changed"]:
        return

    ui = _bridge(window)
    if not ui.model or not ui.combo_sel:
        return

    if ui.is_all_status_view:
        return

    refresh_tune = ui.consume_pending_tune_refresh()
    current_run = os.path.basename(ui.combo_sel)
    ui.build_status_cache(current_run)
    ui.invalidate_bsub_cache(ui.combo_sel)
    if refresh_tune:
        ui.invalidate_tune_cache(ui.combo_sel)

    tree_refresh.refresh_tree_rows(
        ui.model,
        current_run=current_run,
        run_dir=ui.combo_sel,
        refresh_tune=refresh_tune,
        colors=ui.colors,
        preserve_existing_times=False,
        get_target_status=ui.get_target_status,
        get_target_times=ui.get_target_times,
        get_bsub_params=ui.get_bsub_params,
        get_tune_files=ui.get_tune_files,
    )

    ui.update_status_bar()
    ui.tree.viewport().update()
