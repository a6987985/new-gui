from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel


class ClickableLabel(QLabel):
    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class StatusBadgeLabel(QLabel):
    """Small status badge that emits the status key on double click."""

    statusDoubleClicked = pyqtSignal(str)

    def __init__(self, status_key, text, parent=None):
        super().__init__(text, parent)
        self._status_key = status_key
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Double-click to filter targets by this status")

    def mouseDoubleClickEvent(self, event):
        self.statusDoubleClicked.emit(self._status_key)
        super().mouseDoubleClickEvent(event)


# ========== Theme Manager ==========
