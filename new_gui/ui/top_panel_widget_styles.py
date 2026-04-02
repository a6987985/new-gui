"""Shared stylesheet builders for top-panel widgets beyond the action buttons."""


def build_run_selector_style() -> str:
    """Return the run-selector combobox stylesheet used in the top panel."""
    return """
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #a0a0a0;
            border-radius: 6px;
            padding: 6px 12px;
            padding-right: 52px;
            color: #000000;
            font-size: 14px;
            min-width: 200px;
        }
        QComboBox:hover {
            border: 1px solid #808080;
            background-color: #f5f5f5;
        }
        QComboBox:focus {
            border: 1px solid #808080;
        }
        QComboBox:disabled {
            background-color: #EEF1F4;
            border: 1px solid #9BA5B7;
            color: #9BA5B7;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
            subcontrol-origin: padding;
            subcontrol-position: right center;
        }
        QComboBox:on {
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            border-bottom: none;
        }
        QComboBox QAbstractItemView {
            color: #000000;
            background-color: #ffffff;
            border: 1px solid #a0a0a0;
            border-top: none;
            selection-background-color: #EEF1F4;
            selection-color: #000000;
            outline: none;
            padding-left: 10px;
        }
        QComboBox QAbstractItemView::item {
            height: 28px;
        }
    """


def build_tab_close_button_style() -> str:
    """Return the close-button stylesheet for the main top tab widget."""
    return """
        QPushButton {
            border: none;
            border-radius: 10px;
            color: #999999;
            font-weight: bold;
            background: transparent;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #ef5350;
            color: white;
        }
    """
