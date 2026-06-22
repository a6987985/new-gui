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
