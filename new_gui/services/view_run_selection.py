"""Run-selector helpers shared by view controllers and bridge code."""

from __future__ import annotations

import os
from typing import List


def combo_run_names(combo) -> List[str]:
    """Return all visible run names in the selector combo."""
    return [combo.itemText(index) for index in range(combo.count())]


def set_combo_run_names(combo, run_names, selected_run_name: str = "") -> str:
    """Replace combo items while preserving one preferred selection."""
    previous_state = combo.blockSignals(True)
    combo.clear()

    effective_selection = ""
    if run_names:
        combo.addItems(run_names)
        combo.setEnabled(True)
        effective_selection = selected_run_name if selected_run_name in run_names else run_names[0]
        combo.setCurrentIndex(combo.findText(effective_selection))
    else:
        combo.addItem("No runs found")
        combo.setEnabled(False)

    combo.blockSignals(previous_state)
    return effective_selection


def current_working_run_name() -> str:
    """Return the basename for the current process working directory."""
    return os.path.basename(os.getcwd())


def ensure_cached_targets(window, run_name: str) -> None:
    """Populate cached target metadata for one run if absent."""
    if getattr(window, "cached_targets_by_level", None):
        return
    if not run_name or run_name == "No runs found":
        return
    window.cached_targets_by_level = window.parse_dependency_file(run_name)
    window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(run_name)
    window._cached_collapsible_target_groups_run = run_name


def has_cached_targets(window) -> bool:
    """Return whether cached grouped targets are available."""
    return bool(getattr(window, "cached_targets_by_level", None))
