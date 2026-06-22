"""Shared stylesheet builders for the params editor dialog."""


def build_params_editor_meta_label_style() -> str:
    """Return the muted metadata label style used by the params editor."""
    return "color: #666; font-size: 11px;"


def build_params_editor_primary_button_style() -> str:
    """Return the emphasized action button style for the params editor."""
    return """
        QPushButton {
            background-color: #4A90D9;
            color: white;
        }
        QPushButton:hover {
            background-color: #357ABD;
        }
    """


def build_params_editor_dialog_style() -> str:
    """Return the root stylesheet for the params editor dialog."""
    return """
        QDialog {
            background-color: white;
        }
        QTableView {
            border: 1px solid #ccc;
            border-radius: 4px;
            gridline-color: #e0e0e0;
        }
        QTableView::item {
            padding: 4px;
        }
        QTableView::item:selected {
            background-color: #e6f7ff;
        }
        QTableView::item:hover {
            background-color: #f5f5f5;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QLineEdit:focus {
            border: 1px solid #4A90D9;
        }
        QPushButton {
            padding: 6px 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background-color: #f5f5f5;
        }
        QPushButton:hover {
            background-color: #e6f7ff;
            border: 1px solid #4A90D9;
        }
        QPushButton:pressed {
            background-color: #cce5ff;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
    """


def _params_palette(theme):
    """Return a palette dict for params editor themed builders."""
    t = theme or {}
    return {
        "bg": t.get("menu_bg", "#ffffff"),
        "text": t.get("text_color", "#333333"),
        "muted": t.get("muted_color", "#666666"),
        "border": t.get("border_color", "#cccccc"),
        "grid": t.get("border_color", "#e0e0e0"),
        "accent": t.get("accent_color", "#4A90D9"),
        "hover": t.get("menu_hover", "#e3f2fd"),
        "selection": t.get("selection_bg", "#e6f7ff"),
        "panel_bg": t.get("panel_bg", "#f5f5f5"),
    }


def build_params_editor_meta_label_style_themed(theme) -> str:
    """Themed muted metadata label style."""
    p = _params_palette(theme)
    return f"color: {p['muted']}; font-size: 11px;"


def build_params_editor_primary_button_style_themed(theme) -> str:
    """Themed emphasized action button style."""
    p = _params_palette(theme)
    return f"""
        QPushButton {{
            background-color: {p['accent']};
            color: white;
            border: 1px solid {p['accent']};
            border-radius: 4px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {p['accent']};
            opacity: 0.9;
        }}
        QPushButton:disabled {{
            background-color: {p['panel_bg']};
            color: {p['muted']};
            border: 1px solid {p['border']};
        }}
    """


def build_params_editor_dialog_style_themed(theme) -> str:
    """Themed root stylesheet for the params editor dialog."""
    p = _params_palette(theme)
    return f"""
        QDialog {{
            background-color: {p['bg']};
            color: {p['text']};
        }}
        QLabel {{
            color: {p['text']};
        }}
        QTableView {{
            background-color: {p['bg']};
            color: {p['text']};
            border: 1px solid {p['border']};
            border-radius: 4px;
            gridline-color: {p['grid']};
        }}
        QTableView::item {{
            padding: 4px;
        }}
        QTableView::item:selected {{
            background-color: {p['selection']};
            color: {p['text']};
        }}
        QTableView::item:hover {{
            background-color: {p['hover']};
        }}
        QHeaderView::section {{
            background-color: {p['panel_bg']};
            color: {p['text']};
            border: 1px solid {p['border']};
            padding: 4px;
        }}
        QLineEdit {{
            background-color: {p['bg']};
            color: {p['text']};
            padding: 5px;
            border: 1px solid {p['border']};
            border-radius: 4px;
        }}
        QLineEdit:focus {{
            border: 1px solid {p['accent']};
        }}
        QPushButton {{
            color: {p['text']};
            padding: 6px 16px;
            border: 1px solid {p['border']};
            border-radius: 4px;
            background-color: {p['panel_bg']};
        }}
        QPushButton:hover {{
            background-color: {p['hover']};
            border: 1px solid {p['accent']};
        }}
        QPushButton:pressed {{
            background-color: {p['selection']};
        }}
        QGroupBox {{
            color: {p['text']};
            font-weight: bold;
            border: 1px solid {p['border']};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }}
    """


def _current_theme():
    from new_gui.presentation.theme.theme_runtime import ThemeManager
    return ThemeManager().get_theme()
