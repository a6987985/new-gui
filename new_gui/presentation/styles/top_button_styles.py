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


# ---------------------------------------------------------------------------
# Light-theme (hardcoded) builders – kept for backwards compatibility
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Theme-aware builders – return a dict keyed by style name
# ---------------------------------------------------------------------------

LIGHT_BUTTON_BG = "#ffffff"
DARK_BUTTON_BG = "#2d2d2d"
LIGHT_BORDER = "1px solid #cfd8e3"
DARK_BORDER = "1px solid #555555"
LIGHT_TEXT = "#314154"
DARK_TEXT = "#d0d0d0"
LIGHT_HOVER_BG = "#f7fbff"
DARK_HOVER_BG = "#3a4452"
LIGHT_HOVER_BORDER = "1px solid #7ba4d9"
DARK_HOVER_BORDER = "1px solid #6a8cb5"
LIGHT_HOVER_TEXT = "#0f5fa8"
DARK_HOVER_TEXT = "#7ab8f5"
LIGHT_PRESS_BG = "#e7f1fb"
DARK_PRESS_BG = "#4a5568"
LIGHT_PRESS_BORDER = "1px solid #5d8fcf"
DARK_PRESS_BORDER = "1px solid #5a7ca0"


def build_top_button_stylesheets(theme_name: str = "light") -> dict:
    """Return a dict mapping style keys to theme-aware stylesheets."""
    if theme_name == "dark":
        btn_bg = DARK_BUTTON_BG
        border = DARK_BORDER
        text = DARK_TEXT
        hover_bg = DARK_HOVER_BG
        hover_border = DARK_HOVER_BORDER
        hover_text = DARK_HOVER_TEXT
        press_bg = DARK_PRESS_BG
        press_border = DARK_PRESS_BORDER
    else:
        btn_bg = LIGHT_BUTTON_BG
        border = LIGHT_BORDER
        text = LIGHT_TEXT
        hover_bg = LIGHT_HOVER_BG
        hover_border = LIGHT_HOVER_BORDER
        hover_text = LIGHT_HOVER_TEXT
        press_bg = LIGHT_PRESS_BG
        press_border = LIGHT_PRESS_BORDER

    return {
        "neutral": _build_top_button_style(
            background_color=btn_bg,
            border=border,
            text_color=text,
            font_weight=500,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background=hover_bg,
            hover_border=hover_border,
            hover_text_color=hover_text,
            pressed_background=press_bg,
            pressed_border=press_border,
        ),
        "primary": _build_top_button_style(
            background_color=LIGHT_BUTTON_BG if theme_name != "dark" else DARK_BUTTON_BG,
            border="none",
            text_color="#ffffff",
            font_weight=600,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background="#1565c0",
            pressed_background="#0d47a1",
        ),
        "warning": _build_top_button_style(
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
        ),
        "secondary_compact": _build_top_button_style(
            background_color=btn_bg,
            border=border,
            text_color=text,
            font_weight=500,
            font_size=11,
            vertical_padding=4,
            horizontal_padding=8,
            hover_background=hover_bg,
            hover_border=hover_border,
            hover_text_color=hover_text,
            pressed_background=press_bg,
            pressed_border=press_border,
        ),
        "secondary_tight": _build_top_button_style(
            background_color=btn_bg,
            border=border,
            text_color=text,
            font_weight=500,
            font_size=11,
            vertical_padding=3,
            horizontal_padding=6,
            hover_background=hover_bg,
            hover_border=hover_border,
            hover_text_color=hover_text,
            pressed_background=press_bg,
            pressed_border=press_border,
        ),
    }


def build_theme_button_stylesheets(theme: dict) -> dict:
    """Return all five top-button stylesheets mapped to the given theme."""
    bg = theme.get("panel_bg", "#f8f9fa")
    text = theme.get("text_color", "#333333")
    accent = theme.get("accent_color", "#1976d2")
    border = theme.get("border_color", "#e0e0e0")
    menu_bg = theme.get("menu_bg", "#ffffff")
    hover = theme.get("menu_hover", "#e3f2fd")
    return {
        "neutral": _build_top_button_style(
            background_color=menu_bg,
            border=f"1px solid {border}",
            text_color=text,
            font_weight=500,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background=hover,
            hover_border=f"1px solid {accent}",
            hover_text_color=accent,
            pressed_background=hover,
            pressed_border=f"1px solid {accent}",
        ),
        "primary": _build_top_button_style(
            background_color=accent,
            border="none",
            text_color="#ffffff",
            font_weight=600,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background=accent,
            pressed_background=accent,
        ),
        "warning": _build_top_button_style(
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
        ),
        "secondary_compact": build_neutral_top_button_style(
            horizontal_padding=8, vertical_padding=4, font_size=11
        ),
        "secondary_tight": build_neutral_top_button_style(
            horizontal_padding=6, vertical_padding=3, font_size=11
        ),
    }


def build_theme_button_stylesheets(theme):
    """Return a dict of top-button style-sheets using theme colors."""
    menu_bg = theme.get("menu_bg", "#ffffff")
    border_color = theme.get("border_color", "#e0e0e0")
    text_color = theme.get("text_color", "#333333")
    accent = theme.get("accent_color", "#1976d2")
    hover_bg = theme.get("menu_hover", "#e3f2fd")
    panel_bg = theme.get("panel_bg", "#f8f9fa")

    def _neutral_style(h_pad=12, v_pad=6, f_size=12):
        return _build_top_button_style(
            background_color=menu_bg,
            border=f"1px solid {border_color}",
            text_color=text_color,
            font_weight=500,
            font_size=f_size,
            vertical_padding=v_pad,
            horizontal_padding=h_pad,
            hover_background=hover_bg,
            hover_border=f"1px solid {accent}",
            hover_text_color=accent,
            pressed_background=hover_bg,
            pressed_border=f"1px solid {accent}",
            pressed_text_color=accent,
        )

    return {
        "neutral": _neutral_style(),
        "primary": _build_top_button_style(
            background_color=accent,
            border="none",
            text_color=menu_bg,
            font_weight=600,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background=accent,
            pressed_background=accent,
        ),
        "warning": _build_top_button_style(
            background_color=panel_bg,
            border=f"1px solid {border_color}",
            text_color=text_color,
            font_weight=600,
            font_size=12,
            vertical_padding=6,
            horizontal_padding=12,
            hover_background=hover_bg,
            hover_border=f"1px solid {accent}",
            hover_text_color=accent,
            pressed_background=hover_bg,
            pressed_border=f"1px solid {accent}",
        ),
        "secondary_compact": _neutral_style(h_pad=8, v_pad=4, f_size=11),
        "secondary_tight": _neutral_style(h_pad=6, v_pad=3, f_size=11),
    }



def build_theme_button_stylesheets(theme: dict) -> dict:
    """Build all top-button stylesheets using theme colors.

    Args:
        theme: theme dict from shared.config.settings.THEMES[theme_name]

    Returns:
        dict of {"neutral": "...", "primary": "...", "warning": "...", etc.}
    """
    panel_bg = theme.get("panel_bg", "#f8f9fa")
    text = theme.get("text_color", "#333333")
    accent = theme.get("accent_color", "#1976d2")
    border = theme.get("border_color", "#e0e0e0")
    menu_bg = theme.get("menu_bg", "#ffffff")
    menu_hover = theme.get("menu_hover", "#e3f2fd")

    # Derive interactive colors from the theme
    # Darken accent for hover, darken further for pressed
    def _darken(hex_color, percent):
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return "#" + "".join(f"{max(0, int(c * (1 - percent))):02x}" for c in rgb)

    def _lighten(hex_color, percent):
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return "#" + "".join(f"{min(255, int(c + (255 - c) * percent)):02x}" for c in rgb)

    accent_hover = _darken(accent, 0.15)
    accent_pressed = _darken(accent, 0.30)
    border_hover = accent
    danger_light = theme.get("danger_color", "#b42318")
    danger_bg = _lighten(danger_light, 0.92)
    danger_border = _lighten(danger_light, 0.70)

    neutral = _build_top_button_style(
        background_color=menu_bg,
        border=f"1px solid {border}",
        text_color=text,
        font_weight=500,
        font_size=12,
        vertical_padding=6,
        horizontal_padding=12,
        hover_background=menu_hover,
        hover_border=f"1px solid {border_hover}",
        hover_text_color=accent,
        pressed_background=_lighten(accent, 0.88),
        pressed_border=f"1px solid {accent}",
        pressed_text_color=accent,
    )

    primary = _build_top_button_style(
        background_color=accent,
        border="none",
        text_color="#ffffff",
        font_weight=600,
        font_size=12,
        vertical_padding=6,
        horizontal_padding=12,
        hover_background=accent_hover,
        pressed_background=accent_pressed,
    )

    warning = _build_top_button_style(
        background_color=danger_bg,
        border=f"1px solid {danger_border}",
        text_color=danger_light,
        font_weight=600,
        font_size=12,
        vertical_padding=6,
        horizontal_padding=12,
        hover_background=_lighten(danger_light, 0.86),
        hover_border=f"1px solid {danger_light}",
        hover_text_color=danger_light,
        pressed_background=_lighten(danger_light, 0.78),
        pressed_border=f"1px solid {danger_light}",
        pressed_text_color=danger_light,
    )

    secondary_compact = _build_top_button_style(
        background_color=menu_bg,
        border=f"1px solid {border}",
        text_color=text,
        font_weight=500,
        font_size=11,
        vertical_padding=4,
        horizontal_padding=8,
        hover_background=menu_hover,
        hover_border=f"1px solid {border_hover}",
        hover_text_color=accent,
        pressed_background=_lighten(accent, 0.88),
        pressed_border=f"1px solid {accent}",
        pressed_text_color=accent,
    )

    secondary_tight = _build_top_button_style(
        background_color=menu_bg,
        border=f"1px solid {border}",
        text_color=text,
        font_weight=500,
        font_size=11,
        vertical_padding=3,
        horizontal_padding=6,
        hover_background=menu_hover,
        hover_border=f"1px solid {border_hover}",
        hover_text_color=accent,
        pressed_background=_lighten(accent, 0.88),
        pressed_border=f"1px solid {accent}",
        pressed_text_color=accent,
    )

    return {
        "neutral": neutral,
        "primary": primary,
        "warning": warning,
        "secondary_compact": secondary_compact,
        "secondary_tight": secondary_tight,
    }
