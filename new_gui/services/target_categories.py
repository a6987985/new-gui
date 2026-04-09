"""Helpers for loading sidebar categories from one shared target-stage file."""

from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Tuple


_CATEGORY_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_./-]+)\s+"([^"]*)"\s*$')
DEFAULT_TARGET_STAGE_SOURCE = "/home/jason.zhao/XMeta_console/target_stage.list"
DEFAULT_TARGET_STAGE_FILE_NAME = "target_stage.list"
_SHARED_TARGET_STAGE_DIR = os.path.join("..", "..", "XMeta", "util", "GUI")


def resolve_shared_target_stage_dir(execution_dir: str = None) -> str:
    """Return the shared GUI directory resolved from the current execution directory."""
    base_dir = os.path.abspath(execution_dir or os.getcwd())
    return os.path.abspath(os.path.join(base_dir, _SHARED_TARGET_STAGE_DIR))


def resolve_shared_target_stage_file(
    execution_dir: str = None,
    file_name: str = DEFAULT_TARGET_STAGE_FILE_NAME,
) -> str:
    """Return the shared target-stage file path under the GUI directory."""
    return os.path.join(resolve_shared_target_stage_dir(execution_dir), file_name)


def ensure_shared_target_stage_file(
    execution_dir: str = None,
    source_file: str = DEFAULT_TARGET_STAGE_SOURCE,
    file_name: str = DEFAULT_TARGET_STAGE_FILE_NAME,
) -> Tuple[str, bool, bool, str]:
    """Ensure the shared GUI directory and target-stage file exist."""
    gui_dir = resolve_shared_target_stage_dir(execution_dir)
    target_file = os.path.join(gui_dir, file_name)
    gui_dir_existed = os.path.isdir(gui_dir)
    created_gui_dir = False
    copied_target_file = False
    error_message = ""

    try:
        os.makedirs(gui_dir, exist_ok=True)
        created_gui_dir = not gui_dir_existed and os.path.isdir(gui_dir)
    except OSError as exc:
        return target_file, created_gui_dir, copied_target_file, str(exc)

    if not os.path.exists(target_file) and os.path.isfile(source_file):
        try:
            shutil.copy2(source_file, target_file)
            copied_target_file = True
        except OSError as exc:
            error_message = str(exc)

    return target_file, created_gui_dir, copied_target_file, error_message


def load_target_stage_categories(
    execution_dir: str = None,
    file_name: str = DEFAULT_TARGET_STAGE_FILE_NAME,
) -> Tuple[List[Dict[str, object]], str]:
    """Load category definitions from the shared target-stage file."""
    file_path = resolve_shared_target_stage_file(execution_dir, file_name=file_name)
    if not os.path.isfile(file_path):
        return [], file_path

    categories: List[Dict[str, object]] = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            match = _CATEGORY_LINE_RE.match(line)
            if not match:
                continue

            category_name = match.group(1).strip()
            target_blob = match.group(2).strip()
            targets = [token for token in target_blob.split() if token]
            if not category_name:
                continue

            categories.append(
                {
                    "id": category_name.lower(),
                    "label": category_name,
                    "targets": targets,
                }
            )

    return categories, file_path


def load_bb_tcl_categories(run_dir: str, file_name: str = "bb.tcl") -> Tuple[List[Dict[str, object]], str]:
    """Backward-compatible wrapper that now loads from the shared target-stage file."""
    del run_dir, file_name
    return load_target_stage_categories()
