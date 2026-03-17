"""Popup widget for selecting visible columns in the main target tree."""

from typing import Dict, Iterable, List, Sequence

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ColumnVisibilityPicker(QFrame):
    """Popup editor for column visibility with apply/cancel actions."""

    apply_requested = pyqtSignal(list)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("columnVisibilityPicker")
        self._checkboxes: Dict[int, QCheckBox] = {}
        self._locked_columns = set()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QFrame#columnVisibilityPicker {
                background: #ffffff;
                border: 1px solid #d3d9e2;
                border-radius: 8px;
            }
            QCheckBox {
                color: #263238;
                spacing: 6px;
            }
            QPushButton {
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 4px 10px;
                background: #ffffff;
                color: #314154;
            }
            QPushButton:hover {
                background: #f4f8fc;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self._checkbox_container = QVBoxLayout()
        self._checkbox_container.setContentsMargins(0, 0, 0, 0)
        self._checkbox_container.setSpacing(6)
        main_layout.addLayout(self._checkbox_container)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 4, 0, 0)
        button_row.setSpacing(8)
        button_row.addStretch()

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        button_row.addWidget(self._cancel_button)

        self._apply_button = QPushButton("Apply")
        self._apply_button.clicked.connect(self._on_apply_clicked)
        button_row.addWidget(self._apply_button)

        main_layout.addLayout(button_row)

    def set_columns(
        self,
        columns: Sequence[Sequence[object]],
        visible_columns: Iterable[int],
        locked_columns: Iterable[int],
    ) -> None:
        """Rebuild checkbox rows for columns in display order."""
        self._clear_checkboxes()
        visible_set = set(visible_columns or [])
        self._locked_columns = set(locked_columns or [])

        for column_index, column_label in columns:
            checkbox = QCheckBox(str(column_label))
            checkbox.setChecked(column_index in visible_set)
            if column_index in self._locked_columns:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
            self._checkbox_container.addWidget(checkbox)
            self._checkboxes[int(column_index)] = checkbox

    def _clear_checkboxes(self) -> None:
        while self._checkbox_container.count():
            item = self._checkbox_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._checkboxes = {}

    def _on_apply_clicked(self) -> None:
        selected_columns: List[int] = []
        for column_index, checkbox in self._checkboxes.items():
            if checkbox.isChecked():
                selected_columns.append(column_index)

        for locked_column in self._locked_columns:
            if locked_column not in selected_columns:
                selected_columns.append(locked_column)

        self.apply_requested.emit(sorted(selected_columns))

    def _on_cancel_clicked(self) -> None:
        self.cancel_requested.emit()
