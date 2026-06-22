"""Shared stylesheet builders for item delegates."""


def build_tune_combo_editor_style() -> str:
    """Return the combo-editor stylesheet for the tune delegate."""
    return """
        QComboBox {
            border: 1px solid #545F71;
            border-radius: 4px;
            padding: 2px 5px;
            padding-right: 20px;
            background: #ffffff;
            color: #545F71;
        }
        QComboBox:hover {
            border: 1px solid #545F71;
            background: #f5f5f5;
        }
        QComboBox::drop-down {
            border: none;
            width: 18px;
            subcontrol-origin: padding;
            subcontrol-position: right center;
        }
        QComboBox QAbstractItemView {
            color: #545F71;
            background-color: #ffffff;
            border: 1px solid #545F71;
            selection-background-color: #EEF1F4;
            selection-color: #545F71;
        }
    """


def _tune_combo_palette(theme):
    """Palette for tune combo editor themed builder."""
    t = theme or {}
    return {
        "bg": t.get("menu_bg", "#ffffff"),
        "text": t.get("text_color", "#545F71"),
        "border": t.get("border_color", "#545F71"),
        "hover": t.get("menu_hover", "#f5f5f5"),
        "selection_bg": t.get("selection_bg", "#EEF1F4"),
    }


def build_tune_combo_editor_style_themed(theme) -> str:
    """Themed combo-editor stylesheet for the tune delegate."""
    p = _tune_combo_palette(theme)
    return f"""
        QComboBox {{
            border: 1px solid {p['border']};
            border-radius: 4px;
            padding: 2px 5px;
            padding-right: 20px;
            background: {p['bg']};
            color: {p['text']};
        }}
        QComboBox:hover {{
            border: 1px solid {p['border']};
            background: {p['hover']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 18px;
            subcontrol-origin: padding;
            subcontrol-position: right center;
        }}
        QComboBox QAbstractItemView {{
            color: {p['text']};
            background-color: {p['bg']};
            border: 1px solid {p['border']};
            selection-background-color: {p['selection_bg']};
            selection-color: {p['text']};
        }}
    """


def _current_theme():
    from new_gui.presentation.theme.theme_runtime import ThemeManager
    return ThemeManager().get_theme()
