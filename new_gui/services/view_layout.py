"""Tree-view layout helpers for width calculations and adaptive fitting."""

from __future__ import annotations

from typing import Dict, Iterable, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QHeaderView


def get_header_min_widths(model, header) -> Dict[int, int]:
    """Calculate minimum widths required to keep header text fully visible."""
    if model is None or header is None:
        return {}

    header_font = QFont(header.font())
    header_font.setPointSize(10)
    header_font.setWeight(QFont.DemiBold)
    font_metrics = QFontMetrics(header_font)
    min_widths: Dict[int, int] = {}

    for column in range(model.columnCount()):
        header_text = model.headerData(column, Qt.Horizontal) or ""
        if hasattr(header, "get_minimum_width_for_text"):
            text_based_min = header.get_minimum_width_for_text(str(header_text))
        else:
            text_based_min = font_metrics.horizontalAdvance(str(header_text)) + 30
        style_based_min = header.sectionSizeFromContents(column).width() + 8
        min_widths[column] = max(text_based_min, style_based_min)

    return min_widths


def get_main_view_default_column_widths(tree) -> Dict[int, int]:
    """Return default main-view column widths for the active tree font."""
    font_metrics = tree.fontMetrics()
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


def get_main_view_default_window_width(tree, column_widths: Dict[int, int]) -> int:
    """Estimate startup window width from tree column widths and frame metrics."""
    tree_content_width = sum(column_widths.values())
    scrollbar_width = tree.verticalScrollBar().sizeHint().width()
    frame_width = tree.frameWidth() * 2
    return tree_content_width + scrollbar_width + frame_width


def get_visible_columns(tree, model) -> List[int]:
    """Return all visible model columns in visual order."""
    return [column for column in range(model.columnCount()) if not tree.isColumnHidden(column)]


def apply_all_status_column_widths(tree, model, header_min_widths: Dict[int, int]) -> None:
    """Apply adaptive widths for the four-column all-status table schema."""
    if model.columnCount() < 4:
        return
    header = tree.header()
    if header is None:
        return

    header.setStretchLastSection(False)
    for column in range(model.columnCount()):
        header.setSectionResizeMode(column, QHeaderView.Interactive)

    tree.resizeColumnToContents(0)
    tree.resizeColumnToContents(2)
    tree.resizeColumnToContents(3)

    for column in range(4):
        min_width = header_min_widths.get(column, 0)
        if min_width > 0:
            tree.setColumnWidth(column, max(tree.columnWidth(column), min_width))


def apply_adaptive_column_width(tree, model, header_min_widths: Dict[int, int], column: int = 1) -> None:
    """Stretch one target column to absorb viewport width changes."""
    if model.columnCount() <= column or tree.isColumnHidden(column):
        return

    viewport_width = tree.viewport().width()
    if viewport_width <= 0:
        return

    current_target_width = tree.columnWidth(column)
    min_target_width = header_min_widths.get(column, 0)
    visible_columns = get_visible_columns(tree, model)
    if not visible_columns:
        return

    current_total_width = sum(tree.columnWidth(col) for col in visible_columns)
    width_delta = viewport_width - current_total_width
    new_target_width = max(min_target_width, current_target_width + width_delta)
    if new_target_width != current_target_width:
        tree.setColumnWidth(column, new_target_width)


def fill_trailing_blank_with_last_column(tree, model, header_min_widths: Dict[int, int]) -> None:
    """Expand the right-most visible column to remove trailing blank space."""
    visible_columns = get_visible_columns(tree, model)
    if not visible_columns:
        return

    viewport_width = tree.viewport().width()
    if viewport_width <= 0:
        return

    last_column = visible_columns[-1]
    current_total_width = sum(tree.columnWidth(column) for column in visible_columns)
    width_delta = viewport_width - current_total_width
    if width_delta <= 0:
        return

    current_last_width = tree.columnWidth(last_column)
    min_last_width = header_min_widths.get(last_column, 0)
    new_last_width = max(min_last_width, current_last_width + width_delta)
    if new_last_width != current_last_width:
        tree.setColumnWidth(last_column, new_last_width)
