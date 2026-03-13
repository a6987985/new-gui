"""Tune-file write helpers for MainWindow."""

import os
import shutil
from typing import Dict, List, Tuple

from new_gui.config.settings import logger


TuneFileEntry = Tuple[str, str]
CopyError = Tuple[str, str, str]
CopyResult = Dict[str, object]


def ensure_tune_file(tune_file: str) -> bool:
    """Ensure a tune file exists, creating parent directories as needed."""
    os.makedirs(os.path.dirname(tune_file), exist_ok=True)
    if os.path.exists(tune_file):
        return False

    with open(tune_file, "w", encoding="utf-8") as handle:
        handle.write("")
    return True


def copy_tune_files_to_runs(
    selected_tunes: List[TuneFileEntry],
    selected_runs: List[str],
    run_base_dir: str,
    target_name: str,
) -> CopyResult:
    """Copy selected tune files to selected runs and report results."""
    total_success = 0
    copied_paths: List[str] = []
    errors: List[CopyError] = []

    for suffix, source_tune in selected_tunes:
        for run in selected_runs:
            run_dir = os.path.join(run_base_dir, run) if run_base_dir else run
            dest_dir = os.path.join(run_dir, "tune", target_name)
            dest_tune = os.path.join(dest_dir, f"{target_name}.{suffix}.tcl")

            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(source_tune, dest_tune)
                copied_paths.append(dest_tune)
                total_success += 1
                logger.info(f"Copied tune to: {dest_tune}")
            except Exception as exc:
                logger.error(f"Failed to copy tune to {run}: {exc}")
                errors.append((run, suffix, str(exc)))

    return {
        "total_success": total_success,
        "total_attempts": len(selected_tunes) * len(selected_runs),
        "copied_paths": copied_paths,
        "errors": errors,
    }
