"""Shared stylesheet builders for the bottom status bar."""


def build_status_bar_style(background_color: str, border_color: str, text_color: str) -> str:
    """Return the root frame style for the status bar."""
    return f"""
        StatusBar {{
            background-color: {background_color};
            border-top: 1px solid {border_color};
        }}
        QLabel {{
            color: {text_color};
            font-size: 12px;
            background: transparent;
        }}
    """


def build_status_run_label_style(accent_color: str = "#0f5fa8") -> str:
    """Return the highlighted run label style."""
    return f"color: {accent_color}; font-weight: 600;"


def build_status_stats_label_style(text_color: str = "#314154") -> str:
    """Return the task statistics label style."""
    return f"color: {text_color}; font-weight: 500;"


def build_status_separator_style(color: str = "#e0e0e0") -> str:
    """Return the separator frame style."""
    return f"color: {color}; background-color: {color}; max-width: 1px;"


def build_status_badge_style(background_color: str, text_color: str) -> str:
    """Return the badge style for one status count pill."""
    return f"""
        QFrame {{
            background-color: {background_color};
            border-radius: 9px;
        }}
        QFrame:hover {{
            background-color: {background_color};
        }}
        QLabel {{
            background: transparent;
            color: {text_color};
            font-weight: 600;
        }}
    """
