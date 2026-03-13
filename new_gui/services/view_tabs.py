"""Helpers for tab label/button presentation states."""

from typing import Dict


MAIN_RUN_TAB_STYLE = "border: none; font-weight: 600; color: #1976d2; font-size: 13px; background: transparent;"
FILTERED_MAIN_TAB_STYLE = "border: none; font-weight: bold; color: #333; font-size: 13px; background: transparent;"
ALL_STATUS_TAB_STYLE = "border: none; font-weight: bold; color: #1976d2; font-size: 13px; background: transparent;"
TRACE_TAB_STYLE = "border: none; font-weight: bold; color: #d32f2f; font-size: 13px; background: transparent;"

TabState = Dict[str, object]


def get_main_run_tab_state() -> TabState:
    """Return the default tab state for the normal single-run view."""
    return {
        "text": "Main View",
        "style": MAIN_RUN_TAB_STYLE,
        "show_close_button": False,
    }


def get_filtered_main_tab_state() -> TabState:
    """Return the tab state after leaving an in-place filtered view."""
    return {
        "text": "Main View",
        "style": FILTERED_MAIN_TAB_STYLE,
        "show_close_button": False,
    }


def get_all_status_tab_state() -> TabState:
    """Return the tab state for the all-status overview."""
    return {
        "text": "All Status Overview",
        "style": ALL_STATUS_TAB_STYLE,
        "show_close_button": True,
    }


def get_status_tab_state(status: str) -> TabState:
    """Return the tab state for an in-place status filter."""
    return {
        "text": f"Status: {status}",
        "style": FILTERED_MAIN_TAB_STYLE,
        "show_close_button": True,
    }


def get_trace_tab_state(label_text: str) -> TabState:
    """Return the tab state for an in-place trace filter."""
    return {
        "text": label_text,
        "style": TRACE_TAB_STYLE,
        "show_close_button": True,
    }
