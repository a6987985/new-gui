"""Dialog for editing the flow-backed XMETA background color."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from new_gui.services.flow_background import (
    PRESET_XMETA_BACKGROUND_COLORS,
    normalize_background_color,
)
from new_gui.ui.xmeta_background_styles import (
    build_xmeta_background_dialog_style,
    build_xmeta_background_preview_fill_style,
    build_xmeta_background_swatch_style,
)


class XMetaBackgroundDialog(QDialog):
    """Pick one XMETA background color for every run under the active base directory."""

    def __init__(self, initial_color: str, run_count: int, parent=None):
        super().__init__(parent)
        self._selected_color = normalize_background_color(initial_color) or PRESET_XMETA_BACKGROUND_COLORS[0][1]
        self._swatch_buttons = []
        self._run_count = int(run_count)
        self._setup_ui()
        self._refresh_preview()

    def selected_color(self) -> str:
        """Return the normalized color chosen by the user."""
        return self._selected_color

    def _setup_ui(self) -> None:
        """Build the dialog widgets."""
        self.setWindowTitle("Background Color")
        self.setModal(True)
        self.resize(460, 360)
        self.setStyleSheet(build_xmeta_background_dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_label = QLabel("Background Color")
        title_label.setObjectName("xmetaBackgroundTitle")
        layout.addWidget(title_label)

        meta_label = QLabel(
            f"Apply one soft background color to all {self._run_count} runs in the current directory."
        )
        meta_label.setObjectName("xmetaBackgroundMeta")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        preview_frame = QFrame()
        preview_frame.setObjectName("xmetaBackgroundPreview")
        preview_layout = QHBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(12)

        self._preview_chip = QWidget()
        self._preview_chip.setFixedSize(54, 54)
        preview_layout.addWidget(self._preview_chip, 0, Qt.AlignTop)

        preview_text_layout = QVBoxLayout()
        preview_text_layout.setContentsMargins(0, 0, 0, 0)
        preview_text_layout.setSpacing(4)
        preview_title = QLabel("Selected Color")
        preview_title.setObjectName("xmetaBackgroundTitle")
        preview_title.setStyleSheet("font-size: 13px; font-weight: 700;")
        preview_text_layout.addWidget(preview_title)

        self._value_label = QLabel("")
        self._value_label.setObjectName("xmetaBackgroundValue")
        preview_text_layout.addWidget(self._value_label)
        preview_text_layout.addStretch()
        preview_layout.addLayout(preview_text_layout, 1)
        layout.addWidget(preview_frame)

        preset_label = QLabel("Common Colors")
        preset_label.setObjectName("xmetaBackgroundTitle")
        preset_label.setStyleSheet("font-size: 13px; font-weight: 700;")
        layout.addWidget(preset_label)

        preset_grid = QGridLayout()
        preset_grid.setHorizontalSpacing(10)
        preset_grid.setVerticalSpacing(12)

        for index, (label, color_hex) in enumerate(PRESET_XMETA_BACKGROUND_COLORS):
            button = QPushButton()
            button.setToolTip(f"{label} ({color_hex})")
            button.setFixedSize(28, 28)
            button.clicked.connect(
                lambda _checked=False, value=color_hex: self._set_selected_color(value)
            )
            row = index // 6
            column = index % 6
            preset_grid.addWidget(button, row, column)
            self._swatch_buttons.append((button, color_hex))

        layout.addLayout(preset_grid)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        custom_button = QPushButton("Custom...")
        custom_button.setObjectName("xmetaBackgroundActionButton")
        custom_button.clicked.connect(self._pick_custom_color)
        actions_layout.addWidget(custom_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("xmetaBackgroundActionButton")
        cancel_button.clicked.connect(self.reject)
        actions_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply to All Runs")
        apply_button.setObjectName("xmetaBackgroundPrimaryButton")
        apply_button.clicked.connect(self.accept)
        actions_layout.addWidget(apply_button)

        layout.addLayout(actions_layout)

    def _set_selected_color(self, color_hex: str) -> None:
        """Update the currently selected color."""
        normalized = normalize_background_color(color_hex)
        if not normalized:
            return
        self._selected_color = normalized
        self._refresh_preview()

    def _pick_custom_color(self) -> None:
        """Open the Qt color picker for one custom background."""
        color = QColorDialog.getColor(QColor(self._selected_color), self, "Pick Background Color")
        if not color.isValid():
            return
        self._set_selected_color(color.name(QColor.HexRgb))

    def _refresh_preview(self) -> None:
        """Refresh the visible preview and swatch selection."""
        self._preview_chip.setStyleSheet(
            build_xmeta_background_preview_fill_style(self._selected_color)
        )
        self._value_label.setText(self._selected_color.upper())
        for button, color_hex in self._swatch_buttons:
            button.setStyleSheet(
                build_xmeta_background_swatch_style(
                    color_hex,
                    selected=(normalize_background_color(color_hex) == self._selected_color),
                )
            )
