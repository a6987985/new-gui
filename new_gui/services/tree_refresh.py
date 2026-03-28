"""Helpers for refreshing visible tree rows in the main run view."""

from __future__ import annotations

from typing import Callable

from new_gui.services import status_summary
from new_gui.services import tree_rows


def _row_item_text(row_items, column: int) -> str:
    """Return display text for one row item column."""
    if len(row_items) <= column:
        return ""
    item = row_items[column]
    if item is None:
        return ""
    return item.text()


def refresh_tree_rows(
    model,
    *,
    current_run: str,
    run_dir: str,
    refresh_tune: bool,
    colors,
    preserve_existing_times: bool,
    get_target_status: Callable[[str, str], str],
    get_target_times: Callable[[str, str], tuple],
    get_bsub_params: Callable[[str, str], tuple],
    get_tune_files: Callable[[str, str], list],
) -> None:
    """Refresh visible tree rows for one run without rebuilding the model."""

    def refresh_row(row_idx: int, parent_item=None) -> None:
        row_items = tree_rows.get_row_items(model, row_idx, parent_item)
        target_item = row_items[1] if len(row_items) > 1 else None
        row_kind = tree_rows.get_row_kind(target_item)
        target_name = tree_rows.get_row_target_name(target_item)

        if target_name:
            status = get_target_status(current_run, target_name)
            if preserve_existing_times:
                start_time = _row_item_text(row_items, 4)
                end_time = _row_item_text(row_items, 5)
            else:
                start_time, end_time = get_target_times(current_run, target_name)
            queue, cores, memory = get_bsub_params(run_dir, target_name)
            tune_files = get_tune_files(run_dir, target_name) if refresh_tune else None
            tree_rows.update_target_row_items(
                row_items,
                status,
                start_time,
                end_time,
                queue,
                cores,
                memory,
                colors,
                tune_files=tune_files,
            )
        elif row_kind == tree_rows.ROW_KIND_GROUP:
            group_targets = tree_rows.get_row_targets(target_item)
            status_text, status_key = status_summary.summarize_group_status(
                group_targets,
                lambda grouped_target: get_target_status(current_run, grouped_target),
            )
            tree_rows.update_container_row_items(
                row_items,
                status_text,
                status_key,
                colors,
            )

        level_item = row_items[0] if row_items else None
        if level_item and level_item.hasChildren():
            for child_row in range(level_item.rowCount()):
                refresh_row(child_row, level_item)

    for row in range(model.rowCount()):
        refresh_row(row)
