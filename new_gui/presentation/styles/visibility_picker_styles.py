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
