"""View refresh and state orchestration helpers for MainWindow."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
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


def close_tree_view(window) -> None:
    """Close the tree view or clear the active filtered state."""
    mode = view_modes.get_active_view_mode(
        getattr(window, "is_all_status_view", False),
        window.tab_label.text() if hasattr(window, "tab_label") else "",
    )

    if mode == "all_status":
        window.restore_normal_view()
        return

    if mode == "status":
        window._set_filtered_main_view_tab_state()
        if not window._restore_main_view_snapshot():
            window.populate_data(force_rebuild=True)
        return

    if mode == "trace":
        view_state.clear_trace_filter(window.tree, window.model)
        window._set_filtered_main_view_tab_state()
        return

    if hasattr(window, "tree"):
        window.tree.hide()
    if hasattr(window, "tab_bar"):
        window.tab_bar.hide()


def filter_tree(window, text) -> None:
    """Filter tree items by text using the main-view grouped layout."""
    logger.debug(f"filter_tree called with text='{text}'")
    window.is_search_mode = bool(text)

    if not text:
        window.model.clear()
        window.populate_data()
        return

    if not hasattr(window, "cached_targets_by_level") or not window.cached_targets_by_level:
        current_run = window.combo.currentText()
        if current_run and current_run != "No runs found":
            window.cached_targets_by_level = window.parse_dependency_file(current_run)
            window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(current_run)
            window._cached_collapsible_target_groups_run = current_run

    if not window.cached_targets_by_level:
        return

    window.tree.setUpdatesEnabled(False)
    window._reset_main_tree_model()

    matching_groups = tree_structure.filter_level_groups_by_text(window.cached_targets_by_level, text)
    display_groups = window._build_display_level_groups(dict(matching_groups))
    window._append_target_groups_to_model(display_groups)

    window.tree.expandAll()

    window.tree.setUpdatesEnabled(True)


def filter_tree_by_status_flat(window, status):
    """Show status-filtered targets using the main-view grouped layout."""
    status_key = (status or "").strip().lower()
    if not status_key:
        return 0

    if not hasattr(window, "cached_targets_by_level") or not window.cached_targets_by_level:
        current_run = window.combo.currentText()
        if current_run and current_run != "No runs found":
            window.cached_targets_by_level = window.parse_dependency_file(current_run)
            window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(current_run)
            window._cached_collapsible_target_groups_run = current_run

    if not window.cached_targets_by_level:
        return 0

    window.tree.setUpdatesEnabled(False)
    window._reset_main_tree_model()

    current_run = window.combo.currentText()
    matched_groups = tree_structure.filter_level_groups_by_status(
        window.cached_targets_by_level,
        lambda target_name: window.get_target_status(current_run, target_name),
        status_key,
    )
    display_groups = window._build_display_level_groups(dict(matched_groups), run_name=current_run)
    window._append_target_groups_to_model(
        display_groups,
        run_name=current_run,
        status_value=status_key,
    )
    matched_count = tree_structure.count_display_targets(display_groups)

    window.tree.setUpdatesEnabled(True)
    window.tree.expandAll()
    return matched_count


def apply_status_filter(window, status, update_tab=True) -> None:
    """Apply an in-place status filter to the main target view."""
    if not (hasattr(window, "tab_label") and window.tab_label.text().startswith("Status: ")):
        window._capture_main_view_snapshot()

    matched_count = window._filter_tree_by_status_flat(status)
    if matched_count <= 0:
        window.show_notification("Status Filter", f"No targets with status: {status}", "info")
        return

    if update_tab and hasattr(window, "tab_label"):
        window._apply_tab_state(view_tabs.get_status_tab_state(status))


def show_all_status(window) -> None:
    """Show the all-run status overview in the tree view."""
    logger.debug("show_all_status called")

    window.is_all_status_view = True
    window._set_all_status_tab_state()

    overview_rows = run_repository.collect_all_status_overview(window.run_base_dir)
    window._populate_all_status_overview(overview_rows)
    window._apply_all_status_column_widths()
    logger.debug(f"show_all_status completed, showing {len(overview_rows)} runs")


def apply_all_status_column_widths(window) -> None:
    """Apply adaptive widths for the four-column all-status overview."""
    if not hasattr(window, "tree") or not hasattr(window, "model"):
        return
    if window.model.columnCount() < 4:
        return

    header = window.tree.header()
    if header is None:
        return

    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

    window.tree.resizeColumnToContents(0)
    window.tree.resizeColumnToContents(2)
    window.tree.resizeColumnToContents(3)

    header_min_widths = get_header_min_widths(window)
    for col in range(4):
        min_width = header_min_widths.get(col, 0)
        if min_width > 0:
            window.tree.setColumnWidth(col, max(window.tree.columnWidth(col), min_width))


def get_header_min_widths(window):
    """Calculate per-column minimum widths to fully show header text."""
    if not hasattr(window, "tree") or not hasattr(window, "model"):
        return {}

    header = window.tree.header()
    if header is None:
        return {}

    header_font = header.font()
    font_metrics = QFontMetrics(header_font)
    min_widths = {}

    for col in range(window.model.columnCount()):
        header_text = window.model.headerData(col, Qt.Horizontal) or ""
        text_based_min = font_metrics.horizontalAdvance(str(header_text)) + 30
        style_based_min = header.sectionSizeFromContents(col).width() + 8
        min_widths[col] = max(text_based_min, style_based_min)

    return min_widths


def get_main_view_default_column_widths(window):
    """Return the default width plan for the main tree view."""
    font_metrics = window.tree.fontMetrics()
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
    column_widths = window._get_main_view_default_column_widths()
    tree_content_width = sum(column_widths.values())
    scrollbar_width = window.tree.verticalScrollBar().sizeHint().width()
    frame_width = window.tree.frameWidth() * 2
    return tree_content_width + scrollbar_width + frame_width


def apply_initial_window_width(window) -> None:
    """Resize the startup window to match the main-view default tree width."""
    desired_width = max(
        window._get_main_view_default_window_width(),
        window.minimumSizeHint().width(),
    )
    window.resize(desired_width, WINDOW_HEIGHT)


def restore_normal_view(window) -> None:
    """Restore the normal single-run tree view from the overview."""
    if window.is_all_status_view:
        window._activate_selected_run_view(window.combo.currentText(), invalidate_snapshot=True)


def on_run_changed(window) -> None:
    """Rebuild the selected run view after combo-box selection changes."""
    window._activate_selected_run_view(window.combo.currentText(), invalidate_snapshot=True)


def build_current_view_restore_plan(window, scroll_value: int) -> dict:
    """Describe the current filtered/tree mode for replay after rebuild."""
    header_filter_text = window.header.get_filter_text() if hasattr(window, "header") else ""
    tab_label_text = window.tab_label.text() if hasattr(window, "tab_label") else ""
    return view_restore.build_restore_plan(tab_label_text, header_filter_text, scroll_value)


def restore_view_from_plan(window, restore_plan: dict) -> str:
    """Replay a previously captured filtered/tree mode."""
    show_close_button = None
    if hasattr(window, "tab_close_btn"):
        show_close_button = window.tab_close_btn.show

    return view_restore.apply_restore_plan(
        restore_plan,
        window.get_retrace_target,
        lambda targets_to_show: window.filter_tree_by_targets(set(targets_to_show)),
        window._apply_status_filter,
        window.filter_tree,
        window.tree.verticalScrollBar().setValue,
        show_close_button,
    )


def apply_tab_state(window, tab_state: dict) -> None:
    """Apply a tab label and close-button presentation state."""
    if hasattr(window, "tab_label"):
        window.tab_label.setText(tab_state.get("text", ""))
        window.tab_label.setStyleSheet(tab_state.get("style", ""))
    if hasattr(window, "tab_close_btn"):
        if tab_state.get("show_close_button"):
            window.tab_close_btn.show()
        else:
            window.tab_close_btn.hide()


def set_main_run_tab_state(window) -> None:
    """Apply the default tab presentation for the main run view."""
    window._apply_tab_state(view_tabs.get_main_run_tab_state())


def set_filtered_main_view_tab_state(window) -> None:
    """Reset an in-place filtered view back to the Main View appearance."""
    window._apply_tab_state(view_tabs.get_filtered_main_tab_state())


def set_all_status_tab_state(window) -> None:
    """Apply the tab presentation for the all-status overview."""
    window._apply_tab_state(view_tabs.get_all_status_tab_state())


def populate_all_status_overview(window, overview_rows) -> None:
    """Populate the model with the four-column all-status overview."""
    window.tree.setUpdatesEnabled(False)
    run_views.reset_all_status_model(window.model)
    for row in overview_rows:
        window.model.appendRow(run_views.build_all_status_row_items(row, STATUS_COLORS))
    window.tree.setUpdatesEnabled(True)


def activate_selected_run_view(window, current_run: str, invalidate_snapshot: bool = True) -> None:
    """Switch from overview or filtered states back to the selected run view."""
    run_state = run_views.build_run_selection_state(current_run, window.run_base_dir)
    if not run_state:
        return

    if invalidate_snapshot:
        window._invalidate_main_view_snapshot()

    window.is_all_status_view = False
    window.combo_sel = run_state["combo_sel"]
    logger.info(f"Run changed to: {window.combo_sel}")

    window._set_main_run_tab_state()
    window._build_status_cache(run_state["run_name"])
    window.model.clear()
    window.populate_data()

    if hasattr(window, "status_watcher"):
        window.setup_status_watcher()

    window.update_status_bar()


def populate_data(window, force_rebuild=False) -> None:
    """Populate or refresh the current run view."""
    if window.model.rowCount() > 0 and not force_rebuild:
        current_run = window.combo.currentText()
        if not current_run:
            return

        window.tree.setUpdatesEnabled(False)
        try:
            def update_row(row_index, parent_item=None):
                row_items = tree_rows.get_row_items(window.model, row_index, parent_item)
                target_item = row_items[1] if len(row_items) > 1 else None
                row_kind = tree_rows.get_row_kind(target_item)
                target_name = tree_rows.get_row_target_name(target_item)
                if target_name:
                    status = window.get_target_status(current_run, target_name)
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
                        lambda grouped_target: window.get_target_status(current_run, grouped_target),
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

            for row in range(window.model.rowCount()):
                update_row(row)
        finally:
            window.tree.setUpdatesEnabled(True)
            window.tree.viewport().update()
        return

    current_scroll = window.tree.verticalScrollBar().value()

    window.tree.setUpdatesEnabled(False)
    try:
        window._reset_main_tree_model()

        current_run = window.combo.currentText()
        if not current_run:
            return

        targets_by_level = window.parse_dependency_file(current_run)
        window.cached_targets_by_level = targets_by_level
        window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(current_run)
        window._cached_collapsible_target_groups_run = current_run

        if not targets_by_level:
            logger.warning(f"No targets found for {current_run}")
            return

        window._append_target_groups_to_model(
            window._build_display_level_groups(targets_by_level, run_name=current_run),
            run_name=current_run,
        )

        restore_plan = window._build_current_view_restore_plan(current_scroll)
        if restore_plan.get("mode") == "main":
            window.expand_tree_default()
            window.tree.verticalScrollBar().setValue(current_scroll)
        else:
            window._restore_view_from_plan(restore_plan)
    finally:
        window.tree.setUpdatesEnabled(True)
        window.tree.viewport().update()


def change_run(window) -> None:
    """Refresh visible row status and time fields for the active run."""
    if not hasattr(window, "model") or not window.model or not window.combo_sel:
        return

    if window.is_all_status_view:
        return

    current_run = os.path.basename(window.combo_sel)
    window._build_status_cache(current_run)

    def update_row_status(row_idx, parent_item=None):
        row_items = tree_rows.get_row_items(window.model, row_idx, parent_item)
        target_item = row_items[1] if len(row_items) > 1 else None
        row_kind = tree_rows.get_row_kind(target_item)
        target = tree_rows.get_row_target_name(target_item)
        if target:
            status = window.get_target_status(current_run, target)
            start_time, end_time = window.get_target_times(current_run, target)
            tree_rows.update_target_row_items(row_items, status, start_time, end_time, window.colors)
        elif row_kind == tree_rows.ROW_KIND_GROUP:
            group_targets = tree_rows.get_row_targets(target_item)
            status_text, status_key = status_summary.summarize_group_status(
                group_targets,
                lambda grouped_target: window.get_target_status(current_run, grouped_target),
            )
            tree_rows.update_container_row_items(
                row_items,
                status_text,
                status_key,
                window.colors,
            )

        level_item = row_items[0] if row_items else None
        if level_item and level_item.hasChildren():
            for child_row in range(level_item.rowCount()):
                update_row_status(child_row, level_item)

    for row in range(window.model.rowCount()):
        update_row_status(row, None)

    window.update_status_bar()
    window.tree.viewport().update()
