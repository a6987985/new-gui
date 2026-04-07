from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QLabel


class _HoverTooltipPopup(QLabel):
    """Simple custom tooltip popup used for light themed hover hints."""

    def __init__(self):
        super().__init__("", None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWordWrap(False)

    def apply_colors(
        self,
        background: str,
        text_color: str,
        border_color: str,
        accent_color: str,
    ) -> None:
        """Apply the tooltip palette to the popup."""
        self.setStyleSheet(
            f"""
                QLabel {{
                    background-color: {background};
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-left: 3px solid {accent_color};
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }}
            """
        )


class ClickableLabel(QLabel):
    """Label that emits a double-click signal and can show a custom light tooltip."""

    doubleClicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._custom_tooltip_text = ""
        self._custom_tooltip_popup = None
        self._custom_tooltip_colors = {
            "background": "#f7fbff",
            "text_color": "#243b53",
            "border_color": "#c9d7e6",
            "accent_color": "#4a90d9",
        }
        self.setMouseTracking(True)

    def set_custom_tooltip(
        self,
        text: str,
        background: str = "#f7fbff",
        text_color: str = "#243b53",
        border_color: str = "#c9d7e6",
        accent_color: str = "#4a90d9",
    ) -> None:
        """Configure a custom-styled tooltip popup for hover feedback."""
        self._custom_tooltip_text = (text or "").strip()
        self._custom_tooltip_colors = {
            "background": background,
            "text_color": text_color,
            "border_color": border_color,
            "accent_color": accent_color,
        }
        super().setToolTip("")

    def _ensure_custom_tooltip_popup(self):
        """Create the popup lazily so normal labels pay no extra cost."""
        if self._custom_tooltip_popup is None:
            self._custom_tooltip_popup = _HoverTooltipPopup()
        self._custom_tooltip_popup.apply_colors(**self._custom_tooltip_colors)
        return self._custom_tooltip_popup

    def _show_custom_tooltip(self) -> None:
        """Show the custom tooltip below the label."""
        if not self._custom_tooltip_text:
            return

        popup = self._ensure_custom_tooltip_popup()
        popup.setText(self._custom_tooltip_text)
        popup.adjustSize()

        anchor = self.mapToGlobal(QPoint(0, self.height() + 8))
        x_pos = anchor.x() + max(0, (self.width() - popup.width()) // 2)
        y_pos = anchor.y()

        screen = QApplication.screenAt(self.mapToGlobal(self.rect().center()))
        if screen is not None:
            geometry = screen.availableGeometry()
            x_pos = max(geometry.left() + 8, min(x_pos, geometry.right() - popup.width() - 8))
            if y_pos + popup.height() > geometry.bottom() - 8:
                y_pos = self.mapToGlobal(QPoint(0, -popup.height() - 8)).y()

        popup.move(x_pos, y_pos)
        popup.show()

    def _hide_custom_tooltip(self) -> None:
        """Hide the custom tooltip when the pointer leaves the label."""
        if self._custom_tooltip_popup is not None:
            self._custom_tooltip_popup.hide()

    def enterEvent(self, event):
        self._show_custom_tooltip()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_custom_tooltip()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self._hide_custom_tooltip()
        super().hideEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._hide_custom_tooltip()
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
