"""Tree-view layout helpers for width calculations and adaptive fitting."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QHeaderView


MAIN_TREE_TIME_COLUMNS = (4, 5)
MAIN_TREE_TIME_FORMAT_SAMPLE = "YYYY-MM-DD HH:MM:SS"
# Leave room for the item padding applied by the tree style and small font
# fallback differences across platforms.
MAIN_TREE_TIME_HORIZONTAL_PADDING = 40


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


def get_main_view_time_column_width(tree) -> int:
    """Return the fixed width needed to show one full timestamp value."""
    font_metrics = tree.fontMetrics()
    return font_metrics.horizontalAdvance(MAIN_TREE_TIME_FORMAT_SAMPLE) + MAIN_TREE_TIME_HORIZONTAL_PADDING


def get_main_view_min_column_widths(tree, header_min_widths: Dict[int, int]) -> Dict[int, int]:
    """Return main-tree minimum widths that protect fixed-width data columns."""
    min_widths = dict(header_min_widths or {})
    time_width = get_main_view_time_column_width(tree)
    for column in MAIN_TREE_TIME_COLUMNS:
        min_widths[column] = max(min_widths.get(column, 0), time_width)
    return min_widths


def get_main_view_default_column_widths(tree) -> Dict[int, int]:
    """Return default main-view column widths for the active tree font."""
    font_metrics = tree.fontMetrics()
    status_values = ["finish", "running", "failed", "skip", "scheduled", "pending"]
    status_width = max(font_metrics.horizontalAdvance(status) for status in status_values) + 20

    time_width = get_main_view_time_column_width(tree)

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


def resolve_viewport_width(tree, viewport_width: Optional[int] = None) -> int:
    """Return one effective viewport width, honoring any precomputed override."""
    if viewport_width is not None:
        return max(0, int(viewport_width))
    return max(0, tree.viewport().width())


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


def apply_adaptive_column_width(
    tree,
    model,
    header_min_widths: Dict[int, int],
    column: int = 1,
    viewport_width: Optional[int] = None,
) -> None:
    """Stretch one target column to absorb viewport width changes."""
    if model.columnCount() <= column or tree.isColumnHidden(column):
        return

    viewport_width = resolve_viewport_width(tree, viewport_width)
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


def fill_trailing_blank_with_last_column(
    tree,
    model,
    header_min_widths: Dict[int, int],
    viewport_width: Optional[int] = None,
) -> None:
    """Adjust the right-most visible column to keep the viewport edge flush."""
    visible_columns = get_visible_columns(tree, model)
    if not visible_columns:
        return

    viewport_width = resolve_viewport_width(tree, viewport_width)
    if viewport_width <= 0:
        return

    current_total_width = sum(tree.columnWidth(column) for column in visible_columns)
    width_delta = viewport_width - current_total_width
    if width_delta == 0:
        return

    if width_delta > 0:
        last_column = visible_columns[-1]
        current_last_width = tree.columnWidth(last_column)
        min_last_width = header_min_widths.get(last_column, 0)
        new_last_width = max(min_last_width, current_last_width + int(width_delta))
        if new_last_width != current_last_width:
            tree.setColumnWidth(last_column, new_last_width)
        return

    overflow = abs(int(width_delta))
    for column in reversed(visible_columns):
        if overflow <= 0:
            break
        current_width = tree.columnWidth(column)
        min_width = header_min_widths.get(column, 0)
        shrinkable_width = max(0, current_width - min_width)
        if shrinkable_width <= 0:
            continue
        shrink_amount = min(shrinkable_width, overflow)
        tree.setColumnWidth(column, current_width - shrink_amount)
        overflow -= shrink_amount
