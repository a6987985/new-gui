"""Target status and time cache helpers."""

import os
import time
from typing import Dict, List, Optional, Tuple

from new_gui.config.settings import logger


StatusCache = Dict[str, object]
TargetTimeRange = Tuple[str, str]
TRACKER_TIME_OFFSET_SECONDS = 28800


def get_target_status(
    run_base_dir: str,
    run_name: str,
    target_name: str,
    status_cache: Optional[StatusCache] = None,
) -> str:
    """Return one target status using cache when available."""
    if status_cache and status_cache.get("run") == run_name:
        return status_cache.get("statuses", {}).get(target_name, "")

    run_dir = os.path.join(run_base_dir, run_name)
    status_dir = os.path.join(run_dir, "status")
    if not os.path.exists(status_dir):
        return ""

    possible_statuses = ["finish", "failed", "running", "skip", "scheduled", "pending"]
    found_statuses: List[str] = []
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


def build_status_cache(run_base_dir: str, run_name: str) -> StatusCache:
    """Build status and time caches for one run."""
    run_dir = os.path.join(run_base_dir, run_name)
    status_dir = os.path.join(run_dir, "status")
    tracker_dir = os.path.join(run_dir, "logs", "targettracker")

    statuses: Dict[str, str] = {}
    times: Dict[str, TargetTimeRange] = {}

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
                    st_mtime = time_data["start"] + TRACKER_TIME_OFFSET_SECONDS
                    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
                if "finished" in time_data:
                    ft_mtime = time_data["finished"] + TRACKER_TIME_OFFSET_SECONDS
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
    status_cache: Optional[StatusCache] = None,
) -> TargetTimeRange:
    """Return cached start and end time strings for one target."""
    if status_cache and status_cache.get("run") == run_name:
        return status_cache.get("times", {}).get(target_name, ("", ""))
    return ("", "")


def get_start_end_time(tgt_track_file: str) -> TargetTimeRange:
    """Return formatted start and end time from tracker files."""
    start_time = ""
    end_time = ""
    if os.path.exists(tgt_track_file + ".start"):
        st_mtime = os.path.getmtime(tgt_track_file + ".start") + TRACKER_TIME_OFFSET_SECONDS
        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
    if os.path.exists(tgt_track_file + ".finished"):
        ft_mtime = os.path.getmtime(tgt_track_file + ".finished") + TRACKER_TIME_OFFSET_SECONDS
        end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ft_mtime))
    return start_time, end_time
