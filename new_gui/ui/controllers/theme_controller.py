"""Theme application helpers for MainWindow."""

import os

from PyQt5.QtGui import QColor

from new_gui.config.settings import THEMES, logger
from new_gui.ui import style_sheets


def get_xmeta_background_color(window):
    """Return the configured XMETA background color, if any."""
    bg_color = os.environ.get("XMETA_BACKGROUND", "").strip()
    return bg_color or None


def toggle_theme(window) -> None:
    """Toggle between light and dark theme."""
    new_theme = window.theme_manager.toggle_theme()
    if new_theme:
        window.apply_theme(new_theme)


def apply_theme(window, theme_name) -> None:
    """Apply a theme to the application."""
    window.theme_manager.set_theme(theme_name)
    theme = window.theme_manager.get_theme()
    bg_color = window._get_xmeta_background_color()
    window_bg = bg_color or theme["window_bg"]

    if theme_name == "dark":
        scrollbar_bg = "#2d2d2d"
        scrollbar_handle = "#555555"
        scrollbar_handle_hover = "#666666"
        scrollbar_handle_pressed = "#444444"
    else:
        scrollbar_bg = "#f5f5f5"
        scrollbar_handle = "#c0c0c0"
        scrollbar_handle_hover = "#a0a0a0"
        scrollbar_handle_pressed = "#808080"

    if hasattr(window.tree, "_v_scrollbar"):
        window.tree._v_scrollbar.setColors(
            scrollbar_handle, scrollbar_handle_hover, scrollbar_handle_pressed, scrollbar_bg
        )
    if hasattr(window.tree, "_h_scrollbar"):
        window.tree._h_scrollbar.setColors(
            scrollbar_handle, scrollbar_handle_hover, scrollbar_handle_pressed, scrollbar_bg
        )

    window.setStyleSheet(
        f"""
            QMainWindow {{
                background: {window_bg};
            }}
            QTreeView {{
                background: {theme['tree_bg']};
                color: {theme['text_color']};
                border: none;
                border-radius: 10px;
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                padding: 6px 4px 4px 4px;
            }}
            QTreeView::item {{
                height: 17px;
                padding: 5px 6px;
                border: none;
            }}
            QTreeView::item:hover {{
                background: {theme['hover_bg']};
            }}
            QTreeView::item:selected {{
                background: {theme['selection_bg']};
                color: {theme['text_color']};
            }}
            QHeaderView::section {{
                background: {theme['panel_bg']};
                padding: 7px 12px;
                border: none;
                border-bottom: 1px solid {theme['border_color']};
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                font-weight: 600;
                color: {theme['text_color']};
            }}
            QMenuBar {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border-bottom: 1px solid {theme['border_color']};
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {theme['menu_hover']};
                color: #1976d2;
            }}
            QMenu {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 8px 24px;
            }}
            QMenu::item:selected {{
                background-color: {theme['menu_hover']};
                color: #1976d2;
            }}
            QComboBox {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QLineEdit {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QPushButton {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme['menu_hover']};
            }}
            QLabel {{
                color: {theme['text_color']};
            }}
        """
    )

    if hasattr(window, "_status_bar"):
        window._status_bar.update_theme(theme_name)
    if bg_color:
        window._init_top_panel_background()

    theme_info = THEMES.get(theme_name, THEMES["light"])
    window.show_notification("Theme", f"Applied {theme_info['name']} theme", "info")


def init_top_panel_background(window) -> None:
    """Apply XMETA background overrides to container widgets when configured."""
    try:
        bg_color = window._get_xmeta_background_color()

        if bg_color:
            theme = window.theme_manager.get_theme()

            if window.centralWidget() is not None:
                window.centralWidget().setStyleSheet(f"background-color: {bg_color};")

            window.top_panel.setStyleSheet(style_sheets.build_xmeta_top_panel_style(bg_color))
            if window.top_panel.graphicsEffect() is not None:
                window.top_panel.setGraphicsEffect(None)

            window.menu_bar.setStyleSheet(style_sheets.build_xmeta_menu_bar_style(bg_color))

            if hasattr(window, "tab_bar"):
                window.tab_bar.setStyleSheet(
                    style_sheets.build_tab_bar_style(
                        bg_color,
                        "border: none;",
                    )
                )

            if hasattr(window, "tab_widget"):
                tab_widget_bg = QColor(bg_color).lighter(108).name()
                window.tab_widget.setStyleSheet(
                    style_sheets.build_tab_widget_style(
                        tab_widget_bg,
                        "border: none;",
                        "",
                    )
                )

            if hasattr(window, "tree"):
                window.tree.setStyleSheet(style_sheets.build_xmeta_tree_style(theme["text_color"]))

            if hasattr(window, "_status_bar"):
                window._status_bar.setStyleSheet(
                    style_sheets.build_xmeta_status_bar_style(bg_color, theme["text_color"])
                )

            logger.info(f"Applied XMETA background overrides: {bg_color}")
        else:
            if hasattr(window, "_default_top_panel_style"):
                window.top_panel.setStyleSheet(window._default_top_panel_style)
            window.menu_bar.setStyleSheet(window._default_menu_bar_style)
            if hasattr(window, "_default_tab_bar_style"):
                window.tab_bar.setStyleSheet(window._default_tab_bar_style)
            if hasattr(window, "_default_tab_widget_style"):
                window.tab_widget.setStyleSheet(window._default_tab_widget_style)
            if hasattr(window, "_default_tree_style"):
                window.tree.setStyleSheet(window._default_tree_style)
    except Exception as exc:
        logger.warning(f"Failed to get XMETA_BACKGROUND: {exc}")
