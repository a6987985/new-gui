"""Dialog for choosing one fixed core value with color-coded guidance."""

from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from new_gui.services.tree_editing import CORE_VALUE_OPTIONS
from new_gui.ui.core_selection_styles import build_core_selection_dialog_style


_TONE_COLORS = {
    "recommended": "#15803d",
    "warning": "#b45309",
    "danger": "#b91c1c",
}
_DEFAULT_CORE_VALUE = "4"


class CoreSelectionDialog(QDialog):
    """Choose one fixed core value for the active target."""

    def __init__(self, target_name: str, current_value: str, parent=None):
        super().__init__(parent)
        self._target_name = target_name
        self._current_value = str(current_value or "").strip()
        self._button_group = QButtonGroup(self)
        self._setup_ui()

    def selected_core_value(self) -> str:
        """Return the selected core count."""
        checked = self._button_group.checkedButton()
        if checked is None:
            return ""
        return str(checked.property("core_value") or "").strip()

    def _setup_ui(self) -> None:
        """Build the dialog widgets."""
        self.setWindowTitle("Select Cores")
        self.setModal(True)
        self.resize(420, 320)
        self.setStyleSheet(build_core_selection_dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_label = QLabel("Core Selection")
        title_label.setObjectName("coreSelectionTitle")
        layout.addWidget(title_label)

        meta_label = QLabel(f"Choose one fixed core value for target '{self._target_name}'.")
        meta_label.setObjectName("coreSelectionMeta")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        list_frame = QFrame()
        list_frame.setObjectName("coreSelectionListFrame")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(6)

        preferred_value = self._current_value if self._current_value in {
            option["value"] for option in CORE_VALUE_OPTIONS
        } else _DEFAULT_CORE_VALUE

        for option in CORE_VALUE_OPTIONS:
            row_frame = QFrame()
            row_frame.setObjectName("coreSelectionOptionFrame")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(8)

            button = QRadioButton(option["label"])
            button.setProperty("core_value", option["value"])
            button.setStyleSheet(f"color: {_TONE_COLORS.get(option['tone'], '#334155')};")
            self._button_group.addButton(button)
            row_layout.addWidget(button)
            row_layout.addStretch()

            if option["value"] == preferred_value:
                button.setChecked(True)

            list_layout.addWidget(row_frame)

        layout.addWidget(list_frame, 1)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("coreSelectionActionButton")
        cancel_button.clicked.connect(self.reject)
        actions_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply")
        apply_button.setObjectName("coreSelectionPrimaryButton")
        apply_button.clicked.connect(self.accept)
        actions_layout.addWidget(apply_button)
        layout.addLayout(actions_layout)
