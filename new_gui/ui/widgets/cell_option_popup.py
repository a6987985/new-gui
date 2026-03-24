"""Compact popup list used for cell-anchored single-choice selection."""

from typing import Iterable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from new_gui.ui.cell_option_popup_styles import build_cell_option_popup_style


_TONE_COLORS = {
    "recommended": "#15803d",
    "warning": "#b45309",
    "danger": "#b91c1c",
}


class CellOptionPopup(QDialog):
    """Display one compact single-selection list anchored to a tree cell."""

    def __init__(self, options: Iterable[dict], current_value: str = "", parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self._options: List[dict] = list(options)
        self._current_value = str(current_value or "").strip()
        self._selected_value = ""
        self._table: Optional[QTableWidget] = None
        self._setup_ui()

    def selected_value(self) -> str:
        """Return the selected option value."""
        return self._selected_value

    def choose_at(self, global_pos, min_width: int = 0) -> str:
        """Open the popup at one global point and return the chosen value."""
        self._resize_to_content(min_width=min_width)
        self.move(global_pos)
        if self.exec_() == QDialog.Accepted:
            return self._selected_value
        return ""

    def _setup_ui(self) -> None:
        """Build the popup table."""
        self.setStyleSheet(build_cell_option_popup_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        table = QTableWidget(len(self._options), 1, self)
        table.setHorizontalHeaderLabels(["Value"])
        table.horizontalHeader().hide()
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setShowGrid(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setFocusPolicy(Qt.StrongFocus)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)
        table.setAlternatingRowColors(False)
        table.itemClicked.connect(self._handle_item_clicked)
        table.itemActivated.connect(self._handle_item_clicked)
        table.itemEntered.connect(self._handle_item_entered)

        preferred_row = 0
        for row, option in enumerate(self._options):
            value = str(option.get("value") or "").strip()
            label = str(option.get("label") or value)
            item = QTableWidgetItem(label)
            item.setData(Qt.UserRole, value)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            tone = str(option.get("tone") or "").strip()
            if tone in _TONE_COLORS:
                item.setForeground(QBrush(QColor(_TONE_COLORS[tone])))
            table.setItem(row, 0, item)
            table.setRowHeight(row, 26)
            if value == self._current_value:
                preferred_row = row

        if self._options:
            table.selectRow(preferred_row)
            self._selected_value = str(self._options[preferred_row].get("value") or "")

        layout.addWidget(table)
        self._table = table

    def _resize_to_content(self, min_width: int = 0) -> None:
        """Size the popup to fit the option list while staying compact."""
        if self._table is None:
            return

        row_count = max(1, self._table.rowCount())
        visible_rows = min(row_count, 8)
        height = (visible_rows * 26) + 6
        width = max(int(min_width * 0.6), 96)
        self.resize(width, height)

    def _handle_item_entered(self, item: QTableWidgetItem) -> None:
        """Keep hover movement visually aligned with the current row highlight."""
        if self._table is None:
            return
        self._table.setCurrentItem(item)
        self._table.selectRow(item.row())

    def _handle_item_clicked(self, item: QTableWidgetItem) -> None:
        """Accept the clicked item immediately to mimic a dropdown."""
        self._selected_value = str(item.data(Qt.UserRole) or "").strip()
        self.accept()
