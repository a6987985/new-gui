"""Helpers for classifying the active tree view mode."""

from new_gui.model.services import view_mode_state

ViewMode = str


def get_active_view_mode(window) -> ViewMode:
    """Return the effective visible mode for the tree area."""
    return view_mode_state.get_active_view_mode(window)
