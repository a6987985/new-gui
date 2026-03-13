"""Tune-file and BSUB parameter helpers."""

import os
import re
from typing import Dict, List, Set, Tuple

from new_gui.config.settings import logger
from new_gui.services.run_cache import CacheKey, build_run_target_cache_key


TuneFileEntry = Tuple[str, str]
BsubParams = Tuple[str, str, str]


def get_tune_files(
    run_dir: str,
    target_name: str,
    tune_files_cache: Dict[CacheKey, List[TuneFileEntry]],
) -> List[TuneFileEntry]:
    """Return sorted tune files for one target, using the provided cache."""
    cache_key = build_run_target_cache_key(run_dir, target_name)
    cached = tune_files_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    tune_dir = os.path.join(run_dir, "tune", target_name)
    if not os.path.exists(tune_dir):
        tune_files_cache[cache_key] = []
        return []

    tune_files: List[TuneFileEntry] = []
    prefix = f"{target_name}."
    suffix = ".tcl"

    try:
        for filename in os.listdir(tune_dir):
            if not filename.startswith(prefix) or not filename.endswith(suffix):
                continue
            parts = filename.split(".")
            if len(parts) < 3:
                continue
            filepath = os.path.join(tune_dir, filename)
            tune_suffix = ".".join(parts[1:-1])
            tune_files.append((tune_suffix, filepath))
    except OSError as exc:
        logger.error(f"Error reading tune directory {tune_dir}: {exc}")

    tune_files = sorted(tune_files)
    tune_files_cache[cache_key] = tune_files
    return list(tune_files)


def get_tune_candidates_from_cmd(run_dir: str, target_name: str) -> List[TuneFileEntry]:
    """Parse tunesource candidates from cmds/<target>.cmd."""
    cmd_file = os.path.join(run_dir, "cmds", f"{target_name}.cmd")
    if not os.path.exists(cmd_file):
        return []

    candidates: List[TuneFileEntry] = []
    seen_paths: Set[str] = set()
    used_names: Set[str] = set()
    pattern = re.compile(
        r'^\s*tunesource\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))',
        re.IGNORECASE,
    )

    try:
        with open(cmd_file, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                match = pattern.match(line)
                if not match:
                    continue

                raw_path = next((group for group in match.groups() if group), "").strip()
                if not raw_path:
                    continue

                full_path = (
                    raw_path
                    if os.path.isabs(raw_path)
                    else os.path.normpath(os.path.join(run_dir, raw_path))
                )
                if not full_path.endswith(".tcl"):
                    continue

                normalized_path = os.path.normpath(full_path)
                if normalized_path in seen_paths:
                    continue

                display_name = os.path.basename(normalized_path) or raw_path
                if display_name in used_names:
                    if os.path.isabs(raw_path):
                        display_name = normalized_path
                    else:
                        display_name = raw_path

                candidates.append((display_name, normalized_path))
                seen_paths.add(normalized_path)
                used_names.add(display_name)
    except Exception as exc:
        logger.error(f"Failed to parse tunesource entries from {cmd_file}: {exc}")
        return []

    return sorted(candidates, key=lambda item: item[0].lower())


def get_bsub_params(
    run_dir: str,
    target_name: str,
    bsub_params_cache: Dict[CacheKey, BsubParams],
) -> BsubParams:
    """Return cached or parsed BSUB parameters for a target."""
    cache_key = build_run_target_cache_key(run_dir, target_name)
    cached = bsub_params_cache.get(cache_key)
    if cached is not None:
        return cached

    csh_file = os.path.join(run_dir, "make_targets", f"{target_name}.csh")
    if not os.path.exists(csh_file):
        value = ("N/A", "N/A", "N/A")
        bsub_params_cache[cache_key] = value
        return value

    try:
        with open(csh_file, "r") as handle:
            content = handle.read()

        queue_match = re.search(r"-q\s+(\S+)", content)
        queue = queue_match.group(1) if queue_match else "N/A"

        cores_match = re.search(r"-n\s+(\d+)", content)
        cores = cores_match.group(1) if cores_match else "N/A"

        mem_match = re.search(r"rusage\[mem=(\d+)\]", content)
        memory = mem_match.group(1) if mem_match else "N/A"

        value = (queue, cores, memory)
        bsub_params_cache[cache_key] = value
        return value
    except Exception as exc:
        logger.error(f"Error parsing bsub params for {target_name}: {exc}")
        value = ("N/A", "N/A", "N/A")
        bsub_params_cache[cache_key] = value
        return value


def save_bsub_param(run_dir: str, target_name: str, param_type: str, new_value: str) -> bool:
    """Persist one BSUB parameter change to disk."""
    csh_file = os.path.join(run_dir, "make_targets", f"{target_name}.csh")
    if not os.path.exists(csh_file):
        logger.warning(f"CSH file not found: {csh_file}")
        return False

    try:
        with open(csh_file, "r") as handle:
            content = handle.read()

        if param_type == "queue":
            if re.search(r"-q\s+\S+", content):
                content = re.sub(r"-q\s+\S+", f"-q {new_value}", content)
            else:
                logger.warning(f"No -q parameter found in {csh_file}")
                return False
        elif param_type == "cores":
            if re.search(r"-n\s+\d+", content):
                content = re.sub(r"-n\s+\d+", f"-n {new_value}", content)
            else:
                logger.warning(f"No -n parameter found in {csh_file}")
                return False
        elif param_type == "memory":
            if re.search(r"rusage\[mem=\d+\]", content):
                content = re.sub(r"rusage\[mem=\d+\]", f"rusage[mem={new_value}]", content)
            else:
                logger.warning(f"No rusage[mem=] parameter found in {csh_file}")
                return False

        with open(csh_file, "w") as handle:
            handle.write(content)
        return True
    except Exception as exc:
        logger.error(f"Error saving bsub param for {target_name}: {exc}")
        return False
