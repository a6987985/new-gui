"""Shared style builders for visibility picker popups."""


def build_visibility_row_style(object_name: str) -> str:
    """Return the transparent row container style for a picker row."""
    return f"""
        QFrame#{object_name} {{
            background: transparent;
            border: none;
        }}
    """


def build_visibility_label_style() -> str:
    """Return the shared picker label text style."""
    return "color: #263238;"


def build_visibility_picker_style(object_name: str) -> str:
    """Return the popup style for a visibility picker frame."""
    return f"""
        QFrame#{object_name} {{
            background: #ffffff;
            border: 1px solid #d3d9e2;
            border-radius: 8px;
        }}
        QCheckBox {{
            color: #263238;
            spacing: 6px;
        }}
        QPushButton {{
            border: 1px solid #cfd8e3;
            border-radius: 6px;
            padding: 4px 10px;
            background: #ffffff;
            color: #314154;
        }}
        QPushButton:hover {{
            background: #f4f8fc;
        }}
    """


def _visibility_palette(theme):
    """Palette for visibility picker themed builders."""
    t = theme or {}
    return {
        "bg": t.get("menu_bg", "#ffffff"),
        "text": t.get("text_color", "#263238"),
        "border": t.get("border_color", "#d3d9e2"),
        "hover": t.get("menu_hover", "#f4f8fc"),
        "muted_border": t.get("border_color", "#cfd8e3"),
    }


def build_visibility_row_style_themed(object_name: str, theme) -> str:
    """Themed transparent row container style."""
    return f"""
        QFrame#{object_name} {{
            background: transparent;
            border: none;
        }}
    """


def build_visibility_label_style_themed(theme) -> str:
    """Themed picker label text style."""
    p = _visibility_palette(theme)
    return f"color: {p['text']};"


def build_visibility_picker_style_themed(object_name: str, theme) -> str:
    """Themed popup style for a visibility picker frame."""
    p = _visibility_palette(theme)
    return f"""
        QFrame#{object_name} {{
            background: {p['bg']};
            border: 1px solid {p['border']};
            border-radius: 8px;
        }}
        QCheckBox {{
            color: {p['text']};
            spacing: 6px;
        }}
        QPushButton {{
            color: {p['text']};
            border: 1px solid {p['muted_border']};
            border-radius: 6px;
            padding: 4px 10px;
            background: {p['bg']};
        }}
        QPushButton:hover {{
            background: {p['hover']};
        }}
    """


def _current_theme():
    from new_gui.presentation.theme.theme_runtime import ThemeManager
    return ThemeManager().get_theme()
