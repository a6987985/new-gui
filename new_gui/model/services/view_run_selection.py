"""Run-selector helpers shared by view controllers and bridge code."""

from __future__ import annotations

import os
from typing import List

MISSING_RUN_SUFFIX = " (missing)"


def combo_run_names(combo) -> List[str]:
    """Return all visible run names in the selector combo."""
    return [combo.itemText(index) for index in range(combo.count())]


def missing_run_label(run_name: str) -> str:
    """Return the combo-box placeholder label for one missing run."""
    normalized_run_name = str(run_name or "").strip()
    if not normalized_run_name:
        return ""
    if normalized_run_name.endswith(MISSING_RUN_SUFFIX):
        return normalized_run_name
    return f"{normalized_run_name}{MISSING_RUN_SUFFIX}"


def is_missing_run_label(run_name: str) -> bool:
    """Return whether one combo-box entry represents a missing run."""
    return str(run_name or "").strip().endswith(MISSING_RUN_SUFFIX)


def normalize_run_name(run_name: str) -> str:
    """Return the real run name behind one combo-box entry."""
    normalized_run_name = str(run_name or "").strip()
    if is_missing_run_label(normalized_run_name):
        return normalized_run_name[: -len(MISSING_RUN_SUFFIX)].rstrip()
    return normalized_run_name


def is_unavailable_run_entry(run_name: str) -> bool:
    """Return whether one combo-box entry should not activate a real run."""
    normalized_run_name = normalize_run_name(run_name)
    return not normalized_run_name or run_name == "No runs found" or is_missing_run_label(run_name)


def build_combo_run_entries(run_names, missing_run_name: str = "") -> List[str]:
    """Return the visible combo-box entries for valid and missing runs."""
    entries = list(run_names or [])
    normalized_missing_name = normalize_run_name(missing_run_name)
    if normalized_missing_name and normalized_missing_name not in entries:
        entries.insert(0, missing_run_label(normalized_missing_name))
    return entries


def set_combo_run_names(
    combo,
    run_names,
    selected_run_name: str = "",
    missing_run_name: str = "",
) -> str:
    """Replace combo items while preserving one preferred selection."""
    previous_state = combo.blockSignals(True)
    combo.clear()

    effective_selection = ""
    combo_entries = build_combo_run_entries(run_names, missing_run_name=missing_run_name)
    if combo_entries:
        combo.addItems(combo_entries)
        combo.setEnabled(bool(run_names))
        preferred_selection = missing_run_label(missing_run_name)
        if preferred_selection and preferred_selection in combo_entries:
            effective_selection = preferred_selection
        elif selected_run_name in combo_entries:
            effective_selection = selected_run_name
        else:
            effective_selection = combo_entries[0]
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
    normalized_run_name = normalize_run_name(run_name)
    if (
        getattr(window, "cached_targets_by_level", None)
        and getattr(window, "_cached_targets_run", "") == normalized_run_name
    ):
        return
    if is_unavailable_run_entry(run_name):
        return
    window.cached_targets_by_level = window.parse_dependency_file(normalized_run_name)
    window._cached_targets_run = normalized_run_name
    window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(normalized_run_name)
    window._cached_collapsible_target_groups_run = normalized_run_name


def has_cached_targets(window) -> bool:
    """Return whether cached grouped targets are available."""
    return bool(getattr(window, "cached_targets_by_level", None))
