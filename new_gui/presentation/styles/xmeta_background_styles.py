"""Styles for the flow-backed XMETA background dialog."""


def build_xmeta_background_dialog_style() -> str:
    """Return the base dialog stylesheet."""
    return """
        QDialog {
            background: #f7fafc;
            color: #334155;
        }
        QLabel#xmetaBackgroundTitle {
            font-size: 16px;
            font-weight: 700;
            color: #1e293b;
        }
        QLabel#xmetaBackgroundMeta,
        QLabel#xmetaBackgroundValue {
            color: #475569;
            font-size: 12px;
        }
        QPushButton#xmetaBackgroundActionButton {
            background: #ffffff;
            border: 1px solid #cfd8e3;
            border-radius: 8px;
            padding: 7px 14px;
            color: #334155;
            font-weight: 600;
        }
        QPushButton#xmetaBackgroundActionButton:hover {
            background: #f5f8fb;
            border-color: #9eb6d2;
        }
        QPushButton#xmetaBackgroundPrimaryButton {
            background: #1976d2;
            border: 1px solid #1976d2;
            border-radius: 8px;
            padding: 7px 16px;
            color: #ffffff;
            font-weight: 700;
        }
        QPushButton#xmetaBackgroundPrimaryButton:hover {
            background: #1565c0;
            border-color: #1565c0;
        }
        QFrame#xmetaBackgroundPreview {
            border: 1px solid #d7e1eb;
            border-radius: 10px;
            background: #ffffff;
        }
    """


def build_xmeta_background_swatch_style(color_hex: str, selected: bool = False) -> str:
    """Return one swatch style."""
    border_color = "#1d4ed8" if selected else "#ffffff"
    shadow_color = "#93c5fd" if selected else "#d7e1eb"
    return f"""
        QPushButton {{
            background: {color_hex};
            border: 2px solid {border_color};
            border-radius: 14px;
        }}
        QPushButton:hover {{
            border-color: {shadow_color};
        }}
    """


def build_xmeta_background_preview_fill_style(color_hex: str) -> str:
    """Return the live preview chip style."""
    return f"background: {color_hex}; border-radius: 10px; border: 1px solid rgba(15, 23, 42, 0.08);"
