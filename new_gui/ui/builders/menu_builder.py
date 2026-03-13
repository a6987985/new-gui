"""Menu-bar builder helpers for MainWindow."""

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction


def init_menu_bar(window) -> None:
    """Initialize the menu bar."""
    window.menu_bar = window.menuBar()
    window._default_menu_bar_style = """
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 2px 8px;
            font-size: 13px;
            font-weight: bold;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 14px;
            border-radius: 4px;
            color: #333333;
        }
        QMenuBar::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        QMenuBar::item:pressed {
            background-color: #bbdefb;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 8px 24px;
            color: #333333;
        }
        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        QMenu::separator {
            height: 1px;
            background: #e0e0e0;
            margin: 4px 12px;
        }
    """
    window.menu_bar.setStyleSheet(window._default_menu_bar_style)

    status_menu = window.menu_bar.addMenu("Status")
    show_all_status_action = QAction("Show All Status", window)
    show_all_status_action.triggered.connect(window.show_all_status)
    status_menu.addAction(show_all_status_action)

    view_menu = window.menu_bar.addMenu("View")
    show_graph_action = QAction("Show Dependency Graph", window)
    show_graph_action.setShortcut(QKeySequence("Ctrl+G"))
    show_graph_action.triggered.connect(window.show_dependency_graph)
    view_menu.addAction(show_graph_action)

    view_menu.addSeparator()
    theme_menu = view_menu.addMenu("Theme")
    light_theme_action = QAction("Light Theme", window)
    light_theme_action.triggered.connect(lambda: window.apply_theme("light"))
    theme_menu.addAction(light_theme_action)
    dark_theme_action = QAction("Dark Theme", window)
    dark_theme_action.triggered.connect(lambda: window.apply_theme("dark"))
    theme_menu.addAction(dark_theme_action)
    high_contrast_action = QAction("High Contrast", window)
    high_contrast_action.triggered.connect(lambda: window.apply_theme("high_contrast"))
    theme_menu.addAction(high_contrast_action)

    tools_menu = window.menu_bar.addMenu("Tools")
    user_params_action = QAction("📝 User Params", window)
    user_params_action.setShortcut(QKeySequence("Ctrl+P"))
    user_params_action.setToolTip("Edit user.params for current run")
    user_params_action.triggered.connect(window.open_user_params)
    tools_menu.addAction(user_params_action)
    tile_params_action = QAction("📋 Tile Params", window)
    tile_params_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
    tile_params_action.setToolTip("View tile.params for current run")
    tile_params_action.triggered.connect(window.open_tile_params)
    tools_menu.addAction(tile_params_action)

    window.is_all_status_view = False
