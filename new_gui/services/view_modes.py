"""Helpers for classifying the active tree view mode."""


def get_active_view_mode(is_all_status_view: bool, tab_label_text: str) -> str:
    """Return the active view mode for the tree area."""
    if is_all_status_view:
        return "all_status"

    tab_text = (tab_label_text or "").strip()
    if tab_text.startswith("Status: "):
        return "status"
    if tab_text.startswith("Trace"):
        return "trace"
    return "main"
