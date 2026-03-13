from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from new_gui.config.settings import STATUS_CONFIG, THEMES
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
        self.setStyleSheet("""
            StatusBar {
                background-color: rgba(255, 255, 255, 0.95);
                border-top: 1px solid #d8e2ec;
            }
            QLabel {
                color: #526071;
                font-size: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Left side - Run info
        self._run_label = QLabel("Run: -")
        self._run_label.setStyleSheet("color: #0f5fa8; font-weight: 600;")
        layout.addWidget(self._run_label)

        # Separator
        layout.addWidget(self._create_separator())

        # Task statistics
        self._stats_label = QLabel("Tasks: -")
        self._stats_label.setStyleSheet("color: #314154; font-weight: 500;")
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

        # Right side - Connection status
        self._connection_label = QLabel("● Connected")
        self._connection_label.setStyleSheet("color: #4caf50; font-weight: 500;")
        layout.addWidget(self._connection_label)

        # Theme indicator
        self._theme_label = QLabel("☀ Light")
        self._theme_label.setStyleSheet("color: #666666;")
        layout.addWidget(self._theme_label)

    def _create_separator(self):
        """Create a vertical separator"""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #e0e0e0;")
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
            badge.setStyleSheet(
                f"QLabel {{ background-color: {bg_color}; color: {text_color}; "
                "border-radius: 4px; padding: 0px 6px; }"
            )
            badge.statusDoubleClicked.connect(self.status_filter_requested.emit)
            self._status_breakdown_layout.addWidget(badge)

    def update_connection(self, connected):
        """Update connection status"""
        if connected:
            self._connection_label.setText("● Connected")
            self._connection_label.setStyleSheet("color: #28a745;")
        else:
            self._connection_label.setText("○ Disconnected")
            self._connection_label.setStyleSheet("color: #ef5350;")

    def update_theme(self, theme_name):
        """Update theme indicator"""
        if theme_name == "dark":
            self._theme_label.setText("🌙 Dark")
        elif theme_name == "high_contrast":
            self._theme_label.setText("◐ High Contrast")
        else:
            self._theme_label.setText("☀ Light")

        theme = THEMES.get(theme_name, THEMES["light"])
        self.setStyleSheet(f"""
            StatusBar {{
                background-color: {theme['status_bar_bg']};
                border-top: 1px solid {theme['border_color']};
            }}
            QLabel {{
                color: {theme['text_color']};
                font-size: 12px;
            }}
        """)


# ========== Params Table Model (Optimized for large datasets) ==========
