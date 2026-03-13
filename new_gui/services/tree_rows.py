"""Helpers for building and refreshing main tree rows."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QStandardItem


MAIN_TREE_HEADERS = [
    "level",
    "target",
    "status",
    "tune",
    "start time",
    "end time",
    "queue",
    "cores",
    "memory",
]

DEFAULT_STATUS_COLOR = "#87CEEB"


def set_main_tree_headers(model) -> None:
    """Apply the standard headers used by the main target tree."""
    model.setHorizontalHeaderLabels(MAIN_TREE_HEADERS)


def reset_main_tree_model(model, set_column_widths) -> None:
    """Clear and reinitialize the main target tree model."""
    model.clear()
    set_main_tree_headers(model)
    set_column_widths()


def build_target_row_items(
    level_text,
    target_name: str,
    status_value: str,
    tune_files,
    start_time: str,
    end_time: str,
    queue: str,
    cores: str,
    memory: str,
    status_colors: dict,
    tune_display: str = None,
) -> list:
    """Build one main-tree row with the standard columns and styling."""
    normalized_tune_files = list(tune_files or [])
    if tune_display is None:
        tune_display = ", ".join([suffix for suffix, _ in normalized_tune_files]) if normalized_tune_files else ""

    values = [
        "" if level_text is None else str(level_text),
        "" if target_name is None else str(target_name),
        "" if status_value is None else str(status_value),
        tune_display,
        "" if start_time is None else str(start_time),
        "" if end_time is None else str(end_time),
        "" if queue is None else str(queue),
        "" if cores is None else str(cores),
        "" if memory is None else str(memory),
    ]

    color = QColor(status_colors.get(values[2].lower(), DEFAULT_STATUS_COLOR))
    row_items = []
    for col_idx, value in enumerate(values):
        item = QStandardItem(value)
        item.setEditable(col_idx == 3)
        item.setForeground(QBrush(Qt.black))
        if col_idx == 3:
            item.setData(normalized_tune_files, Qt.UserRole)
        item.setBackground(QBrush(color))
        row_items.append(item)
    return row_items


def get_row_items(model, row_index: int, parent_item=None) -> list:
    """Return all items for a model row."""
    if parent_item is None:
        return [model.item(row_index, col) for col in range(model.columnCount())]
    return [parent_item.child(row_index, col) for col in range(model.columnCount())]


def update_target_row_items(row_items: list, status_value: str, start_time: str, end_time: str, status_colors: dict) -> None:
    """Refresh status, colors, and times for an existing main-tree row."""
    if len(row_items) < len(MAIN_TREE_HEADERS):
        return

    normalized_status = "" if status_value is None else str(status_value)
    normalized_start = "" if start_time is None else str(start_time)
    normalized_end = "" if end_time is None else str(end_time)

    status_item = row_items[2]
    start_time_item = row_items[4]
    end_time_item = row_items[5]

    if status_item and normalized_status != status_item.text():
        status_item.setText(normalized_status)
        color = QColor(status_colors.get(normalized_status.lower(), DEFAULT_STATUS_COLOR))
        for item in row_items:
            if item:
                item.setBackground(QBrush(color))

    if start_time_item and normalized_start != start_time_item.text():
        start_time_item.setText(normalized_start)
    if end_time_item and normalized_end != end_time_item.text():
        end_time_item.setText(normalized_end)
