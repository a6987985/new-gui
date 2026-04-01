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
