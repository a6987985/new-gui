"""Run-refresh and rebuild flows extracted from the main view controller."""

from __future__ import annotations

import os

from new_gui.shared.config.settings import STATUS_COLORS, logger
from new_gui.model.services import tree_refresh
from new_gui.presentation.presenters import content_tab_controller, runtime_controller
from new_gui.presentation.presenters.view_filter_controller import apply_active_category_scope
from new_gui.presentation.presenters.view_window_bridge import ViewWindowBridge


def bridge(window) -> ViewWindowBridge:
    """Return the narrow MainWindow bridge used by run-refresh flows."""
    return ViewWindowBridge(window)


def rebuild_tree_from_current_run(window) -> None:
    """Rebuild the current tree model from dependency data."""
    ui = bridge(window)
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

        scoped_targets_by_level = apply_active_category_scope(window, targets_by_level)
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


def refresh_current_run(window) -> None:
    """Refresh visible row status and time fields for the active run."""
    from new_gui.presentation.presenters import view_controller

    ui = bridge(window)
    if ui.runtime_observers_paused():
        ui.mark_runtime_refresh_pending()
        return

    refresh_state = view_controller.refresh_run_list(window, activate_if_selection_changed=True)
    if refresh_state["selection_changed"]:
        return

    if not ui.model or not ui.combo_sel:
        return

    if ui.is_all_status_view:
        return

    refresh_tune = ui.consume_pending_tune_refresh()
    refresh_dependency = ui.consume_pending_dependency_refresh()
    current_run = os.path.basename(ui.combo_sel)
    ui.build_status_cache(current_run)
    ui.invalidate_bsub_cache(ui.combo_sel)
    if refresh_tune:
        ui.invalidate_tune_cache(ui.combo_sel)
    if refresh_dependency:
        ui.invalidate_main_view_snapshot()
        ui.invalidate_search_view_snapshot()
        ui.clear_cached_target_data()
        rebuild_tree_from_current_run(window)
        ui.mark_dependency_graph_dirty()
        if getattr(window, "_active_content_mode", "main") == "graph":
            content_tab_controller.ensure_dependency_graph_panel(window, preserve_viewport=True)
        runtime_controller.update_backup_timer_state(window)
        return

    tree_refresh.refresh_tree_rows(
        ui.model,
        current_run=current_run,
        run_dir=ui.combo_sel,
        refresh_tune=refresh_tune,
        colors=ui.colors or STATUS_COLORS,
        preserve_existing_times=False,
        get_target_status=ui.get_target_status,
        get_target_times=ui.get_target_times,
        get_bsub_params=ui.get_bsub_params,
        get_tune_files=ui.get_tune_files,
    )

    ui.update_status_bar()
    ui.tree.viewport().update()
    if ui.has_status_watcher():
        ui.setup_status_watcher()
    ui.mark_dependency_graph_dirty()
    if getattr(window, "_active_content_mode", "main") == "graph":
        content_tab_controller.ensure_dependency_graph_panel(window, preserve_viewport=True)
    runtime_controller.update_backup_timer_state(window)
    runtime_controller.update_status_snapshot_timer_state(window)
