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
        }}
    """


def build_status_run_label_style() -> str:
    """Return the highlighted run label style."""
    return "color: #0f5fa8; font-weight: 600;"


def build_status_stats_label_style() -> str:
    """Return the task statistics label style."""
    return "color: #314154; font-weight: 500;"


def build_status_theme_label_style() -> str:
    """Return the theme label style."""
    return "color: #666666;"


def build_status_separator_style() -> str:
    """Return the separator frame style."""
    return "color: #e0e0e0;"


def build_status_badge_style(background_color: str, text_color: str) -> str:
    """Return the badge style for one status count pill."""
    return (
        f"QLabel {{ background-color: {background_color}; color: {text_color}; "
        "border-radius: 4px; padding: 0px 6px; }"
    )
