"""Shared stylesheet builders for notification widgets."""


def build_notification_icon_style(color: str) -> str:
    """Return the icon label style for a notification."""
    return f"""
        font-size: 24px;
        color: {color};
    """


def build_notification_title_style() -> str:
    """Return the title label style for a notification."""
    return """
        font-weight: bold;
        font-size: 13px;
        color: #333333;
    """


def build_notification_message_style() -> str:
    """Return the message label style for a notification."""
    return """
        font-size: 11px;
        color: #666666;
    """


def build_notification_close_button_style() -> str:
    """Return the close button style for a notification."""
    return """
        QPushButton {
            border: none;
            font-size: 16px;
            color: #999999;
            background: transparent;
        }
        QPushButton:hover {
            color: #333333;
        }
    """


def build_notification_frame_style(accent_color: str) -> str:
    """Return the frame style for a notification."""
    return f"""
        NotificationWidget {{
            background-color: white;
            border: 1px solid #e0e0e0;
            border-left: 4px solid {accent_color};
            border-radius: 6px;
        }}
    """
