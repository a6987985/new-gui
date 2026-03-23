"""Tune-file and BSUB parameter helpers."""

import getpass
import glob
import os
import re
import shlex
import subprocess
from typing import Dict, List, Set, Tuple

from new_gui.config.settings import logger
from new_gui.services.flow_background import find_flow_cshrc_paths
from new_gui.services.run_catalog import list_available_runs
from new_gui.services.run_cache import CacheKey, build_run_target_cache_key


TuneFileEntry = Tuple[str, str]
BsubParams = Tuple[str, str, str]
QueueDiscoveryResult = Dict[str, object]
_QUEUE_PATTERN = re.compile(r"-q\s+(\S+)")
_EDITABLE_QUEUE_PREFIX = "pd_"


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


def discover_available_queues(
    run_dir: str,
    run_base_dir: str = "",
    current_queue: str = "",
) -> QueueDiscoveryResult:
    """Return queue choices for the current user, preferring live LSF discovery."""
    username = (getpass.getuser() or os.environ.get("USER") or "").strip()
    queues, error_message = _discover_lsf_queues(run_dir, username)
    source = "lsf"
    message = f"Showing editable '{_EDITABLE_QUEUE_PREFIX}' queues available to user '{username}'."

    if not queues:
        queues = _collect_project_seen_queues(run_base_dir or run_dir)
        source = "project"
        if error_message:
            message = (
                f"LSF lookup failed. Showing editable '{_EDITABLE_QUEUE_PREFIX}' queues already "
                f"used in this project. ({error_message})"
            )
        else:
            message = (
                f"No live LSF queues were returned. Showing editable "
                f"'{_EDITABLE_QUEUE_PREFIX}' queues already used in this project."
            )

    queues = [queue_name for queue_name in queues if is_editable_queue_name(queue_name)]

    normalized = []
    seen = set()
    fallback_current = [current_queue] if is_editable_queue_name(current_queue) else []
    for queue_name in queues + fallback_current:
        queue_name = str(queue_name or "").strip()
        if not queue_name or queue_name in seen:
            continue
        seen.add(queue_name)
        normalized.append(queue_name)

    return {
        "queues": normalized,
        "source": source,
        "message": message,
        "username": username,
        "error": error_message,
    }


def is_editable_queue_name(queue_name: str) -> bool:
    """Return whether the queue can be edited through the GUI picker."""
    return str(queue_name or "").strip().startswith(_EDITABLE_QUEUE_PREFIX)


def _discover_lsf_queues(run_dir: str, username: str) -> Tuple[List[str], str]:
    """Return live LSF queues visible to the provided user."""
    if not username:
        return [], "Unable to determine current user."

    try:
        result = _run_lsf_command(
            run_dir,
            ["bqueues", "-u", username, "-o", "queue_name status", "-noheader"],
        )
    except subprocess.TimeoutExpired:
        return [], "LSF queue lookup timed out."
    except OSError as exc:
        return [], str(exc)

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        return [], details

    queues: List[str] = []
    for raw_line in (result.stdout or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        queue_name = parts[0].strip()
        status = parts[1].strip().lower()
        if queue_name and status.startswith("open"):
            queues.append(queue_name)

    return sorted(set(queues)), ""


def _run_lsf_command(run_dir: str, argv: List[str]) -> subprocess.CompletedProcess:
    """Run one LSF command, sourcing the flow cshrc when available."""
    cshrc_paths = find_flow_cshrc_paths(run_dir)
    env = os.environ.copy()

    if cshrc_paths:
        cshrc_path = cshrc_paths[0]
        quoted_command = " ".join(shlex.quote(part) for part in argv)
        shell_command = f"source {shlex.quote(cshrc_path)} >& /dev/null; {quoted_command}"
        return subprocess.run(
            ["/bin/csh", "-fc", shell_command],
            capture_output=True,
            text=True,
            env=env,
            timeout=8,
        )

    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env=env,
        timeout=8,
    )


def _collect_project_seen_queues(base_path: str) -> List[str]:
    """Return queue names already referenced by make_targets csh files."""
    if not base_path:
        return []

    candidate_runs: List[str] = []
    if os.path.isdir(os.path.join(base_path, "make_targets")):
        candidate_runs.append(base_path)
    elif os.path.isdir(base_path):
        for run_name in list_available_runs(base_path):
            candidate_runs.append(os.path.join(base_path, run_name))

    queues = set()
    for run_dir in candidate_runs:
        pattern = os.path.join(run_dir, "make_targets", "*.csh")
        for csh_file in glob.glob(pattern):
            try:
                with open(csh_file, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
            except OSError:
                continue

            for match in _QUEUE_PATTERN.finditer(content):
                queue_name = match.group(1).strip()
                if is_editable_queue_name(queue_name):
                    queues.add(queue_name)

    return sorted(queues)
