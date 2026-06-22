"""Helpers for preserving and restoring search-driven tree state."""

from typing import Callable, Dict, List, Sequence


SearchContext = Dict[str, object]


def build_search_context(
    is_search_mode: bool,
    search_text: str,
    selected_targets: Sequence[str] = (),
    scroll_value: int = 0,
) -> SearchContext:
    """Capture the current search-related state."""
    return {
        "is_search_mode": bool(is_search_mode),
        "search_text": search_text or "",
        "selected_targets": list(selected_targets or []),
        "scroll_value": int(scroll_value or 0),
    }


def refresh_after_action(
    search_context: SearchContext,
    current_run: str,
    build_status_cache: Callable[[str], None],
    rebuild_main_tree: Callable[[], None],
    filter_tree: Callable[[str], None],
    set_scroll_value: Callable[[int], None],
    refresh_tree_rows_stable: Callable[[], bool] = None,
) -> None:
    """Refresh the tree after an action and restore search filtering if needed."""
    if current_run and current_run != "No runs found":
        build_status_cache(current_run)

    if refresh_tree_rows_stable is not None and refresh_tree_rows_stable():
        set_scroll_value(search_context.get("scroll_value", 0))
        return

    rebuild_main_tree()

    if search_context.get("is_search_mode") and search_context.get("search_text"):
        filter_tree(search_context["search_text"])

    set_scroll_value(search_context.get("scroll_value", 0))


def exit_search_mode(
    search_context: SearchContext,
    clear_search_ui: Callable[[], None],
    rebuild_main_tree: Callable[[], None],
    select_targets_in_tree: Callable[[List[str]], None],
) -> List[str]:
    """Exit search mode, rebuild the main tree, and restore selected targets."""
    selected_targets = list(search_context.get("selected_targets", []))
    if not search_context.get("is_search_mode"):
        return selected_targets

    clear_search_ui()
    rebuild_main_tree()

    if selected_targets:
        select_targets_in_tree(selected_targets)

    return selected_targets
