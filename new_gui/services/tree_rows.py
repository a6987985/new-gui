"""Helpers for building and refreshing main tree rows."""

from typing import Dict, List, Optional, Sequence, Tuple

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

TuneFileEntry = Tuple[str, str]
StatusColors = Dict[str, str]
RowItems = List[QStandardItem]

ROW_KIND_ROLE = Qt.UserRole + 10
TARGET_NAME_ROLE = Qt.UserRole + 11
DESCENDANT_TARGETS_ROLE = Qt.UserRole + 12

ROW_KIND_TARGET = "target"
ROW_KIND_GROUP = "group"
ROW_KIND_LEVEL = "level"


def set_main_tree_headers(model) -> None:
    """Apply the standard headers used by the main target tree."""
    model.setHorizontalHeaderLabels(MAIN_TREE_HEADERS)


def reset_main_tree_model(model, set_column_widths) -> None:
    """Clear and reinitialize the main target tree model."""
    model.clear()
    set_main_tree_headers(model)
    set_column_widths()


def _apply_row_metadata(
    row_items: RowItems,
    row_kind: str,
    target_name: str = "",
    descendant_targets: Optional[Sequence[str]] = None,
) -> RowItems:
    """Attach row-kind metadata used by selection and filtering helpers."""
    normalized_targets = [target for target in list(descendant_targets or []) if target]
    normalized_target_name = target_name or ""
    for item in row_items:
        if item is None:
            continue
        item.setData(row_kind, ROW_KIND_ROLE)
        item.setData(normalized_target_name, TARGET_NAME_ROLE)
        item.setData(normalized_targets, DESCENDANT_TARGETS_ROLE)
    return row_items


def build_target_row_items(
    level_text,
    target_name: str,
    status_value: str,
    tune_files: Sequence[TuneFileEntry],
    start_time: str,
    end_time: str,
    queue: str,
    cores: str,
    memory: str,
    status_colors: StatusColors,
    tune_display: Optional[str] = None,
) -> RowItems:
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
    row_items: RowItems = []
    for col_idx, value in enumerate(values):
        item = QStandardItem(value)
        item.setEditable(col_idx == 3)
        item.setForeground(QBrush(Qt.black))
        if col_idx == 3:
            item.setData(normalized_tune_files, Qt.UserRole)
        item.setBackground(QBrush(color))
        row_items.append(item)
    return _apply_row_metadata(
        row_items,
        ROW_KIND_TARGET,
        target_name=target_name,
        descendant_targets=[target_name],
    )


def build_container_row_items(
    level_text,
    label_text: str,
    row_kind: str,
    descendant_targets: Optional[Sequence[str]] = None,
    status_value: str = "",
    status_key: str = "",
    status_colors: Optional[StatusColors] = None,
) -> RowItems:
    """Build a non-leaf row used for level and synthetic group containers."""
    normalized_status = "" if status_value is None else str(status_value)
    values = [
        "" if level_text is None else str(level_text),
        "" if label_text is None else str(label_text),
        normalized_status,
        "",
        "",
        "",
        "",
        "",
        "",
    ]

    row_items: RowItems = []
    effective_colors = status_colors or {}
    normalized_status_key = (status_key or "").strip().lower()
    color_hex = (
        effective_colors.get(normalized_status_key, DEFAULT_STATUS_COLOR)
        if normalized_status_key
        else DEFAULT_STATUS_COLOR
    )
    background_color = QColor(color_hex)
    for col_idx, value in enumerate(values):
        item = QStandardItem(value)
        item.setEditable(False)
        item.setForeground(QBrush(Qt.black))
        item.setBackground(QBrush(background_color))
        if row_kind == ROW_KIND_LEVEL and col_idx in (0, 1):
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        row_items.append(item)

    return _apply_row_metadata(
        row_items,
        row_kind,
        descendant_targets=descendant_targets,
    )


def update_container_row_items(
    row_items: RowItems,
    status_value: str,
    status_key: str,
    status_colors: StatusColors,
) -> None:
    """Refresh a synthetic container row using an aggregated status value."""
    if len(row_items) < len(MAIN_TREE_HEADERS):
        return

    normalized_status = "" if status_value is None else str(status_value)
    status_item = row_items[2]
    if status_item and normalized_status != status_item.text():
        status_item.setText(normalized_status)

    normalized_status_key = (status_key or "").strip().lower()
    color_hex = (
        status_colors.get(normalized_status_key, DEFAULT_STATUS_COLOR)
        if normalized_status_key
        else DEFAULT_STATUS_COLOR
    )
    color = QColor(color_hex)
    for item in row_items:
        if item is not None:
            item.setBackground(QBrush(color))


def get_row_items(model, row_index: int, parent_item=None) -> RowItems:
    """Return all items for a model row."""
    if parent_item is None:
        return [model.item(row_index, col) for col in range(model.columnCount())]
    return [parent_item.child(row_index, col) for col in range(model.columnCount())]


def get_row_kind(item) -> str:
    """Return the metadata row kind for a tree item."""
    if item is None:
        return ""
    return item.data(ROW_KIND_ROLE) or ""


def get_row_target_name(item) -> str:
    """Return the real leaf-target name for a row, if any."""
    if item is None:
        return ""
    return item.data(TARGET_NAME_ROLE) or ""


def get_row_targets(item) -> List[str]:
    """Return descendant real targets represented by a row."""
    if item is None:
        return []
    if get_row_kind(item) == ROW_KIND_TARGET:
        target_name = get_row_target_name(item)
        return [target_name] if target_name else []
    descendant_targets = item.data(DESCENDANT_TARGETS_ROLE) or []
    return [target for target in descendant_targets if target]


def update_target_row_items(
    row_items: RowItems,
    status_value: str,
    start_time: str,
    end_time: str,
    queue: str,
    cores: str,
    memory: str,
    status_colors: StatusColors,
) -> None:
    """Refresh status, colors, times, and BSUB fields for an existing main-tree row."""
    if len(row_items) < len(MAIN_TREE_HEADERS):
        return

    normalized_status = "" if status_value is None else str(status_value)
    normalized_start = "" if start_time is None else str(start_time)
    normalized_end = "" if end_time is None else str(end_time)
    normalized_queue = "" if queue is None else str(queue)
    normalized_cores = "" if cores is None else str(cores)
    normalized_memory = "" if memory is None else str(memory)

    status_item = row_items[2]
    start_time_item = row_items[4]
    end_time_item = row_items[5]
    queue_item = row_items[6]
    cores_item = row_items[7]
    memory_item = row_items[8]

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
    if queue_item and normalized_queue != queue_item.text():
        queue_item.setText(normalized_queue)
    if cores_item and normalized_cores != cores_item.text():
        cores_item.setText(normalized_cores)
    if memory_item and normalized_memory != memory_item.text():
        memory_item.setText(normalized_memory)
