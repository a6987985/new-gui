"""Window-level UI builder helpers for MainWindow."""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from new_gui.config.settings import FADE_IN_DURATION_MS, WINDOW_HEIGHT, WINDOW_WIDTH
from new_gui.ui.builders import top_panel_builder


def init_window(window) -> None:
    """Initialize window properties and animation."""
    window.setWindowTitle("XMeta Console")
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.window_bg = window._get_xmeta_background_color() or "#f5f5f5"
    window_bg = window.window_bg

    window.setWindowOpacity(0.0)
    window.fade_anim = QPropertyAnimation(window, b"windowOpacity")
    window.fade_anim.setDuration(FADE_IN_DURATION_MS)
    window.fade_anim.setStartValue(0.0)
    window.fade_anim.setEndValue(1.0)
    window.fade_anim.setEasingCurve(QEasingCurve.InOutCubic)
    window.fade_anim.start()

    window.setStyleSheet(
        f"""
            QMainWindow {{
                background-color: {window_bg};
            }}
        """
    )


def init_central_widget(window) -> None:
    """Initialize the central widget and main layout."""
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    window._main_layout = QVBoxLayout(central_widget)
    window._main_layout.setContentsMargins(0, 0, 0, 0)
    window._main_layout.setSpacing(0)
    window._main_layout.setAlignment(Qt.AlignTop)


def position_top_action_buttons(window) -> None:
    """Float the top action buttons independently from the main row layout."""
    if not hasattr(window, "_top_button_container"):
        return

    container = window._top_button_container
    container.adjustSize()
    right_margin = 16
    x_pos = window.width() - right_margin - container.sizeHint().width()
    y_pos = top_panel_builder.get_top_button_anchor_y(window)
    container.move(max(0, x_pos), y_pos)
    container.raise_()
