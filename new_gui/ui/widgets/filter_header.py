from PyQt5.QtCore import QEvent, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QHeaderView, QLineEdit


class FilterHeaderView(QHeaderView):
    """Custom header with embedded filter input for target column."""

    filter_changed = pyqtSignal(str)
    level_double_clicked = pyqtSignal()

    def __init__(self, orientation, parent=None, filter_column=1):
        super().__init__(orientation, parent)
        self.filter_column = filter_column
        self.filter_edit = None
        self._filter_visible = False
        self._filter_text = ""
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

        content_rect = self._section_content_rect(self.filter_column)
        if not content_rect.isValid():
            return

        self.filter_edit.setGeometry(content_rect.adjusted(2, 2, -2, -2))

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

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setStyleSheet(
            """
                QLineEdit {
                    background-color: #ffffff;
                    border: 2px solid #7aa7d9;
                    border-radius: 8px;
                    padding: 4px 10px;
                    color: #334155;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 2px solid #4f8fda;
                }
            """
        )
        self.filter_edit.setPlaceholderText("Search targets...")
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.filter_edit.installEventFilter(self)
        self.filter_edit.hide()

    def _show_filter(self):
        if self._filter_visible:
            return

        self._ensure_filter_edit()
        self.filter_edit.setPlaceholderText("Search targets...")
        if self.filter_edit.text() != self._filter_text:
            self.filter_edit.setText(self._filter_text)
        self._update_filter_geometry()

        self.filter_edit.show()
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

    def eventFilter(self, obj, event):
        if obj == self.filter_edit:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._hide_filter()
                    return True
                if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                    self._hide_filter()
                    return True
        return super().eventFilter(obj, event)

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

    def set_filter_text(self, text):
        self._filter_text = text
        if self.filter_edit:
            self.filter_edit.setText(text)

    def show_filter(self):
        """Public method to show filter."""
        self._show_filter()

    def hide_filter(self):
        """Public method to hide filter."""
        self._hide_filter()
