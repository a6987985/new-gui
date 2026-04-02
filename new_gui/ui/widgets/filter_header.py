from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QHeaderView, QLineEdit, QPushButton

class HeaderFilterLineEdit(QLineEdit):
    """Standalone overlay editor used for the target-column filter."""

    escape_pressed = pyqtSignal()
    close_requested = pyqtSignal()
    focus_lost = pyqtSignal()
    options_changed = pyqtSignal()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
            self.close_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_lost.emit()

    def resizeEvent(self, event):
        """Reposition inline search-option buttons when geometry changes."""
        super().resizeEvent(event)
        self._position_option_buttons()

    def _create_option_button(self, text: str, tooltip: str):
        """Build one compact checkable option button for the search box."""
        button = QPushButton(text, self)
        button.setCheckable(True)
        button.setFocusPolicy(Qt.NoFocus)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setFixedHeight(20)
        button.setStyleSheet(
            """
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #6b7280;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 2px;
                }
                QPushButton:hover {
                    color: #374151;
                }
                QPushButton:checked {
                    color: #1f2937;
                    text-decoration: underline;
                }
            """
        )
        button.toggled.connect(lambda _checked: self.options_changed.emit())
        return button

    def _ensure_option_buttons(self) -> None:
        """Create all inline search-option buttons once."""
        if hasattr(self, "_regex_button"):
            return

        self._case_button = self._create_option_button("Aa", "Match case")
        self._whole_word_button = self._create_option_button("ab", "Match whole word")
        self._regex_button = self._create_option_button(".*", "Use regular expression")
        self._option_button_order = [
            self._case_button,
            self._whole_word_button,
            self._regex_button,
        ]
        self._position_option_buttons()

    def _position_option_buttons(self) -> None:
        """Place the inline option buttons near the right side of the editor."""
        if not hasattr(self, "_option_button_order"):
            return

        right_padding = 10
        spacing = 2
        x = self.width() - right_padding
        y = (self.height() - 20) // 2
        for button in reversed(self._option_button_order):
            text_width = self.fontMetrics().horizontalAdvance(button.text())
            button_width = max(20, text_width + 6)
            x -= button_width
            button.setGeometry(x, y, button_width, 20)
            x -= spacing

    def _right_padding_for_options(self) -> int:
        """Return line-edit right padding large enough for the option buttons."""
        if not hasattr(self, "_option_button_order"):
            return 10

        width_sum = 0
        for button in self._option_button_order:
            text_width = self.fontMetrics().horizontalAdvance(button.text())
            width_sum += max(20, text_width + 6)
        spacing = max(0, len(self._option_button_order) - 1) * 2
        return width_sum + spacing + 14

    def setup_search_options_ui(self) -> None:
        """Initialize and style inline search-option buttons."""
        self._ensure_option_buttons()
        right_padding = self._right_padding_for_options()
        self.setStyleSheet(
            f"""
                QLineEdit {{
                    background-color: #ffffff;
                    border: 2px solid #7aa7d9;
                    border-radius: 8px;
                    padding: 4px 10px;
                    padding-right: {right_padding}px;
                    color: #334155;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 2px solid #4f8fda;
                }}
            """
        )
        self._position_option_buttons()

    def set_search_options(self, options: dict) -> None:
        """Apply one full search-options payload without emitting extra updates."""
        self._ensure_option_buttons()
        normalized = options or {}
        for button, option_key in (
            (self._case_button, "case_sensitive"),
            (self._whole_word_button, "whole_word"),
            (self._regex_button, "regex"),
        ):
            was_blocked = button.blockSignals(True)
            button.setChecked(bool(normalized.get(option_key, False)))
            button.blockSignals(was_blocked)

    def get_search_options(self) -> dict:
        """Return current search-option states from inline toggle buttons."""
        self._ensure_option_buttons()
        return {
            "case_sensitive": bool(self._case_button.isChecked()),
            "whole_word": bool(self._whole_word_button.isChecked()),
            "regex": bool(self._regex_button.isChecked()),
        }


class FilterHeaderView(QHeaderView):
    """Custom header with embedded filter input for target column."""

    filter_changed = pyqtSignal(str)
    filter_options_changed = pyqtSignal(dict)
    level_double_clicked = pyqtSignal()

    def __init__(self, orientation, parent=None, filter_column=1):
        super().__init__(orientation, parent)
        self.filter_column = filter_column
        self.filter_edit = None
        self._filter_geometry_updates_enabled = True
        self._filter_visible = False
        self._filter_text = ""
        self._filter_options = {
            "case_sensitive": False,
            "whole_word": False,
            "regex": False,
        }
        self._hovered_section = -1
        self._hovered_handle_section = -1
        self._section_gap = 6
        self._section_v_margin = 6
        self._resize_hint_margin = 7
        self.setSectionsClickable(True)
        self.setMouseTracking(True)
        self.setDefaultAlignment(Qt.AlignCenter)
        self.sectionDoubleClicked.connect(self._on_double_click)
        self.sectionResized.connect(lambda *_: self._update_filter_geometry())
        self.geometriesChanged.connect(self._update_filter_geometry)

    def _section_content_rect(self, logical_index: int) -> QRect:
        section_count = self.count()
        if logical_index < 0 or logical_index >= section_count:
            return QRect()

        header_pos = self.sectionViewportPosition(logical_index)
        header_width = self.sectionSize(logical_index)
        if header_width <= 0:
            return QRect()

        gap = self._section_gap // 2
        return QRect(
            int(header_pos + gap),
            self._section_v_margin,
            max(0, int(header_width - self._section_gap)),
            max(0, int(self.height() - (self._section_v_margin * 2))),
        )

    def get_section_text_margins(self) -> tuple:
        """Return the left/right text margins used when painting section labels."""
        return 14, 20

    def get_minimum_width_for_text(self, text: str) -> int:
        """Return the minimum section width required to show one header label."""
        font = QFont(self.font())
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        text_width = self.fontMetrics().horizontalAdvance(str(text or ""))
        left_margin, right_margin = self.get_section_text_margins()
        return text_width + self._section_gap + left_margin + right_margin + 8

    def _handle_section_at_pos(self, x_pos: int) -> int:
        section_count = self.count()
        for logical_index in range(section_count - 1):
            if self.isSectionHidden(logical_index):
                continue
            boundary_x = self.sectionViewportPosition(logical_index) + self.sectionSize(logical_index)
            if abs(x_pos - boundary_x) <= self._resize_hint_margin:
                return logical_index
        return -1

    def _update_filter_geometry(self):
        if not self.filter_edit:
            return
        if not self._filter_geometry_updates_enabled:
            return

        try:
            if not self.filter_edit.isVisible():
                return
        except RuntimeError:
            self.filter_edit = None
            return

        content_rect = self._section_content_rect(self.filter_column)
        if not content_rect.isValid():
            return

        parent_widget = self.filter_edit.parentWidget()
        if parent_widget is None:
            return

        try:
            top_left = self.mapTo(parent_widget, content_rect.topLeft() + QPoint(2, 2))
        except RuntimeError:
            self.filter_edit = None
            return

        try:
            self.filter_edit.setGeometry(
                top_left.x(),
                top_left.y(),
                max(0, content_rect.width() - 4),
                max(0, content_rect.height() - 4),
            )
        except RuntimeError:
            self.filter_edit = None

    def set_filter_geometry_updates_enabled(self, enabled: bool) -> None:
        """Enable or disable geometry syncing for the embedded filter editor."""
        self._filter_geometry_updates_enabled = bool(enabled)
        if self._filter_geometry_updates_enabled:
            self._update_filter_geometry()

    def _on_double_click(self, logical_index):
        if logical_index == 0:
            self.level_double_clicked.emit()
        elif logical_index == self.filter_column:
            self._toggle_filter()

    def _toggle_filter(self):
        if self._filter_visible:
            self._hide_filter()
        else:
            self._show_filter()

    def _ensure_filter_edit(self):
        """Create the embedded filter editor once and reuse it across show/hide cycles."""
        if self.filter_edit is not None:
            return

        parent_widget = self.parentWidget() or self
        self.filter_edit = HeaderFilterLineEdit(parent_widget)
        self.filter_edit.setup_search_options_ui()
        self.filter_edit.setPlaceholderText("Search targets...")
        self.filter_edit.set_search_options(self._filter_options)
        self.filter_edit.textEdited.connect(self._on_filter_changed)
        self.filter_edit.escape_pressed.connect(self._hide_filter)
        self.filter_edit.close_requested.connect(self._hide_filter)
        self.filter_edit.focus_lost.connect(self._on_filter_focus_lost)
        self.filter_edit.options_changed.connect(self._on_filter_options_changed)
        self.filter_edit.hide()

    def _show_filter(self):
        if self._filter_visible:
            return

        self._ensure_filter_edit()
        self.filter_edit.setPlaceholderText("Search targets...")
        if self.filter_edit.text() != self._filter_text:
            self.filter_edit.setText(self._filter_text)

        self.filter_edit.show()
        self.filter_edit.raise_()
        self._update_filter_geometry()
        self.filter_edit.setFocus()
        self.filter_edit.selectAll()

        self._filter_visible = True
        self.viewport().update()

    def _hide_filter(self):
        if self.filter_edit:
            self._filter_text = self.filter_edit.text()
            self.filter_edit.hide()
        self._filter_visible = False
        self.viewport().update()

    def _on_filter_changed(self, text):
        self._filter_text = text
        self.filter_changed.emit(text)

    def _on_filter_options_changed(self):
        """Mirror inline option toggles and trigger re-filter with current text."""
        if not self.filter_edit:
            return
        self._filter_options = self.filter_edit.get_search_options()
        self.filter_options_changed.emit(dict(self._filter_options))
        self.filter_changed.emit(self._filter_text)

    def _on_filter_focus_lost(self):
        """Hide the filter editor only when it is empty and no longer focused."""
        if not self.filter_edit:
            return
        if self.filter_edit.hasFocus():
            return
        if (self.filter_edit.text() or "").strip():
            return
        self._hide_filter()

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int):
        if not rect.isValid():
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        content_rect = self._section_content_rect(logical_index)
        if not content_rect.isValid():
            painter.restore()
            return

        is_hovered = logical_index == self._hovered_section
        is_filter_active = logical_index == self.filter_column and self._filter_visible
        fill_color = QColor("#fafbfd")
        border_color = QColor("#e4e8ef")
        text_color = QColor("#374151")
        if is_hovered:
            fill_color = QColor("#ffffff")
            border_color = QColor("#d3dbe6")
        if is_filter_active:
            fill_color = QColor("#ffffff")
            border_color = QColor("#7aa7d9")

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(content_rect, 8, 8)

        header_text = ""
        model = self.model()
        if model is not None:
            header_text = str(model.headerData(logical_index, self.orientation(), Qt.DisplayRole) or "")

        font = QFont(self.font())
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(text_color)
        left_margin, right_margin = self.get_section_text_margins()
        painter.drawText(
            content_rect.adjusted(left_margin, 0, -right_margin, 0),
            Qt.AlignCenter,
            header_text,
        )

        painter.restore()

    def mouseMoveEvent(self, event):
        hovered_section = self.logicalIndexAt(event.pos())
        hovered_handle_section = self._handle_section_at_pos(event.pos().x())
        if (
            hovered_section != self._hovered_section
            or hovered_handle_section != self._hovered_handle_section
        ):
            self._hovered_section = hovered_section
            self._hovered_handle_section = hovered_handle_section
            self.viewport().update()

        if hovered_handle_section != -1:
            self.viewport().setCursor(Qt.SplitHCursor)
        else:
            self.viewport().unsetCursor()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered_section = -1
        self._hovered_handle_section = -1
        self.viewport().unsetCursor()
        self.viewport().update()
        super().leaveEvent(event)

    def get_filter_text(self):
        return self._filter_text

    def get_filter_options(self):
        """Return active search behavior flags for header filtering."""
        return dict(self._filter_options)

    def set_filter_text(self, text):
        self._filter_text = text
        if self.filter_edit:
            self.filter_edit.setText(text)

    def set_filter_options(self, options: dict) -> None:
        """Set active search behavior flags for header filtering."""
        normalized = {
            "case_sensitive": bool((options or {}).get("case_sensitive", False)),
            "whole_word": bool((options or {}).get("whole_word", False)),
            "regex": bool((options or {}).get("regex", False)),
        }
        self._filter_options = normalized
        if self.filter_edit:
            self.filter_edit.set_search_options(normalized)

    def show_filter(self):
        """Public method to show filter."""
        self._show_filter()

    def hide_filter(self):
        """Public method to hide filter."""
        self._hide_filter()
