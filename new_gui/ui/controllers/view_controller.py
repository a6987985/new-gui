"""View refresh and state orchestration helpers for MainWindow."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QHeaderView

from new_gui.config.settings import STATUS_COLORS, WINDOW_HEIGHT, logger
from new_gui.services import run_repository
from new_gui.services import run_views
from new_gui.services import status_summary
from new_gui.services import tree_rows
from new_gui.services import tree_structure
from new_gui.services import view_modes
from new_gui.services import view_restore
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

    ui.ensure_cached_targets()
    if not ui.has_cached_targets():
        return

    ui.set_tree_updates_enabled(False)
    ui.reset_main_tree_model()

    matching_groups = tree_structure.filter_level_groups_by_text(ui.cached_targets_by_level, text)
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

    ui.ensure_cached_targets()
    if not ui.has_cached_targets():
        return 0

    ui.set_tree_updates_enabled(False)
    ui.reset_main_tree_model()

    current_run = ui.current_run_name()
    matched_groups = tree_structure.filter_level_groups_by_status(
        ui.cached_targets_by_level,
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
    if ui.model.columnCount() < 4:
        return

    header = ui.tree.header()
    if header is None:
        return

    header.setStretchLastSection(False)
    for col in range(ui.model.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.Interactive)

    ui.tree.resizeColumnToContents(0)
    ui.tree.resizeColumnToContents(2)
    ui.tree.resizeColumnToContents(3)

    header_min_widths = get_header_min_widths(window)
    for col in range(4):
        min_width = header_min_widths.get(col, 0)
        if min_width > 0:
            ui.tree.setColumnWidth(col, max(ui.tree.columnWidth(col), min_width))

    apply_adaptive_target_column_width(window)


def get_header_min_widths(window):
    """Calculate per-column minimum widths to fully show header text."""
    ui = _bridge(window)

    header = ui.tree.header()
    if header is None:
        return {}

    header_font = QFont(header.font())
    header_font.setPointSize(10)
    header_font.setWeight(QFont.DemiBold)
    font_metrics = QFontMetrics(header_font)
    min_widths = {}

    for col in range(ui.model.columnCount()):
        header_text = ui.model.headerData(col, Qt.Horizontal) or ""
        if hasattr(header, "get_minimum_width_for_text"):
            text_based_min = header.get_minimum_width_for_text(str(header_text))
        else:
            text_based_min = font_metrics.horizontalAdvance(str(header_text)) + 30
        style_based_min = header.sectionSizeFromContents(col).width() + 8
        min_widths[col] = max(text_based_min, style_based_min)

    return min_widths


def get_main_view_default_column_widths(window):
    """Return the default width plan for the main tree view."""
    ui = _bridge(window)
    font_metrics = ui.tree.fontMetrics()
    status_values = ["finish", "running", "failed", "skip", "scheduled", "pending"]
    status_width = max(font_metrics.horizontalAdvance(status) for status in status_values) + 20

    time_format = "YYYY-MM-DD HH:MM:SS"
    time_width = font_metrics.horizontalAdvance(time_format) + 20

    return {
        0: 80,
        1: 400,
        2: status_width,
        3: 120,
        4: time_width,
        5: time_width,
        6: 100,
        7: 60,
        8: 80,
    }


def get_main_view_default_window_width(window):
    """Estimate the startup window width from the main-view column defaults."""
    ui = _bridge(window)
    column_widths = get_main_view_default_column_widths(window)
    tree_content_width = sum(column_widths.values())
    scrollbar_width = ui.tree.verticalScrollBar().sizeHint().width()
    frame_width = ui.tree.frameWidth() * 2
    return tree_content_width + scrollbar_width + frame_width


def apply_adaptive_target_column_width(window, column: int = 1) -> None:
    """Stretch only the target column when the tree viewport width changes."""
    ui = _bridge(window)
    if ui.model.columnCount() <= column:
        return
    if ui.tree.isColumnHidden(column):
        return

    viewport_width = ui.tree.viewport().width()
    if viewport_width <= 0:
        return

    header_min_widths = get_header_min_widths(window)
    current_target_width = ui.tree.columnWidth(column)
    min_target_width = header_min_widths.get(column, 0)
    visible_columns = [col for col in range(ui.model.columnCount()) if not ui.tree.isColumnHidden(col)]
    if not visible_columns:
        return
    current_total_width = sum(ui.tree.columnWidth(col) for col in visible_columns)
    width_delta = viewport_width - current_total_width
    new_target_width = max(min_target_width, current_target_width + width_delta)

    if new_target_width != current_target_width:
        ui.tree.setColumnWidth(column, new_target_width)


def fill_trailing_blank_with_last_column(window) -> None:
    """Expand the last visible column to remove right-side blank space."""
    ui = _bridge(window)

    visible_columns = [col for col in range(ui.model.columnCount()) if not ui.tree.isColumnHidden(col)]
    if not visible_columns:
        return

    viewport_width = ui.tree.viewport().width()
    if viewport_width <= 0:
        return

    last_column = visible_columns[-1]
    current_total_width = sum(ui.tree.columnWidth(col) for col in visible_columns)
    width_delta = viewport_width - current_total_width
    if width_delta <= 0:
        return

    header_min_widths = get_header_min_widths(window)
    current_last_width = ui.tree.columnWidth(last_column)
    min_last_width = header_min_widths.get(last_column, 0)
    new_last_width = max(min_last_width, current_last_width + width_delta)

    if new_last_width != current_last_width:
        ui.tree.setColumnWidth(last_column, new_last_width)


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

    ui.set_main_run_tab_state()
    ui.build_status_cache(run_state["run_name"])
    ui.clear_model()
    ui.populate_data()
    ui.apply_main_tree_column_visibility(ui.main_tree_visible_columns, save_state=False)

    if ui.has_status_watcher():
        ui.setup_status_watcher()

    ui.update_status_bar()
    ui.update_column_visibility_control_state()


def populate_data(window, force_rebuild=False) -> None:
    """Populate or refresh the current run view."""
    ui = _bridge(window)
    if ui.model.rowCount() > 0 and not force_rebuild:
        current_run = ui.current_run_name()
        if not current_run:
            return

        ui.set_tree_updates_enabled(False)
        try:
            def update_row(row_index, parent_item=None):
                row_items = tree_rows.get_row_items(ui.model, row_index, parent_item)
                target_item = row_items[1] if len(row_items) > 1 else None
                row_kind = tree_rows.get_row_kind(target_item)
                target_name = tree_rows.get_row_target_name(target_item)
                if target_name:
                    status = ui.get_target_status(current_run, target_name)
                    tree_rows.update_target_row_items(
                        row_items,
                        status,
                        row_items[4].text() if len(row_items) > 4 and row_items[4] else "",
                        row_items[5].text() if len(row_items) > 5 and row_items[5] else "",
                        STATUS_COLORS,
                    )
                elif row_kind == tree_rows.ROW_KIND_GROUP:
                    group_targets = tree_rows.get_row_targets(target_item)
                    status_text, status_key = status_summary.summarize_group_status(
                        group_targets,
                        lambda grouped_target: ui.get_target_status(current_run, grouped_target),
                    )
                    tree_rows.update_container_row_items(
                        row_items,
                        status_text,
                        status_key,
                        STATUS_COLORS,
                    )

                level_item = row_items[0] if row_items else None
                if level_item and level_item.hasChildren():
                    for child_row in range(level_item.rowCount()):
                        update_row(child_row, level_item)

            for row in range(ui.model.rowCount()):
                update_row(row)
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
    ui = _bridge(window)
    if not ui.model or not ui.combo_sel:
        return

    if ui.is_all_status_view:
        return

    current_run = os.path.basename(ui.combo_sel)
    ui.build_status_cache(current_run)

    def update_row_status(row_idx, parent_item=None):
        row_items = tree_rows.get_row_items(ui.model, row_idx, parent_item)
        target_item = row_items[1] if len(row_items) > 1 else None
        row_kind = tree_rows.get_row_kind(target_item)
        target = tree_rows.get_row_target_name(target_item)
        if target:
            status = ui.get_target_status(current_run, target)
            start_time, end_time = ui.get_target_times(current_run, target)
            tree_rows.update_target_row_items(row_items, status, start_time, end_time, ui.colors)
        elif row_kind == tree_rows.ROW_KIND_GROUP:
            group_targets = tree_rows.get_row_targets(target_item)
            status_text, status_key = status_summary.summarize_group_status(
                group_targets,
                lambda grouped_target: ui.get_target_status(current_run, grouped_target),
            )
            tree_rows.update_container_row_items(
                row_items,
                status_text,
                status_key,
                ui.colors,
            )

        level_item = row_items[0] if row_items else None
        if level_item and level_item.hasChildren():
            for child_row in range(level_item.rowCount()):
                update_row_status(child_row, level_item)

    for row in range(ui.model.rowCount()):
        update_row_status(row, None)

    ui.update_status_bar()
    ui.tree.viewport().update()
