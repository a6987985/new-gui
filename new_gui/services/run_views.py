"""Helpers for run-oriented view switching and all-status rows."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QStandardItem


ALL_STATUS_HEADERS = ["Run Directory", "Latest Target", "Status", "Time Stamp"]


def build_run_selection_state(current_run: str, run_base_dir: str):
    """Return the resolved run selection state for a combo-box value."""
    if not current_run or current_run == "No runs found":
        return None

    return {
        "run_name": current_run,
        "combo_sel": os.path.join(run_base_dir, current_run),
    }


def reset_all_status_model(model) -> None:
    """Reset the tree model for the four-column all-status overview."""
    model.clear()
    model.setHorizontalHeaderLabels(ALL_STATUS_HEADERS)


def build_all_status_row_items(overview_row: dict, status_colors: dict) -> list:
    """Build one all-status overview row."""
    run_name = overview_row.get("run_name", "")
    latest_target = overview_row.get("latest_target", "")
    latest_status = overview_row.get("latest_status", "")
    latest_timestamp = overview_row.get("latest_timestamp", "")

    row_items = []
    for value in [run_name, latest_target, latest_status, latest_timestamp]:
        item = QStandardItem(value)
        item.setEditable(False)
        item.setForeground(QBrush(Qt.black))
        row_items.append(item)

    color_code = status_colors.get(latest_status.lower(), "#FFFFFF")
    color = QColor(color_code)
    for item in row_items:
        item.setBackground(QBrush(color))
    return row_items
