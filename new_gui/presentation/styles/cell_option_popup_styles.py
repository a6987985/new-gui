"""Styles for compact cell-anchored option popups."""


def build_cell_option_popup_style() -> str:
    """Return the shared popup and table stylesheet."""
    return """
        QDialog {
            background: #ffffff;
            border: 1px solid #cfd8e3;
            border-radius: 4px;
        }
        QTableWidget {
            background: #ffffff;
            border: none;
            gridline-color: transparent;
            outline: none;
            selection-background-color: #dfeefd;
            selection-color: #1f2937;
            color: #334155;
            font-size: 12px;
        }
        QTableWidget::item {
            padding: 4px 8px;
            border: none;
        }
        QTableWidget::item:hover {
            background: #eef5fc;
        }
    """


def _cell_option_palette(theme):
    """Palette for cell option popup themed builder."""
    t = theme or {}
    return {
        "bg": t.get("menu_bg", "#ffffff"),
        "text": t.get("text_color", "#334155"),
        "border": t.get("border_color", "#cfd8e3"),
        "selection_bg": t.get("selection_bg", "#dfeefd"),
        "hover": t.get("menu_hover", "#eef5fc"),
    }


def build_cell_option_popup_style_themed(theme) -> str:
    """Themed popup and table stylesheet."""
    p = _cell_option_palette(theme)
    return f"""
        QDialog {{
            background: {p['bg']};
            border: 1px solid {p['border']};
            border-radius: 4px;
        }}
        QTableWidget {{
            background: {p['bg']};
            border: none;
            gridline-color: transparent;
            outline: none;
            selection-background-color: {p['selection_bg']};
            selection-color: {p['text']};
            color: {p['text']};
            font-size: 12px;
        }}
        QTableWidget::item {{
            padding: 4px 8px;
            border: none;
        }}
        QTableWidget::item:hover {{
            background: {p['hover']};
        }}
    """


def _current_theme():
    from new_gui.presentation.theme.theme_runtime import ThemeManager
    return ThemeManager().get_theme()
