from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import QHeaderView, QLineEdit


class FilterHeaderView(QHeaderView):
    """Custom header with embedded filter input for target column"""

    filter_changed = pyqtSignal(str)
    level_double_clicked = pyqtSignal()

    def __init__(self, orientation, parent=None, filter_column=1):
        super().__init__(orientation, parent)
        self.filter_column = filter_column
        self.filter_edit = None
        self._filter_visible = False
        self._filter_text = ""
        self.setSectionsClickable(True)
        self.sectionDoubleClicked.connect(self._on_double_click)

    def _on_double_click(self, logical_index):
        if logical_index == 0:
            # Double-clicked on level column - toggle tree expansion
            self.level_double_clicked.emit()
        elif logical_index == self.filter_column:
            self._toggle_filter()

    def _toggle_filter(self):
        if self._filter_visible:
            self._hide_filter()
        else:
            self._show_filter()

    def _show_filter(self):
        if self._filter_visible:
            return

        # Create QLineEdit overlay at target column position
        self.filter_edit = QLineEdit(self)
        self.filter_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #1976d2;
                border-radius: 4px;
                padding: 2px 6px;
                color: #333333;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
            }
        """)
        self.filter_edit.setPlaceholderText("Search targets...")
        self.filter_edit.setText(self._filter_text)

        # Position the filter at the target column header
        header_pos = self.sectionViewportPosition(self.filter_column)
        header_width = self.sectionSize(self.filter_column)
        header_height = self.height()

        # Account for header offset (first column might be hidden or offset)
        offset = self.offset()
        self.filter_edit.setGeometry(int(header_pos - offset), 0, header_width, header_height)

        self.filter_edit.show()
        self.filter_edit.setFocus()
        self.filter_edit.selectAll()

        # Connect signals
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.filter_edit.installEventFilter(self)

        self._filter_visible = True

    def _hide_filter(self):
        if self.filter_edit:
            self._filter_text = self.filter_edit.text()
            self.filter_edit.deleteLater()
            self.filter_edit = None
        self._filter_visible = False

    def _on_filter_changed(self, text):
        self._filter_text = text
        self.filter_changed.emit(text)

    def eventFilter(self, obj, event):
        if obj == self.filter_edit:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._hide_filter()
                    return True
                elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
                    self._hide_filter()
                    return True
                elif event.key() == Qt.Key_Tab:
                    self._hide_filter()
                    return True
            elif event.type() == QEvent.FocusOut:
                # Hide filter when focus is lost
                if self.filter_edit and not self.filter_edit.hasFocus():
                    self._hide_filter()
                    return True
        return super().eventFilter(obj, event)

    def get_filter_text(self):
        return self._filter_text

    def set_filter_text(self, text):
        self._filter_text = text
        if self.filter_edit:
            self.filter_edit.setText(text)

    def show_filter(self):
        """Public method to show filter"""
        self._show_filter()

    def hide_filter(self):
        """Public method to hide filter"""
        self._hide_filter()


