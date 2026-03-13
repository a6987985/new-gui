"""Run-level file and cache helpers for MainWindow."""

import os
import re
import time
from typing import Dict, List, Tuple

from new_gui.config.settings import RE_ACTIVE_TARGETS, RE_DEPENDENCY_OUT, RE_LEVEL_LINE, logger


def build_run_target_cache_key(run_dir: str, target_name: str) -> tuple:
    """Build a stable cache key for per-target run data."""
    return (os.path.abspath(run_dir), target_name)


def invalidate_run_target_cache(
    cache: Dict[tuple, object],
    run_dir: str = None,
    target_name: str = None,
) -> None:
    """Invalidate cached run-target data in place."""
    if run_dir is None and target_name is None:
        cache.clear()
        return

    run_key = os.path.abspath(run_dir) if run_dir else None
    keys_to_remove = []
    for key_run, key_target in cache.keys():
        if run_key and key_run != run_key:
            continue
        if target_name and key_target != target_name:
            continue
        keys_to_remove.append((key_run, key_target))

    for key in keys_to_remove:
        cache.pop(key, None)


def parse_dependency_file(run_base_dir: str, run_name: str) -> Dict[int, List[str]]:
    """Parse .target_dependency.csh into a level-to-target mapping."""
    dependency_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    targets_by_level: Dict[int, List[str]] = {}

    if not os.path.exists(dependency_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return targets_by_level

    try:
        with open(dependency_file, "r") as handle:
            for line in handle:
                line = line.strip()
                match = RE_LEVEL_LINE.match(line)
                if match:
                    level_num = int(match.group(1))
                    targets = match.group(2).split()
                    targets_by_level[level_num] = targets
    except FileNotFoundError:
        logger.warning(f"Dependency file not found: {dependency_file}")
    except PermissionError as exc:
        logger.error(f"Permission denied reading dependency file: {exc}")
    except UnicodeDecodeError as exc:
        logger.error(f"Error decoding dependency file: {exc}")
    except Exception as exc:
        logger.error(f"Error parsing dependency file for {run_name}: {exc}")

    return targets_by_level


def get_tune_files(
    run_dir: str,
    target_name: str,
    tune_files_cache: Dict[tuple, List[Tuple[str, str]]],
) -> List[Tuple[str, str]]:
    """Return sorted tune files for one target, using the provided cache."""
    cache_key = build_run_target_cache_key(run_dir, target_name)
    cached = tune_files_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    tune_dir = os.path.join(run_dir, "tune", target_name)
    if not os.path.exists(tune_dir):
        tune_files_cache[cache_key] = []
        return []

    tune_files: List[Tuple[str, str]] = []
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


def get_tune_candidates_from_cmd(run_dir: str, target_name: str) -> List[Tuple[str, str]]:
    """Parse tunesource candidates from cmds/<target>.cmd."""
    cmd_file = os.path.join(run_dir, "cmds", f"{target_name}.cmd")
    if not os.path.exists(cmd_file):
        return []

    candidates: List[Tuple[str, str]] = []
    seen_paths = set()
    used_names = set()
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
    bsub_params_cache: Dict[tuple, Tuple[str, str, str]],
) -> Tuple[str, str, str]:
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


def list_available_runs(run_base_dir: str) -> List[str]:
    """Return runs that contain a .target_dependency.csh file."""
    available_runs = []
    if not run_base_dir or not os.path.exists(run_base_dir):
        return available_runs

    for item in os.listdir(run_base_dir):
        item_path = os.path.join(run_base_dir, item)
        dep_file = os.path.join(item_path, ".target_dependency.csh")
        if os.path.isdir(item_path) and os.path.exists(dep_file):
            available_runs.append(item)
    return available_runs


def scan_runs(run_base_dir: str) -> List[str]:
    """Scan the run base directory and return sorted valid run names."""
    runs = []
    if not os.path.exists(run_base_dir):
        return runs

    logger.info(f"Scanning for runs in: {os.path.abspath(run_base_dir)}")
    try:
        for item in os.listdir(run_base_dir):
            item_path = os.path.join(run_base_dir, item)
            if not os.path.isdir(item_path):
                continue
            dependency_file = os.path.join(item_path, ".target_dependency.csh")
            if os.path.exists(dependency_file):
                runs.append(item)
                logger.info(f"Found run: {item}")
    except Exception as exc:
        logger.error(f"Error scanning runs: {exc}")

    logger.info(f"Total runs found: {len(runs)}")
    return sorted(runs)


def get_target_status(
    run_base_dir: str,
    run_name: str,
    target_name: str,
    status_cache: Dict[str, object] = None,
) -> str:
    """Return one target status using cache when available."""
    if status_cache and status_cache.get("run") == run_name:
        return status_cache.get("statuses", {}).get(target_name, "")

    run_dir = os.path.join(run_base_dir, run_name)
    status_dir = os.path.join(run_dir, "status")
    if not os.path.exists(status_dir):
        return ""

    possible_statuses = ["finish", "failed", "running", "skip", "scheduled", "pending"]
    found_statuses = []
    for status in possible_statuses:
        status_file = os.path.join(status_dir, f"{target_name}.{status}")
        if os.path.exists(status_file):
            found_statuses.append(status)

    if not found_statuses:
        return ""
    if "skip" in found_statuses:
        return "skip"

    latest_status = None
    latest_time = 0
    for status in found_statuses:
        status_file = os.path.join(status_dir, f"{target_name}.{status}")
        mtime = os.path.getmtime(status_file)
        if mtime > latest_time:
            latest_time = mtime
            latest_status = status

    return latest_status if latest_status else ""


def build_status_cache(run_base_dir: str, run_name: str) -> Dict[str, object]:
    """Build status and time caches for one run."""
    run_dir = os.path.join(run_base_dir, run_name)
    status_dir = os.path.join(run_dir, "status")
    tracker_dir = os.path.join(run_dir, "logs", "targettracker")

    statuses: Dict[str, str] = {}
    times: Dict[str, Tuple[str, str]] = {}

    if os.path.exists(status_dir):
        try:
            status_files = os.listdir(status_dir)
            target_status_files: Dict[str, List[Tuple[str, float]]] = {}

            for filename in status_files:
                filepath = os.path.join(status_dir, filename)
                if not os.path.isfile(filepath):
                    continue

                parts = filename.rsplit(".", 1)
                if len(parts) == 2:
                    target_name, status = parts
                    if target_name not in target_status_files:
                        target_status_files[target_name] = []
                    try:
                        mtime = os.path.getmtime(filepath)
                        target_status_files[target_name].append((status, mtime))
                    except OSError:
                        pass

            for target_name, status_list in target_status_files.items():
                if not status_list:
                    continue
                status_names = [item[0] for item in status_list]
                if "skip" in status_names:
                    statuses[target_name] = "skip"
                else:
                    latest = max(status_list, key=lambda item: item[1])
                    statuses[target_name] = latest[0]
        except PermissionError as exc:
            logger.error(f"Permission denied accessing status directory: {exc}")
        except OSError as exc:
            logger.error(f"Error reading status directory: {exc}")
        except Exception as exc:
            logger.error(f"Error building status cache: {exc}")

    if os.path.exists(tracker_dir):
        try:
            tracker_files = os.listdir(tracker_dir)
            target_times: Dict[str, Dict[str, float]] = {}

            for filename in tracker_files:
                filepath = os.path.join(tracker_dir, filename)
                if not os.path.isfile(filepath):
                    continue

                if filename.endswith(".start"):
                    target_name = filename[:-6]
                    if target_name not in target_times:
                        target_times[target_name] = {}
                    try:
                        target_times[target_name]["start"] = os.path.getmtime(filepath)
                    except OSError:
                        pass
                elif filename.endswith(".finished"):
                    target_name = filename[:-9]
                    if target_name not in target_times:
                        target_times[target_name] = {}
                    try:
                        target_times[target_name]["finished"] = os.path.getmtime(filepath)
                    except OSError:
                        pass

            for target_name, time_data in target_times.items():
                start_time = ""
                end_time = ""
                if "start" in time_data:
                    st_mtime = time_data["start"] + 28800
                    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
                if "finished" in time_data:
                    ft_mtime = time_data["finished"] + 28800
                    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ft_mtime))
                times[target_name] = (start_time, end_time)
        except PermissionError as exc:
            logger.error(f"Permission denied accessing tracker directory: {exc}")
        except OSError as exc:
            logger.error(f"Error reading tracker directory: {exc}")
        except Exception as exc:
            logger.error(f"Error building time cache: {exc}")

    return {"run": run_name, "statuses": statuses, "times": times}


def get_target_times(
    run_name: str,
    target_name: str,
    status_cache: Dict[str, object] = None,
) -> Tuple[str, str]:
    """Return cached start and end time strings for one target."""
    if status_cache and status_cache.get("run") == run_name:
        return status_cache.get("times", {}).get(target_name, ("", ""))
    return ("", "")


def get_active_targets(run_dir: str) -> List[str]:
    """Parse ACTIVE_TARGETS from .target_dependency.csh."""
    if not run_dir:
        return []

    deps_file = os.path.join(run_dir, ".target_dependency.csh")
    if not os.path.exists(deps_file):
        return []

    try:
        with open(deps_file, "r") as handle:
            content = handle.read()
        match = RE_ACTIVE_TARGETS.search(content)
        if match:
            return match.group(1).split()
    except FileNotFoundError:
        logger.warning(f"Dependency file not found: {deps_file}")
    except PermissionError as exc:
        logger.error(f"Permission denied reading dependency file: {exc}")
    except UnicodeDecodeError as exc:
        logger.error(f"Error decoding dependency file: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error reading ACTIVE_TARGETS: {exc}")
    return []


def get_retrace_targets(run_dir: str, target: str, inout: str) -> List[str]:
    """Parse .target_dependency.csh to find related targets."""
    retrace_targets: List[str] = []
    if not run_dir:
        return retrace_targets

    dep_file = os.path.join(run_dir, ".target_dependency.csh")
    if not os.path.exists(dep_file):
        return retrace_targets

    try:
        with open(dep_file, "r") as handle:
            content = handle.read()

        if inout == "in":
            pattern = re.compile(rf'set\s+ALL_RELATED_{re.escape(target)}\s*=\s*"([^"]*)"')
        else:
            pattern = re.compile(rf'set\s+DEPENDENCY_OUT_{re.escape(target)}\s*=\s*"([^"]*)"')

        match = pattern.search(content)
        if match:
            retrace_targets = match.group(1).split()
    except Exception as exc:
        logger.error(f"Error parsing dependencies: {exc}")

    return retrace_targets


def get_start_end_time(tgt_track_file: str) -> Tuple[str, str]:
    """Return formatted start and end time from tracker files."""
    start_time = ""
    end_time = ""
    if os.path.exists(tgt_track_file + ".start"):
        st_mtime = os.path.getmtime(tgt_track_file + ".start") + 28800
        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
    if os.path.exists(tgt_track_file + ".finished"):
        ft_mtime = os.path.getmtime(tgt_track_file + ".finished") + 28800
        end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ft_mtime))
    return start_time, end_time


def collect_all_status_overview(run_base_dir: str) -> List[Dict[str, str]]:
    """Collect latest status summary for each run."""
    overview_rows: List[Dict[str, str]] = []
    for run_name in scan_runs(run_base_dir):
        run_dir = os.path.join(run_base_dir, run_name)
        status_dir = os.path.join(run_dir, "status")

        latest_target = ""
        latest_status = ""
        latest_timestamp = ""
        latest_mtime = 0

        if os.path.exists(status_dir):
            try:
                for status_file in os.listdir(status_dir):
                    file_path = os.path.join(status_dir, status_file)
                    if not os.path.isfile(file_path):
                        continue
                    mtime = os.path.getmtime(file_path)
                    if mtime <= latest_mtime:
                        continue

                    latest_mtime = mtime
                    parts = status_file.rsplit(".", 1)
                    if len(parts) == 2:
                        latest_target = parts[0]
                        latest_status = parts[1]
                    else:
                        latest_target = status_file
                        latest_status = ""
                    latest_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            except Exception as exc:
                logger.error(f"Error scanning status for {run_name}: {exc}")

        overview_rows.append(
            {
                "run_name": run_name,
                "latest_target": latest_target,
                "latest_status": latest_status,
                "latest_timestamp": latest_timestamp,
            }
        )

    return overview_rows


def build_dependency_graph(
    run_base_dir: str,
    run_name: str,
    status_cache: Dict[str, object] = None,
) -> Dict[str, object]:
    """Build dependency graph data from .target_dependency.csh."""
    graph_data: Dict[str, object] = {
        "nodes": [],
        "edges": [],
        "levels": {},
    }

    dep_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    if not os.path.exists(dep_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return graph_data

    try:
        targets_by_level = parse_dependency_file(run_base_dir, run_name)
        graph_data["levels"] = targets_by_level

        all_targets: List[str] = []
        for targets in targets_by_level.values():
            all_targets.extend(targets)

        effective_cache = status_cache
        if not effective_cache or effective_cache.get("run") != run_name:
            effective_cache = build_status_cache(run_base_dir, run_name)

        for target in all_targets:
            status = get_target_status(run_base_dir, run_name, target, effective_cache)
            graph_data["nodes"].append((target, status))

        with open(dep_file, "r") as handle:
            content = handle.read()

        all_targets_set = set(all_targets)
        for match in RE_DEPENDENCY_OUT.finditer(content):
            source = match.group(1)
            if source not in all_targets_set:
                continue
            downstream_targets = match.group(2).strip().split()
            for downstream in downstream_targets:
                if downstream in all_targets_set:
                    graph_data["edges"].append((source, downstream))
    except Exception as exc:
        logger.error(f"Error building dependency graph: {exc}")

    return graph_data
