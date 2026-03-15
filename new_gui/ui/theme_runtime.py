import math

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtGui import QColor

from new_gui.config.settings import THEMES


class ThemeManager:
    """Manages application themes (Light/Dark/High Contrast)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_theme = "light"
        self._themes = THEMES
        self._listeners = []

    @property
    def current_theme(self):
        return self._current_theme

    def get_theme(self):
        """Get current theme configuration"""
        return self._themes.get(self._current_theme, self._themes["light"])

    def set_theme(self, theme_name):
        """Set theme and notify listeners"""
        if theme_name in self._themes:
            self._current_theme = theme_name
            for listener in self._listeners:
                listener(theme_name)
            return True
        return False

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        new_theme = "dark" if self._current_theme == "light" else "light"
        if self.set_theme(new_theme):
            return new_theme
        return None


# ========== Status Animator ==========
class StatusAnimator(QObject):
    """Manages status animation effects (pulse, shake, fade)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return
        super().__init__(parent)
        self._initialized = True
        self._pulse_phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animations)
        self._timer.start(50)  # 20 FPS for smooth animations

    def _update_animations(self):
        """Update all active animations"""
        self._pulse_phase = (self._pulse_phase + 0.1) % (2 * math.pi)

    def get_pulse_factor(self):
        """Get current pulse animation factor (0.0 to 1.0)"""
        return (math.sin(self._pulse_phase) + 1) / 2

    def get_animated_color(self, base_color, animation_type):
        """Get animated color for a given base color and animation type"""
        if animation_type == "pulse":
            # Pulse between base color and a lighter version
            factor = self.get_pulse_factor()
            color = QColor(base_color)
            lighter = color.lighter(130)
            return self._blend_colors(color, lighter, factor)
        return QColor(base_color)

    def _blend_colors(self, color1, color2, factor):
        """Blend two colors by factor (0.0 = color1, 1.0 = color2)"""
        r = int(color1.red() * (1 - factor) + color2.red() * factor)
        g = int(color1.green() * (1 - factor) + color2.green() * factor)
        b = int(color1.blue() * (1 - factor) + color2.blue() * factor)
        return QColor(r, g, b)


# ========== Notification Widget ==========
