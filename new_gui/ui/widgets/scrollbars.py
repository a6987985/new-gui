from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPolygonF
from PyQt5.QtWidgets import QScrollBar, QStyle, QStyleOptionSlider


class RoundedScrollBar(QScrollBar):
    """Custom ScrollBar with rounded corners on all sides - works across platforms"""

    def __init__(self, orientation, parent=None, show_step_buttons=False):
        super().__init__(orientation, parent)
        self._handle_color = QColor("#b0b0b0")
        self._handle_color_hover = QColor("#909090")
        self._handle_color_pressed = QColor("#707070")
        self._track_color = QColor("#f0f0f0")
        self._button_color = QColor("#ececec")
        self._arrow_color = QColor("#8b8b8b")
        self._border_radius = 7.0
        self._hover = False
        self._pressed = False
        self._show_step_buttons = show_step_buttons

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        # Ensure custom painting does not leave transparent pixels that reveal parent backgrounds.
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def setColors(self, handle_color, handle_hover, handle_pressed, track_color):
        """Update scrollbar colors (for theme support)"""
        self._handle_color = QColor(handle_color)
        self._handle_color_hover = QColor(handle_hover)
        self._handle_color_pressed = QColor(handle_pressed)
        self._track_color = QColor(track_color)
        self._button_color = QColor(track_color).darker(104)
        self.update()

    def _style_subcontrol_rect(self, control):
        """Return the style-calculated geometry for a scrollbar sub-control."""
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        return self.style().subControlRect(QStyle.CC_ScrollBar, option, control, self)

    def _draw_step_button(self, painter, rect, direction):
        """Draw a rounded step button with a simple triangular arrow."""
        if not self._show_step_buttons or not rect.isValid() or rect.width() < 4 or rect.height() < 4:
            return

        button_rect = rect.adjusted(1, 1, -1, -1)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._button_color)
        painter.drawRoundedRect(button_rect, self._border_radius, self._border_radius)

        painter.setBrush(self._arrow_color)
        center = button_rect.center()
        if self.orientation() == Qt.Vertical:
            if direction == "up":
                points = QPolygonF([
                    QPointF(center.x(), center.y() - 3),
                    QPointF(center.x() - 4, center.y() + 2),
                    QPointF(center.x() + 4, center.y() + 2),
                ])
            else:
                points = QPolygonF([
                    QPointF(center.x(), center.y() + 3),
                    QPointF(center.x() - 4, center.y() - 2),
                    QPointF(center.x() + 4, center.y() - 2),
                ])
        else:
            if direction == "left":
                points = QPolygonF([
                    QPointF(center.x() - 3, center.y()),
                    QPointF(center.x() + 2, center.y() - 4),
                    QPointF(center.x() + 2, center.y() + 4),
                ])
            else:
                points = QPolygonF([
                    QPointF(center.x() + 3, center.y()),
                    QPointF(center.x() - 2, center.y() - 4),
                    QPointF(center.x() - 2, center.y() + 4),
                ])
        painter.drawPolygon(points)

    def paintEvent(self, event):
        """Custom paint event to draw rounded scrollbar - platform independent"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Paint a solid base first to avoid theme background bleed-through around antialiased corners.
        painter.fillRect(self.rect(), self._track_color)

        groove_rect = self._style_subcontrol_rect(QStyle.SC_ScrollBarGroove)
        slider_rect = self._style_subcontrol_rect(QStyle.SC_ScrollBarSlider)
        sub_line_rect = self._style_subcontrol_rect(QStyle.SC_ScrollBarSubLine)
        add_line_rect = self._style_subcontrol_rect(QStyle.SC_ScrollBarAddLine)

        painter.setPen(Qt.NoPen)
        if groove_rect.isValid():
            painter.setBrush(self._track_color)
            groove_draw_rect = groove_rect.adjusted(1, 1, -1, -1)
            painter.drawRoundedRect(groove_draw_rect, self._border_radius, self._border_radius)

        self._draw_step_button(
            painter,
            sub_line_rect,
            "up" if self.orientation() == Qt.Vertical else "left",
        )
        self._draw_step_button(
            painter,
            add_line_rect,
            "down" if self.orientation() == Qt.Vertical else "right",
        )

        if not slider_rect.isValid() or slider_rect.width() < 2 or slider_rect.height() < 2:
            return

        # Determine handle color based on state
        if self._pressed:
            handle_color = self._handle_color_pressed
        elif self._hover:
            handle_color = self._handle_color_hover
        else:
            handle_color = self._handle_color

        # Draw rounded handle
        painter.setBrush(handle_color)
        painter.setPen(Qt.NoPen)

        # Add small margin for visual padding
        margin = 2
        adjusted = slider_rect.adjusted(margin, margin, -margin, -margin)
        if adjusted.width() < 4 or adjusted.height() < 4:
            adjusted = slider_rect

        # Draw the rounded rectangle
        painter.drawRoundedRect(adjusted, self._border_radius, self._border_radius)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._pressed = True
        self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._pressed = False
        self.update()


