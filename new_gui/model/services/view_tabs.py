"""Helpers for tab label/button presentation states."""

from typing import Dict


MAIN_RUN_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 700; color: #1976d2; font-size: 13px; background: transparent;"
)
FILTERED_MAIN_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 600; color: #334455; font-size: 13px; background: transparent;"
)
ALL_STATUS_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 700; color: #1976d2; font-size: 13px; background: transparent;"
)
TRACE_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 700; color: #d32f2f; font-size: 13px; background: transparent;"
)
CATEGORY_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 700; color: #1f5e97; font-size: 13px; background: transparent;"
)
GRAPH_TAB_STYLE = (
    "border: none; border-radius: 10px; padding: 1px 6px; "
    "font-weight: 700; color: #1f6fb2; font-size: 13px; background: transparent;"
)

TabState = Dict[str, object]


def get_main_run_tab_state() -> TabState:
    """Return the default tab state for the normal single-run view."""
    return {
        "text": "TreeView",
        "style": MAIN_RUN_TAB_STYLE,
        "show_close_button": False,
    }


def get_filtered_main_tab_state() -> TabState:
    """Return the tab state after leaving an in-place filtered view."""
    return {
        "text": "TreeView",
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


def get_category_tab_state(scope: str, category_label: str) -> TabState:
    """Return the tab state for a sidebar category scoped view."""
    normalized_scope = (scope or "stage").strip().upper()
    normalized_label = (category_label or "").strip() or "Unknown"
    return {
        "text": f"Category: {normalized_scope} / {normalized_label}",
        "style": CATEGORY_TAB_STYLE,
        "show_close_button": True,
    }


def get_graph_tab_state() -> TabState:
    """Return the tab state while dependency graph mode is active."""
    return {
        "text": "Dependency Graph",
        "style": GRAPH_TAB_STYLE,
        "show_close_button": False,
    }
