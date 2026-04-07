"""Short-lived visual freeze overlays used during layout transitions."""

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel, QWidget


class WidgetTransitionOverlayController:
    """Freeze one widget's current appearance until the next event-loop turn."""

    def __init__(self) -> None:
        self._overlay = None
        self._revision = 0

    def begin(self, target: QWidget) -> int:
        """Capture one widget snapshot and show it as a temporary overlay."""
        self._revision += 1
        revision = self._revision
        if target is None or not target.isVisible():
            return revision
        if target.width() <= 0 or target.height() <= 0:
            return revision

        self.clear_now()

        overlay = QLabel(target)
        overlay.setObjectName("transitionOverlay")
        overlay.setGeometry(target.rect())
        overlay.setPixmap(target.grab())
        overlay.setScaledContents(False)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.show()
        overlay.raise_()
        self._overlay = overlay
        return revision

    def schedule_clear(self, revision: int) -> None:
        """Clear the overlay on the next event-loop turn if the revision still matches."""
        QTimer.singleShot(0, lambda: self.clear_if_current(revision))

    def clear_if_current(self, revision: int) -> None:
        """Clear the overlay only when this revision is still the latest transition."""
        if revision != self._revision:
            return
        self.clear_now()

    def clear_now(self) -> None:
        """Drop the current overlay immediately."""
        if self._overlay is None:
            return
        overlay = self._overlay
        self._overlay = None
        overlay.deleteLater()

    def is_active(self) -> bool:
        """Return whether one overlay is currently visible."""
        return self._overlay is not None
