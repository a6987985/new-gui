"""Theme application helpers for MainWindow."""

import os

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QToolTip

from new_gui.config.settings import THEMES, logger
from new_gui.services import flow_background
from new_gui.ui import style_sheets
from new_gui.ui.dialogs.xmeta_background_dialog import XMetaBackgroundDialog


def apply_tooltip_theme(theme: dict) -> None:
    """Apply a consistent tooltip palette and stylesheet for the active theme."""
    app = QApplication.instance()
    if app is None:
        return

    app.setStyleSheet(
        style_sheets.build_tooltip_style(
            theme["menu_bg"],
            theme["text_color"],
            theme["border_color"],
            theme["accent_color"],
        )
    )

    tooltip_bg = QColor(theme["menu_bg"])
    tooltip_text = QColor(theme["text_color"])
    tooltip_palette = QPalette(QToolTip.palette())
    for color_group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        tooltip_palette.setColor(color_group, QPalette.ToolTipBase, tooltip_bg)
        tooltip_palette.setColor(color_group, QPalette.ToolTipText, tooltip_text)
        tooltip_palette.setColor(color_group, QPalette.Base, tooltip_bg)
        tooltip_palette.setColor(color_group, QPalette.Text, tooltip_text)
        tooltip_palette.setColor(color_group, QPalette.Window, tooltip_bg)
        tooltip_palette.setColor(color_group, QPalette.WindowText, tooltip_text)
    QToolTip.setPalette(tooltip_palette)


def get_xmeta_background_color(window):
    """Return the configured XMETA background color, if any."""
    bg_color = getattr(window, "_xmeta_background_color", None)
    if bg_color:
        return bg_color

    launch_color = getattr(window, "_launch_xmeta_background", None)
    resolved = flow_background.resolve_run_background(
        getattr(window, "combo_sel", None),
        fallback_color=launch_color,
    )
    window._xmeta_background_color = resolved
    return resolved or None


def toggle_theme(window) -> None:
    """Toggle between light and dark theme."""
    new_theme = window.theme_manager.toggle_theme()
    if new_theme:
        window.apply_theme(new_theme)


def apply_theme(window, theme_name, announce: bool = True) -> None:
    """Apply a theme to the application."""
    window.theme_manager.set_theme(theme_name)
    theme = window.theme_manager.get_theme()
    bg_color = window._get_xmeta_background_color()
    window_bg = bg_color or theme["window_bg"]
    window.window_bg = window_bg
    apply_tooltip_theme(theme)

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
    window._init_top_panel_background()

    if announce:
        theme_info = THEMES.get(theme_name, THEMES["light"])
        window.show_notification("Theme", f"Applied {theme_info['name']} theme", "info")


def refresh_xmeta_background(window, run_dir: str = None, announce: bool = False):
    """Reload the effective background from one run and re-apply the theme."""
    launch_color = getattr(window, "_launch_xmeta_background", None)
    resolved = flow_background.resolve_run_background(
        run_dir or getattr(window, "combo_sel", None),
        fallback_color=launch_color,
    )
    window._xmeta_background_color = resolved

    if resolved:
        os.environ["XMETA_BACKGROUND"] = resolved
    elif launch_color:
        os.environ["XMETA_BACKGROUND"] = launch_color
    else:
        os.environ.pop("XMETA_BACKGROUND", None)

    if hasattr(window, "_embedded_terminal"):
        window._embedded_terminal.set_terminal_background(resolved, restart_if_running=True)

    apply_theme(window, window.theme_manager.current_theme, announce=announce)
    return resolved


def open_xmeta_background_dialog(window) -> None:
    """Open the background editor and write the chosen color to every discovered run flow."""
    runs = flow_background.list_available_runs(window.run_base_dir)
    if not runs:
        window.show_notification("Background Color", "No runs were found in the current directory.", "warning")
        return

    dialog = XMetaBackgroundDialog(
        initial_color=window._get_xmeta_background_color() or "",
        run_count=len(runs),
        parent=window,
    )
    if dialog.exec_() != dialog.Accepted:
        return

    result = flow_background.apply_background_to_all_runs(window.run_base_dir, dialog.selected_color())
    failed_runs = result["failed_runs"]
    updated_runs = result["updated_runs"]
    updated_paths = result.get("updated_paths", [])

    if not updated_runs:
        detail = failed_runs[0][1] if failed_runs else "No runs were updated."
        window.show_notification("Background Color", detail, "error")
        return

    refresh_xmeta_background(window, run_dir=getattr(window, "combo_sel", None), announce=False)
    summary = (
        f"Applied {result['color']} to {len(updated_runs)}/{result['run_count']} runs"
        f" across {len(updated_paths)} flow cshrc file(s)."
    )
    if failed_runs:
        summary += f" Failed: {len(failed_runs)}."
        notification_type = "warning"
    else:
        notification_type = "success"

    window.show_notification("Background Color", summary, notification_type)
    if hasattr(window, "append_ui_log"):
        window.append_ui_log(
            "WARNING" if failed_runs else "INFO",
            "params",
            "Updated XMETA background across run flows.",
            details=summary,
        )


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
