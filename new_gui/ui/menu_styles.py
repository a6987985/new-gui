"""Shared stylesheet builders for lightweight popup menus."""


def build_popup_menu_style(
    *,
    selected_background: str,
    selected_text_color: str,
    item_text_color: str = "#000000",
    background_color: str = "#ffffff",
    border_color: str = "#cccccc",
    item_padding: str = "5px 20px",
) -> str:
    """Return a reusable popup-menu stylesheet."""
    return f"""
        QMenu {{
            background: {background_color};
            border: 1px solid {border_color};
            padding: 0px;
        }}
        QMenu::item {{
            padding: {item_padding};
            color: {item_text_color};
            border: none;
        }}
        QMenu::item:selected {{
            background-color: {selected_background};
            color: {selected_text_color};
        }}
    """
