"""Static top-button definitions and style policies."""

from new_gui.ui.top_button_styles import (
    build_neutral_top_button_style,
    build_primary_top_button_style,
    build_secondary_compact_top_button_style,
    build_secondary_tight_top_button_style,
    build_warning_top_button_style,
)


DEFAULT_TOP_BUTTON_IDS = (
    "run_all",
    "run",
    "stop",
    "skip",
    "unskip",
    "invalid",
)

TOP_BUTTON_DEFINITIONS = (
    {
        "id": "run_all",
        "label": "Run All",
        "style": "primary",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_run all"),
    },
    {
        "id": "run",
        "label": "Run",
        "style": "primary",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_run"),
    },
    {
        "id": "stop",
        "label": "Stop",
        "style": "warning",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_stop"),
    },
    {
        "id": "skip",
        "label": "Skip",
        "style": "warning",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_skip"),
    },
    {
        "id": "unskip",
        "label": "Unskip",
        "style": "neutral",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_unskip"),
    },
    {
        "id": "invalid",
        "label": "Invalid",
        "style": "warning",
        "preferred_row": 1,
        "callback": lambda window: window.start("XMeta_invalid"),
    },
    {
        "id": "term",
        "label": "Term",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.open_terminal(),
    },
    {
        "id": "csh",
        "label": "Csh",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.handle_csh(),
    },
    {
        "id": "log",
        "label": "Log",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.handle_log(),
    },
    {
        "id": "cmd",
        "label": "Cmd",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.handle_cmd(),
    },
    {
        "id": "trace_up",
        "label": "Trace Up",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.retrace_tab("in"),
    },
    {
        "id": "trace_down",
        "label": "Trace Down",
        "style": "neutral",
        "preferred_row": 2,
        "callback": lambda window: window.retrace_tab("out"),
    },
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
    return [(definition["id"], definition["label"]) for definition in TOP_BUTTON_DEFINITIONS]


def normalize_visible_top_buttons(button_ids):
    """Return a normalized set of visible top-button ids."""
    valid_ids = {definition["id"] for definition in TOP_BUTTON_DEFINITIONS}
    return {button_id for button_id in (button_ids or set()) if button_id in valid_ids}
