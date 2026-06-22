"""Shared style builders for floating top action buttons."""


def _build_top_button_style(
    *,
    background_color: str,
    border: str,
    text_color: str,
    font_weight: int,
    font_size: int,
    vertical_padding: int,
    horizontal_padding: int,
    hover_background: str,
    hover_border: str = None,
    hover_text_color: str = None,
    pressed_background: str = None,
    pressed_border: str = None,
    pressed_text_color: str = None,
) -> str:
    """Return a QPushButton stylesheet for one top-button visual variant."""
    hover_border = hover_border or border
    hover_text_color = hover_text_color or text_color
    pressed_background = pressed_background or hover_background
    pressed_border = pressed_border or hover_border
    pressed_text_color = pressed_text_color or hover_text_color

    return f"""
        QPushButton {{
            background-color: {background_color};
            border: {border};
            border-radius: 6px;
            padding: {vertical_padding}px {horizontal_padding}px;
            font-weight: {font_weight};
            font-size: {font_size}px;
            color: {text_color};
        }}
        QPushButton:hover {{
            background-color: {hover_background};
            border: {hover_border};
            color: {hover_text_color};
        }}
        QPushButton:pressed {{
            background-color: {pressed_background};
            border: {pressed_border};
            color: {pressed_text_color};
        }}
    """


def build_neutral_top_button_style(
    horizontal_padding: int = 12,
    vertical_padding: int = 6,
    font_size: int = 12,
) -> str:
    """Return the neutral top-button stylesheet."""
    return _build_top_button_style(
        background_color="#ffffff",
        border="1px solid #cfd8e3",
        text_color="#314154",
        font_weight=500,
        font_size=font_size,
        vertical_padding=vertical_padding,
        horizontal_padding=horizontal_padding,
        hover_background="#f7fbff",
        hover_border="1px solid #7ba4d9",
        hover_text_color="#0f5fa8",
        pressed_background="#e7f1fb",
        pressed_border="1px solid #5d8fcf",
    )


def build_primary_top_button_style() -> str:
    """Return the primary top-button stylesheet."""
    return _build_top_button_style(
        background_color="#1976d2",
        border="none",
        text_color="#ffffff",
        font_weight=600,
        font_size=12,
        vertical_padding=6,
        horizontal_padding=12,
        hover_background="#1565c0",
        pressed_background="#0d47a1",
    )


def build_warning_top_button_style() -> str:
    """Return the warning top-button stylesheet."""
    return _build_top_button_style(
        background_color="#fff8f8",
        border="1px solid #f3c5c5",
        text_color="#b42318",
        font_weight=600,
        font_size=12,
        vertical_padding=6,
        horizontal_padding=12,
        hover_background="#ffefef",
        hover_border="1px solid #e38b8b",
        pressed_background="#ffdede",
        pressed_border="1px solid #e38b8b",
    )


def build_secondary_compact_top_button_style() -> str:
    """Return the compact secondary top-button stylesheet."""
    return build_neutral_top_button_style(horizontal_padding=8, vertical_padding=4, font_size=11)


def build_secondary_tight_top_button_style() -> str:
    """Return the tight secondary top-button stylesheet."""
    return build_neutral_top_button_style(horizontal_padding=6, vertical_padding=3, font_size=11)
