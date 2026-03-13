"""Theme application helpers for MainWindow."""

import os

from PyQt5.QtGui import QColor

from new_gui.config.settings import THEMES, logger


def get_xmeta_background_color(window):
    """Return the configured XMETA background color, if any."""
    bg_color = os.environ.get("XMETA_BACKGROUND", "").strip()
    return bg_color or None


def toggle_theme(window) -> None:
    """Toggle between light and dark theme."""
    new_theme = window.theme_manager.toggle_theme()
    window.apply_theme(new_theme)
    window.show_notification("Theme", f"Switched to {THEMES[new_theme]['name']} theme", "info")


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

            window.top_panel.setStyleSheet(f"#topPanel {{ background-color: {bg_color}; border: none; }}")
            if window.top_panel.graphicsEffect() is not None:
                window.top_panel.setGraphicsEffect(None)

            window.menu_bar.setStyleSheet(
                f"""
                    QMenuBar {{
                        background-color: {bg_color};
                        border: none;
                        padding: 4px 8px;
                        font-size: 13px;
                        font-weight: bold;
                    }}
                    QMenuBar::item {{
                        background-color: transparent;
                        padding: 6px 14px;
                        border-radius: 4px;
                        color: #333333;
                    }}
                    QMenuBar::item:selected {{
                        background-color: #e3f2fd;
                        color: #1976d2;
                    }}
                    QMenuBar::item:pressed {{
                        background-color: #bbdefb;
                    }}
                    QMenu {{
                        background-color: #ffffff;
                        border: 1px solid #e0e0e0;
                        border-radius: 6px;
                        padding: 4px 0px;
                    }}
                    QMenu::item {{
                        padding: 8px 24px;
                        color: #333333;
                    }}
                    QMenu::item:selected {{
                        background-color: #e3f2fd;
                        color: #1976d2;
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background: #e0e0e0;
                        margin: 4px 12px;
                    }}
                """
            )

            if hasattr(window, "tab_bar"):
                window.tab_bar.setStyleSheet(
                    f"""
                        #tabBar {{
                            background-color: {bg_color};
                            border: none;
                        }}
                    """
                )

            if hasattr(window, "tab_widget"):
                tab_widget_bg = QColor(bg_color).lighter(108).name()
                window.tab_widget.setStyleSheet(
                    f"""
                        #tabWidget {{
                            background-color: {tab_widget_bg};
                            border: none;
                            border-top-left-radius: 8px;
                            border-top-right-radius: 8px;
                        }}
                    """
                )

            if hasattr(window, "tree"):
                window.tree.setStyleSheet(
                    f"""
                        QTreeView {{
                            background: rgba(255, 255, 255, 0.9);
                            border: none;
                            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                            font-size: 10pt;
                            border-radius: 10px;
                            padding: 6px 4px 4px 4px;
                        }}
                        QTreeView::item {{
                            height: 17px;
                            padding: 5px 6px;
                            border: none;
                        }}
                        QTreeView:focus {{
                            outline: none;
                        }}
                        QHeaderView::section {{
                            background: rgba(250,250,250,0.95);
                            padding: 7px 12px;
                            border: none;
                            border-bottom: 1px solid rgba(148, 163, 184, 0.35);
                            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                            font-size: 10pt;
                            font-weight: 600;
                            color: {theme['text_color']};
                        }}
                        QTreeView::item:hover {{
                            background: transparent;
                        }}
                        QTreeView::item:selected {{
                            background: transparent;
                            color: #000000 !important;
                            outline: none;
                        }}
                        QTreeView::branch {{
                            background: transparent;
                            border: none;
                        }}
                        QTreeView::branch:has-siblings:!adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:has-siblings:adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:has-children:!has-siblings:closed {{
                            background: transparent;
                            image: none;
                        }}
                        QTreeView::branch:has-children:!has-siblings:open {{
                            background: transparent;
                            image: none;
                        }}
                        QTreeView::branch:has-children:has-siblings:closed {{
                            image: none;
                        }}
                        QTreeView::branch:has-children:has-siblings:open {{
                            image: none;
                        }}
                        QTreeView::branch:closed:has-children {{
                            border-image: none;
                        }}
                        QTreeView::branch:open:has-children {{
                            border-image: none;
                        }}
                        QTreeView::branch:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-siblings:!adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-siblings:adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:!has-children:!has-siblings:adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-children:!has-siblings:closed:selected,
                        QTreeView::branch:has-children:!has-siblings:open:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:hover {{
                            background: rgba(230,240,255,0.6) !important;
                        }}
                    """
                )

            if hasattr(window, "_status_bar"):
                window._status_bar.setStyleSheet(
                    f"""
                        StatusBar {{
                            background-color: {bg_color};
                            border-top: none;
                        }}
                        QLabel {{
                            color: {theme['text_color']};
                            font-size: 12px;
                        }}
                    """
                )

            logger.info(f"Applied XMETA background overrides: {bg_color}")
        else:
            window.top_panel.setStyleSheet(
                f"""
                    QWidget {{
                        background: {window._default_top_panel_bg};
                        border-radius: 0px;
                    }}
                """
            )
            window.menu_bar.setStyleSheet(window._default_menu_bar_style)
    except Exception as exc:
        logger.warning(f"Failed to get XMETA_BACKGROUND: {exc}")
