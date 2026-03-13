"""Helpers for preserving and restoring search-driven tree state."""


def build_search_context(is_search_mode: bool, search_text: str, selected_targets=None) -> dict:
    """Capture the current search-related state."""
    return {
        "is_search_mode": bool(is_search_mode),
        "search_text": search_text or "",
        "selected_targets": list(selected_targets or []),
    }


def refresh_after_action(
    search_context: dict,
    current_run: str,
    build_status_cache,
    rebuild_main_tree,
    filter_tree,
) -> None:
    """Refresh the tree after an action and restore search filtering if needed."""
    if current_run and current_run != "No runs found":
        build_status_cache(current_run)

    rebuild_main_tree()

    if search_context.get("is_search_mode") and search_context.get("search_text"):
        filter_tree(search_context["search_text"])


def exit_search_mode(
    search_context: dict,
    clear_search_ui,
    rebuild_main_tree,
    select_targets_in_tree,
) -> list:
    """Exit search mode, rebuild the main tree, and restore selected targets."""
    selected_targets = list(search_context.get("selected_targets", []))
    if not search_context.get("is_search_mode"):
        return selected_targets

    clear_search_ui()
    rebuild_main_tree()

    if selected_targets:
        select_targets_in_tree(selected_targets)

    return selected_targets
