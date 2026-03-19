"""Notification widgets and manager used by the main GUI."""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QTimer, QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from new_gui.config.settings import (
    ANIMATION_DURATION_MS,
    MAX_NOTIFICATIONS,
    NOTIFICATION_MARGIN_BOTTOM,
    NOTIFICATION_MARGIN_RIGHT,
    NOTIFICATION_SPACING,
    NOTIFICATION_TYPES,
)
from new_gui.ui.notification_styles import (
    build_notification_close_button_style,
    build_notification_frame_style,
    build_notification_icon_style,
    build_notification_message_style,
    build_notification_title_style,
)


class NotificationWidget(QFrame):
    """A single notification widget that shows at the corner of the screen."""

    dismiss_requested = pyqtSignal()

    def __init__(self, title, message, notification_type="info", parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.title = title
        self.message = message

        self._setup_ui()
        self._start_animation()

    def _setup_ui(self):
        """Setup the notification UI."""
        config = NOTIFICATION_TYPES.get(self.notification_type, NOTIFICATION_TYPES["info"])

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setFixedWidth(350)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        icon_label = QLabel(config["icon"])
        icon_label.setStyleSheet(build_notification_icon_style(config["color"]))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(self.title)
        title_label.setStyleSheet(build_notification_title_style())
        text_layout.addWidget(title_label)

        message_label = QLabel(self.message)
        message_label.setStyleSheet(build_notification_message_style())
        message_label.setWordWrap(True)
        text_layout.addWidget(message_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(build_notification_close_button_style())
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

        self.setStyleSheet(build_notification_frame_style(config["color"]))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

    def _start_animation(self):
        """Start the entrance animation."""
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(ANIMATION_DURATION_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

    def fade_out(self):
        """Start fade out animation."""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(ANIMATION_DURATION_MS)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.finished.connect(self.deleteLater)
        self._fade_anim.start()

    def _on_close(self):
        """Handle close button click."""
        self.dismiss_requested.emit()

    def mousePressEvent(self, event):
        """Handle click on notification."""
        if event.button() == Qt.LeftButton:
            self.dismiss_requested.emit()
        super().mousePressEvent(event)


class NotificationManager(QObject):
    """Manage notification widgets at the corner of the screen."""

    _instance = None

    def __new__(cls, parent=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return
        super().__init__(parent)
        self._initialized = True
        self._notifications = []
        self._parent = parent
        self._max_notifications = MAX_NOTIFICATIONS
        self._spacing = NOTIFICATION_SPACING
        self._margin_bottom = NOTIFICATION_MARGIN_BOTTOM
        self._margin_right = NOTIFICATION_MARGIN_RIGHT

    def show_notification(self, title, message, notification_type="info", duration=None):
        """Show a notification."""
        if not self._parent:
            return

        config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["info"])
        if duration is None:
            duration = config["duration"]

        notification = NotificationWidget(title, message, notification_type, self._parent)
        notification.dismiss_requested.connect(lambda: self._dismiss_notification(notification))

        self._position_notification(notification)
        self._notifications.append(notification)
        notification.show()

        if duration > 0:
            QTimer.singleShot(duration, lambda: self._dismiss_notification(notification))

        return notification

    def _position_notification(self, notification):
        """Position a notification widget."""
        if not self._parent:
            return

        parent_rect = self._parent.rect()
        x = parent_rect.right() - notification.width() - self._margin_right
        y = parent_rect.bottom() - self._margin_bottom

        for current_notification in self._notifications:
            if current_notification.isVisible():
                y -= current_notification.height() + self._spacing

        if len(self._notifications) >= self._max_notifications:
            oldest = self._notifications[0]
            self._dismiss_notification(oldest)

        notification.move(x, y)

    def _dismiss_notification(self, notification):
        """Dismiss a notification with animation."""
        if notification in self._notifications:
            notification.fade_out()
            self._notifications.remove(notification)
            self._reposition_all()

    def _reposition_all(self):
        """Reposition all visible notifications."""
        if not self._parent:
            return

        parent_rect = self._parent.rect()
        y = parent_rect.bottom() - self._margin_bottom

        for notification in reversed(self._notifications):
            if notification.isVisible():
                x = parent_rect.right() - notification.width() - self._margin_right
                notification.move(x, y - notification.height())
                y -= notification.height() + self._spacing
