"""Run discovery and all-status overview helpers."""

import os
import time
from typing import Dict, List

from new_gui.config.settings import logger


OverviewRow = Dict[str, str]


def _discover_runs(run_base_dir: str) -> List[str]:
    """Return sorted runs that contain a .target_dependency.csh file."""
    runs: List[str] = []
    if not run_base_dir or not os.path.exists(run_base_dir):
        return runs

    for item in os.listdir(run_base_dir):
        item_path = os.path.join(run_base_dir, item)
        dep_file = os.path.join(item_path, ".target_dependency.csh")
        if os.path.isdir(item_path) and os.path.exists(dep_file):
            runs.append(item)

    return sorted(runs)


def list_available_runs(run_base_dir: str) -> List[str]:
    """Return runs that contain a .target_dependency.csh file."""
    return _discover_runs(run_base_dir)


def scan_runs(run_base_dir: str) -> List[str]:
    """Scan the run base directory and return sorted valid run names."""
    if not os.path.exists(run_base_dir):
        return []

    logger.info(f"Scanning for runs in: {os.path.abspath(run_base_dir)}")
    try:
        runs = _discover_runs(run_base_dir)
    except Exception as exc:
        logger.error(f"Error scanning runs: {exc}")
        return []

    logger.info(f"Total runs found: {len(runs)}")
    return runs


def collect_all_status_overview(run_base_dir: str) -> List[OverviewRow]:
    """Collect latest status summary for each run."""
    overview_rows: List[OverviewRow] = []
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
