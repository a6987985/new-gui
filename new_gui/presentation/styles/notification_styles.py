"""Shared stylesheet builders for notification widgets."""


DEFAULT_FRAME_BG = "#ffffff"
DEFAULT_FRAME_BORDER = "#e0e0e0"
DEFAULT_TITLE_COLOR = "#333333"
DEFAULT_MESSAGE_COLOR = "#666666"
DEFAULT_CLOSE_COLOR = "#999999"
DEFAULT_CLOSE_HOVER_COLOR = "#333333"


def build_notification_icon_style(color: str) -> str:
    """Return the icon label style for a notification."""
    return f"""
        font-size: 24px;
        color: {color};
        background: transparent;
    """


def build_notification_title_style(text_color: str = DEFAULT_TITLE_COLOR) -> str:
    """Return the title label style for a notification."""
    return f"""
        font-weight: 600;
        font-size: 13px;
        color: {text_color};
        background: transparent;
    """


def build_notification_message_style(text_color: str = DEFAULT_MESSAGE_COLOR) -> str:
    """Return the message label style for a notification."""
    return f"""
        font-size: 11px;
        color: {text_color};
        background: transparent;
    """


def build_notification_close_button_style(
    color: str = DEFAULT_CLOSE_COLOR,
    hover_color: str = DEFAULT_CLOSE_HOVER_COLOR,
) -> str:
    """Return the close button style for a notification."""
    return f"""
        QPushButton {{
            border: none;
            font-size: 16px;
            color: {color};
            background: transparent;
        }}
        QPushButton:hover {{
            color: {hover_color};
            background: transparent;
        }}
    """


def build_notification_frame_style(
    accent_color: str,
    background_color: str = DEFAULT_FRAME_BG,
    border_color: str = DEFAULT_FRAME_BORDER,
) -> str:
    """Return the frame style for a notification."""
    return f"""
        NotificationWidget {{
            background-color: {background_color};
            border: 1px solid {border_color};
            border-left: 4px solid {accent_color};
            border-radius: 8px;
        }}
    """


def build_notification_theme(theme: dict) -> dict:
    """Return color tokens used by notification widgets for the given theme.

    Args:
        theme: theme dict from shared.config.settings.THEMES[theme_name]

    Returns:
        dict of {"background", "border", "title", "message", "close",
        "close_hover"}
    """
    bg = theme.get("menu_bg", DEFAULT_FRAME_BG)
    border = theme.get("border_color", DEFAULT_FRAME_BORDER)
    title = theme.get("text_color", DEFAULT_TITLE_COLOR)
    muted = theme.get("muted_color") or theme.get("hint_color") or DEFAULT_MESSAGE_COLOR
    close_color = theme.get("muted_color") or DEFAULT_CLOSE_COLOR
    close_hover = theme.get("text_color") or DEFAULT_CLOSE_HOVER_COLOR
    return {
        "background": bg,
        "border": border,
        "title": title,
        "message": muted,
        "close": close_color,
        "close_hover": close_hover,
    }
