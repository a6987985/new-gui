"""Tune-action workflow helpers used by action-controller dialogs."""

from __future__ import annotations

import os
from typing import Dict, List, Sequence, Tuple

from new_gui.services import tune_actions


TuneEntry = Tuple[str, str]


def validate_single_target_action(selected_targets: Sequence[str], run_dir: str, action_name: str) -> str:
    """Return a user-facing validation message for single-target tune actions."""
    if not run_dir:
        return f"Select exactly one target to {action_name}."
    if len(selected_targets) != 1:
        return f"Select exactly one target to {action_name}."
    return ""


def build_missing_tunesource_message(target_name: str) -> str:
    """Return message shown when a target has no tunesource entries."""
    return f"No tunesource entries found in cmds/{target_name}.cmd"


def build_missing_tune_message(target_name: str) -> str:
    """Return message shown when a target has no tune files."""
    return f"No tune file found for: {target_name}"


def apply_create_tune(tune_file: str) -> Dict[str, str]:
    """Create one tune file when missing and return normalized feedback."""
    created = tune_actions.ensure_tune_file(tune_file)
    tune_name = os.path.basename(tune_file)
    if created:
        return {
            "notification_type": "success",
            "message": f"Created tune file: {tune_name}",
        }
    return {
        "notification_type": "info",
        "message": f"Tune file already exists: {tune_name}",
    }


def resolve_current_run_name(run_dir: str) -> str:
    """Resolve run name from selected run directory or plain label."""
    if not run_dir:
        return ""
    return os.path.basename(run_dir) if os.path.isabs(run_dir) else run_dir


def build_no_other_runs_message() -> str:
    """Return message shown when no destination runs exist."""
    return "No other runs available"


def copy_tunes(
    selected_tunes: List[TuneEntry],
    selected_runs: List[str],
    run_base_dir: str,
    target_name: str,
) -> Dict[str, object]:
    """Copy selected tune files to selected runs via shared tune-actions service."""
    return tune_actions.copy_tune_files_to_runs(
        selected_tunes,
        selected_runs,
        run_base_dir,
        target_name,
    )


def build_copy_tune_summary(
    selected_tunes: List[TuneEntry],
    selected_runs: List[str],
    copy_result: Dict[str, object],
) -> str:
    """Return the copy-complete message for tune fanout operations."""
    total_success = int(copy_result.get("total_success", 0))
    tune_names = ", ".join([suffix for suffix, _ in selected_tunes])
    return (
        f"Copied {len(selected_tunes)} tune file(s) ({tune_names})\n"
        f"to {total_success}/{len(selected_runs)} runs"
    )
