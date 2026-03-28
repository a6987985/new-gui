"""Static top-button definitions and style policies."""

from new_gui.ui.top_button_styles import (
    build_neutral_top_button_style,
    build_primary_top_button_style,
    build_secondary_compact_top_button_style,
    build_secondary_tight_top_button_style,
    build_warning_top_button_style,
)
from new_gui.ui.action_registry import get_top_button_action_ids
from new_gui.ui.action_registry import get_top_button_choices as _registry_top_button_choices
from new_gui.ui.action_registry import get_top_button_definitions


DEFAULT_TOP_BUTTON_IDS = get_top_button_action_ids()

TOP_BUTTON_DEFINITIONS = tuple(
    {
        "id": definition.action_id,
        "label": definition.button_label,
        "style": definition.button_style,
        "preferred_row": definition.preferred_row,
        "callback": definition.trigger,
    }
    for definition in get_top_button_definitions()
)

TOP_BUTTON_STYLE_SHEETS = {
    "neutral": build_neutral_top_button_style(),
    "primary": build_primary_top_button_style(),
    "warning": build_warning_top_button_style(),
    "secondary_compact": build_secondary_compact_top_button_style(),
    "secondary_tight": build_secondary_tight_top_button_style(),
}

ROW1_BUTTON_SPACING = 8
ROW2_COMPACT_SPACING = 6
ROW2_TIGHT_SPACING = 4
ROW2_NEUTRAL_PADDING_CANDIDATES = (12, 11, 10, 9, 8, 7, 6, 5, 4)
TOP_BUTTON_MENU_ROW_Y_OFFSET = 10
TOP_BUTTON_PANEL_ROW_Y_OFFSET = 10


def get_top_button_choices():
    """Return top-button ids and labels in stable display order."""
    return _registry_top_button_choices()


def normalize_visible_top_buttons(button_ids):
    """Return a normalized set of visible top-button ids."""
    valid_ids = {definition["id"] for definition in TOP_BUTTON_DEFINITIONS}
    return {button_id for button_id in (button_ids or set()) if button_id in valid_ids}
