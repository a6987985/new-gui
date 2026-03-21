"""Flow-backed XMETA background helpers."""

from __future__ import annotations

import glob
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from PyQt5.QtGui import QColor

from new_gui.config.settings import logger
from new_gui.services.run_catalog import list_available_runs


XMetaBackgroundPreset = Tuple[str, str]

PRESET_XMETA_BACKGROUND_COLORS: List[XMetaBackgroundPreset] = [
    ("Mist Red", "#c98e8a"),
    ("Clay Red", "#b97c78"),
    ("Sand Orange", "#c9a27c"),
    ("Warm Beige", "#cbb79e"),
    ("Sage Green", "#9fb59a"),
    ("Moss Green", "#8fa78b"),
    ("Seafoam", "#8fb8b2"),
    ("Dust Blue", "#8fafbe"),
    ("Slate Blue", "#869db4"),
    ("Lavender Gray", "#9a95b8"),
    ("Mauve", "#b08fa8"),
    ("Smoke Gray", "#8f949b"),
]

_BACKGROUND_PARAM_NAME = "XMETA_BACKGROUND"
_CSHRC_GLOB = os.path.join("..", "..", "flowsetup", "Meta_*_GUI.swd", "cshrc")
_SETENV_PATTERN = re.compile(r"^\s*setenv\s+XMETA_BACKGROUND\b")
_SET_PATTERN = re.compile(r"^\s*set\s+XMETA_BACKGROUND\b")
_EXPORT_PATTERN = re.compile(r"^\s*export\s+XMETA_BACKGROUND\b")


def normalize_background_color(value: str) -> Optional[str]:
    """Return one normalized hex color or None when the input is invalid."""
    color = QColor(str(value or "").strip())
    if not color.isValid():
        return None
    return color.name(QColor.HexRgb)


def choose_terminal_foreground(background_color: str) -> str:
    """Choose a readable terminal foreground for one background color."""
    normalized = normalize_background_color(background_color) or "#ffffff"
    color = QColor(normalized)
    luminance = (
        (0.2126 * color.redF())
        + (0.7152 * color.greenF())
        + (0.0722 * color.blueF())
    )
    return "#f8fafc" if luminance < 0.55 else "#111827"


def find_flow_cshrc_paths(run_dir: str) -> List[str]:
    """Return matching flowsetup cshrc paths for one run directory."""
    if not run_dir:
        return []

    pattern = os.path.normpath(os.path.join(run_dir, _CSHRC_GLOB))
    return sorted(
        {
            os.path.normpath(path)
            for path in glob.glob(pattern)
            if os.path.isfile(path)
        }
    )


def load_run_background(run_dir: str) -> Optional[str]:
    """Return XMETA_BACKGROUND from the matched flowsetup cshrc when available."""
    for cshrc_path in find_flow_cshrc_paths(run_dir):
        try:
            with open(cshrc_path, "r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    stripped = raw_line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    if not (
                        _SETENV_PATTERN.match(stripped)
                        or _SET_PATTERN.match(stripped)
                        or _EXPORT_PATTERN.match(stripped)
                    ):
                        continue

                    if "=" in stripped and stripped.startswith("export "):
                        value = stripped.split("=", 1)[1].strip().strip("\"'")
                    else:
                        tokens = stripped.split()
                        if len(tokens) >= 3 and tokens[0] == "setenv":
                            value = tokens[2].strip().strip("\"'")
                        elif len(tokens) >= 4 and tokens[0] == "set" and tokens[2] == "=":
                            value = " ".join(tokens[3:]).strip().strip("\"'")
                        else:
                            continue
                    return normalize_background_color(value)
        except Exception as exc:
            logger.warning(f"Failed to read XMETA background from {cshrc_path}: {exc}")
    return None


def resolve_run_background(run_dir: str, fallback_color: str = None) -> Optional[str]:
    """Return the run-backed background color or the provided fallback."""
    return load_run_background(run_dir) or normalize_background_color(fallback_color or "")


def save_run_background(run_dir: str, color: str) -> Tuple[bool, List[str]]:
    """Persist XMETA_BACKGROUND in every matched flowsetup cshrc for one run."""
    normalized = normalize_background_color(color)
    if not normalized or not run_dir or not os.path.isdir(run_dir):
        return False, []

    cshrc_paths = find_flow_cshrc_paths(run_dir)
    if not cshrc_paths:
        return False, []

    updated_paths: List[str] = []
    for cshrc_path in cshrc_paths:
        if _save_background_to_cshrc(cshrc_path, normalized):
            updated_paths.append(cshrc_path)
        else:
            return False, updated_paths
    return True, updated_paths


def _save_background_to_cshrc(cshrc_path: str, normalized_color: str) -> bool:
    """Update one flowsetup cshrc file with the provided XMETA background."""
    try:
        shutil.copy2(cshrc_path, f"{cshrc_path}.bak")
    except Exception as exc:
        logger.warning(f"Failed to back up {cshrc_path}: {exc}")

    try:
        with open(cshrc_path, "r", encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
    except Exception as exc:
        logger.error(f"Failed to read {cshrc_path}: {exc}")
        return False

    replacement = f'setenv {_BACKGROUND_PARAM_NAME} "{normalized_color}"\n'
    updated = False

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if (
            _SETENV_PATTERN.match(stripped)
            or _SET_PATTERN.match(stripped)
            or _EXPORT_PATTERN.match(stripped)
        ):
            lines[index] = replacement
            updated = True
            break

    if not updated:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(replacement)

    try:
        with open(cshrc_path, "w", encoding="utf-8") as handle:
            handle.writelines(lines)
        return True
    except Exception as exc:
        logger.error(f"Failed to write XMETA background to {cshrc_path}: {exc}")
        return False


def apply_background_to_all_runs(run_base_dir: str, color: str) -> Dict[str, object]:
    """Write XMETA_BACKGROUND to every discovered run flow cshrc under one base directory."""
    normalized = normalize_background_color(color)
    runs = list_available_runs(run_base_dir)
    updated_runs: List[str] = []
    failed_runs: List[Tuple[str, str]] = []
    updated_paths: List[str] = []
    processed_paths: Dict[str, bool] = {}

    if not normalized:
        return {
            "color": None,
            "run_count": len(runs),
            "updated_runs": updated_runs,
            "updated_paths": updated_paths,
            "failed_runs": [("*", "Invalid color value")],
        }

    for run_name in runs:
        run_dir = os.path.join(run_base_dir, run_name)
        matched_paths = find_flow_cshrc_paths(run_dir)
        if not matched_paths:
            failed_runs.append((run_name, "No matching ../../flowsetup/Meta_*_GUI.swd/cshrc"))
            continue

        run_success = True
        for cshrc_path in matched_paths:
            if cshrc_path not in processed_paths:
                processed_paths[cshrc_path] = _save_background_to_cshrc(cshrc_path, normalized)
            if not processed_paths[cshrc_path]:
                run_success = False

        if run_success:
            updated_runs.append(run_name)
        else:
            failed_runs.append((run_name, "Failed to write one or more flow cshrc files"))

    updated_paths = sorted(path for path, ok in processed_paths.items() if ok)

    return {
        "color": normalized,
        "run_count": len(runs),
        "updated_runs": updated_runs,
        "updated_paths": updated_paths,
        "failed_runs": failed_runs,
    }
