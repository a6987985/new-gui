"""Menu-bar builder helpers for MainWindow."""

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QWidgetAction

from new_gui.ui import style_sheets


def init_menu_bar(window) -> None:
    """Initialize the menu bar."""
    window.menu_bar = window.menuBar()
    window._default_menu_bar_style = style_sheets.build_default_menu_bar_style()
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

    setting_menu = window.menu_bar.addMenu("Setting")
    column_menu = setting_menu.addMenu("colomn")
    column_menu.aboutToShow.connect(window._prepare_column_visibility_menu)
    column_picker_action = QWidgetAction(window)
    column_picker_action.setDefaultWidget(window._get_or_create_column_visibility_picker())
    column_menu.addAction(column_picker_action)
    button_menu = setting_menu.addMenu("button")
    button_menu.aboutToShow.connect(window._prepare_button_visibility_menu)
    button_picker_action = QWidgetAction(window)
    button_picker_action.setDefaultWidget(window._get_or_create_button_visibility_picker())
    button_menu.addAction(button_picker_action)
    setting_menu.addSeparator()
    background_color_action = QAction("Background Color...", window)
    background_color_action.setToolTip("Apply a flow-backed XMETA background to all runs")
    background_color_action.triggered.connect(window.open_xmeta_background_dialog)
    setting_menu.addAction(background_color_action)
    window.setting_menu = setting_menu
    window.column_menu = column_menu
    window.button_menu = button_menu

    tools_menu = window.menu_bar.addMenu("Tools")
    external_terminal_action = QAction("External Terminal", window)
    external_terminal_action.setToolTip("Open the external terminal for the current run")
    external_terminal_action.triggered.connect(window.open_external_terminal)
    tools_menu.addAction(external_terminal_action)
    tools_menu.addSeparator()
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
    window._update_column_visibility_control_state()
