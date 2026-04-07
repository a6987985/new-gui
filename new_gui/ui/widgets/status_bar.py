from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from new_gui.config.settings import STATUS_CONFIG, THEMES
from new_gui.ui.status_bar_styles import (
    build_status_badge_style,
    build_status_bar_style,
    build_status_run_label_style,
    build_status_separator_style,
    build_status_stats_label_style,
    build_status_theme_label_style,
)
from new_gui.ui.widgets.labels import StatusBadgeLabel


class StatusBar(QFrame):
    """Custom status bar with task statistics and connection status"""
    status_filter_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the status bar UI"""
        self.setFixedHeight(34)
        self.setStyleSheet(build_status_bar_style("rgba(255, 255, 255, 0.95)", "#d8e2ec", "#526071"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Left side - Run info
        self._run_label = QLabel("Run: -")
        self._run_label.setStyleSheet(build_status_run_label_style())
        layout.addWidget(self._run_label)

        # Separator
        layout.addWidget(self._create_separator())

        # Task statistics
        self._stats_label = QLabel("Tasks: -")
        self._stats_label.setStyleSheet(build_status_stats_label_style())
        layout.addWidget(self._stats_label)

        # Separator
        layout.addWidget(self._create_separator())

        # Status breakdown badges
        self._status_breakdown_widget = QWidget()
        self._status_breakdown_layout = QHBoxLayout(self._status_breakdown_widget)
        self._status_breakdown_layout.setContentsMargins(0, 2, 0, 2)
        self._status_breakdown_layout.setSpacing(6)
        layout.addWidget(self._status_breakdown_widget)

        layout.addStretch()

        # Theme indicator
        self._theme_label = QLabel("☀ Light")
        self._theme_label.setStyleSheet(build_status_theme_label_style())
        layout.addWidget(self._theme_label)

    def _create_separator(self):
        """Create a vertical separator"""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(build_status_separator_style())
        return sep

    def update_run(self, run_name):
        """Update the current run name"""
        self._run_label.setText(f"Run: {run_name}")

    def update_stats(self, stats):
        """Update task statistics

        Args:
            stats: dict with keys: total, finish, running, failed, skip, scheduled, pending
        """
        total = stats.get("total", 0)
        self._stats_label.setText(f"Tasks: {total}")

        # Build status breakdown badges
        while self._status_breakdown_layout.count():
            item = self._status_breakdown_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for status in ["finish", "running", "failed", "skip", "scheduled", "pending"]:
            count = stats.get(status, 0)
            config = STATUS_CONFIG.get(status, {})
            icon = config.get("icon", "")
            bg_color = config.get("color", "#87CEEB")
            text_color = config.get("text_color", "#223041")
            badge = StatusBadgeLabel(status, f"{icon} {count}")
            badge.setFixedHeight(18)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(build_status_badge_style(bg_color, text_color))
            badge.statusDoubleClicked.connect(self.status_filter_requested.emit)
            self._status_breakdown_layout.addWidget(badge)

    def update_theme(self, theme_name):
        """Update theme indicator"""
        if theme_name == "dark":
            self._theme_label.setText("🌙 Dark")
        elif theme_name == "high_contrast":
            self._theme_label.setText("◐ High Contrast")
        else:
            self._theme_label.setText("☀ Light")

        theme = THEMES.get(theme_name, THEMES["light"])
        self.setStyleSheet(
            build_status_bar_style(
                theme["status_bar_bg"],
                theme["border_color"],
                theme["text_color"],
            )
        )


# ========== Params Table Model (Optimized for large datasets) ==========
