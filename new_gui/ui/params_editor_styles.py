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
