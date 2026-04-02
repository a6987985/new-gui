"""Custom combo box used by the main GUI."""

from PyQt5.QtCore import QPointF, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QComboBox, QCompleter, QPushButton, QStyle, QStyleOptionComboBox

from new_gui.ui.icon_factory import build_search_icon
from new_gui.ui.widgets.scrollbars import RoundedScrollBar


class BoundedComboBox(QComboBox):
    """Custom ComboBox with on-demand search mode and custom dropdown arrow."""

    popup_about_to_show = pyqtSignal()
    _DROP_DOWN_WIDTH = 24
    _SEARCH_BUTTON_SIZE = 20
    _SEARCH_ICON_SIZE = 16
    _SEARCH_ARROW_GAP = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(False)
        self.setMaxVisibleItems(10)
        self._arrow_color = QColor("#555555")
        self._arrow_color_hover = QColor("#333333")
        self._delegate = None

        self.search_btn = QPushButton(self)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedSize(self._SEARCH_BUTTON_SIZE, self._SEARCH_BUTTON_SIZE)
        self.search_btn.setIcon(build_search_icon(size=self._SEARCH_ICON_SIZE))
        self.search_btn.setIconSize(self.search_btn.icon().actualSize(self.search_btn.size()))
        self.search_btn.setFocusPolicy(Qt.NoFocus)
        self.search_btn.setToolTip("Search runs")
        self.search_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """
        )
        self.search_btn.clicked.connect(self.enable_search_mode)
        self.currentIndexChanged.connect(self.disable_search_mode)

        self._popup_scrollbar = RoundedScrollBar(Qt.Vertical, self.view(), show_step_buttons=True)
        self._popup_scrollbar.setFixedWidth(16)
        self._popup_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self.view().setVerticalScrollBar(self._popup_scrollbar)
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view().setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setArrowColor(self, color):
        """Set the dropdown arrow color."""
        self._arrow_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw dropdown arrow."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        arrow_rect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        if arrow_rect.isValid():
            arrow_color = self._arrow_color_hover if opt.state & QStyle.State_MouseOver else self._arrow_color

            pen = QPen(arrow_color)
            pen.setWidthF(1.5)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

            arrow_width = 6
            arrow_height = 3
            gap = 2

            center_x = arrow_rect.center().x()
            center_y = arrow_rect.center().y()

            up_v_tip = QPointF(center_x, center_y - gap - arrow_height)
            up_v_left = QPointF(center_x - arrow_width // 2, center_y - gap)
            up_v_right = QPointF(center_x + arrow_width // 2, center_y - gap)
            painter.drawLine(up_v_left, up_v_tip)
            painter.drawLine(up_v_tip, up_v_right)

            down_v_left = QPointF(center_x - arrow_width // 2, center_y + gap)
            down_v_tip = QPointF(center_x, center_y + gap + arrow_height)
            down_v_right = QPointF(center_x + arrow_width // 2, center_y + gap)
            painter.drawLine(down_v_left, down_v_tip)
            painter.drawLine(down_v_tip, down_v_right)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_search_button()

    def _position_search_button(self):
        """Position search button properly within the ComboBox."""
        btn_size = self.search_btn.size()
        btn_width = btn_size.width()
        btn_height = btn_size.height()

        x = self.width() - self._DROP_DOWN_WIDTH - btn_width - self._SEARCH_ARROW_GAP
        x = max(5, x)

        y = (self.height() - btn_height) // 2
        y = max(1, y)
        self.search_btn.move(x, y)
        self.search_btn.raise_()

    def enable_search_mode(self):
        """Enable editing and focus the line edit."""
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

        if not self.completer() or self.completer().completionMode() != QCompleter.PopupCompletion:
            completer = QCompleter(self.model(), self)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            self.setCompleter(completer)

        self.lineEdit().setFocus()
        self.lineEdit().selectAll()
        self.search_btn.hide()

    def disable_search_mode(self):
        """Disable editing and restore search button."""
        if self.isEditable():
            self.setEditable(False)
        self.search_btn.show()
        self._position_search_button()

    def showPopup(self):
        self.popup_about_to_show.emit()
        super().showPopup()
        popup = self.view().window()
        if popup is not None:
            combo_bottom_left = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(combo_bottom_left)

    def hidePopup(self):
        super().hidePopup()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.lineEdit() and not self.currentText().strip():
            index = self.currentIndex()
            if index >= 0:
                self.setEditText(self.itemText(index))
        QTimer.singleShot(100, self.disable_search_mode)
