"""Styles for the queue selection dialog."""


def build_queue_selection_dialog_style() -> str:
    """Return the base dialog stylesheet."""
    return """
        QDialog {
            background: #f7fafc;
            color: #334155;
        }
        QLabel#queueSelectionTitle {
            font-size: 16px;
            font-weight: 700;
            color: #1e293b;
        }
        QLabel#queueSelectionMeta,
        QLabel#queueSelectionHint {
            color: #475569;
            font-size: 12px;
        }
        QFrame#queueSelectionListFrame {
            border: 1px solid #d7e1eb;
            border-radius: 10px;
            background: #ffffff;
        }
        QRadioButton {
            spacing: 8px;
            padding: 6px 4px;
            color: #334155;
            font-size: 13px;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        QRadioButton::indicator:unchecked {
            border: 2px solid #94a3b8;
            border-radius: 8px;
            background: #ffffff;
        }
        QRadioButton::indicator:checked {
            border: 2px solid #1976d2;
            border-radius: 8px;
            background: #1976d2;
        }
        QPushButton#queueSelectionActionButton {
            background: #ffffff;
            border: 1px solid #cfd8e3;
            border-radius: 8px;
            padding: 7px 14px;
            color: #334155;
            font-weight: 600;
        }
        QPushButton#queueSelectionActionButton:hover {
            background: #f5f8fb;
            border-color: #9eb6d2;
        }
        QPushButton#queueSelectionPrimaryButton {
            background: #1976d2;
            border: 1px solid #1976d2;
            border-radius: 8px;
            padding: 7px 16px;
            color: #ffffff;
            font-weight: 700;
        }
        QPushButton#queueSelectionPrimaryButton:hover {
            background: #1565c0;
            border-color: #1565c0;
        }
    """
