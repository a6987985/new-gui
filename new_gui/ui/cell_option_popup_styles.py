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
