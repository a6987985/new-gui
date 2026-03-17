"""Popup widget for selecting visible top action buttons."""

from typing import Dict, Iterable, List, Sequence

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ButtonVisibilityPicker(QFrame):
    """Popup editor for top-button visibility with apply/cancel actions."""

    apply_requested = pyqtSignal(list)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("buttonVisibilityPicker")
        self._checkboxes: Dict[str, QCheckBox] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QFrame#buttonVisibilityPicker {
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

    def set_buttons(
        self,
        buttons: Sequence[Sequence[str]],
        visible_button_ids: Iterable[str],
    ) -> None:
        """Rebuild checkbox rows for top buttons in display order."""
        self._clear_checkboxes()
        visible_set = set(visible_button_ids or [])

        for button_id, button_label in buttons:
            checkbox = QCheckBox(str(button_label))
            checkbox.setChecked(button_id in visible_set)
            self._checkbox_container.addWidget(checkbox)
            self._checkboxes[str(button_id)] = checkbox

    def _clear_checkboxes(self) -> None:
        while self._checkbox_container.count():
            item = self._checkbox_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._checkboxes = {}

    def _on_apply_clicked(self) -> None:
        selected_button_ids: List[str] = []
        for button_id, checkbox in self._checkboxes.items():
            if checkbox.isChecked():
                selected_button_ids.append(button_id)
        self.apply_requested.emit(selected_button_ids)

    def _on_cancel_clicked(self) -> None:
        self.cancel_requested.emit()
