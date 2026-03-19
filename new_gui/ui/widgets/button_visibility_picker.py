"""Popup widget for selecting visible top action buttons."""

from typing import Dict, Iterable, List, Sequence

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from new_gui.ui.visibility_picker_styles import (
    build_visibility_label_style,
    build_visibility_picker_style,
    build_visibility_row_style,
)


class ButtonVisibilityRow(QFrame):
    """One picker row where only the checkbox itself toggles state."""

    def __init__(self, label_text: str, parent: QWidget = None):
        super().__init__(parent)
        self.checkbox = QCheckBox(self)
        self.label = QLabel(label_text, self)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("buttonVisibilityRow")
        self.setStyleSheet(build_visibility_row_style("buttonVisibilityRow"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.checkbox, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.label, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addStretch()

        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet(build_visibility_label_style())

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()


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
        self.setStyleSheet(build_visibility_picker_style("buttonVisibilityPicker"))

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
            row = ButtonVisibilityRow(str(button_label), self)
            row.checkbox.setChecked(button_id in visible_set)
            self._checkbox_container.addWidget(row)
            self._checkboxes[str(button_id)] = row.checkbox

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

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()
