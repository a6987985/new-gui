"""Helpers for executing flow actions and preserving refresh behavior."""

import os
import shlex
import subprocess
from typing import Dict, List, Optional, Sequence

from new_gui.services.run_dependency import parse_dependency_file


SYNC_REFRESH_ACTIONS = {"XMeta_unskip", "XMeta_skip"}
LONG_RUNNING_ACTIONS = {"XMeta_run", "XMeta_run all"}
SYNC_ACTION_TIMEOUT_SECONDS = 30
ASYNC_ACTION_TIMEOUT_SECONDS = 300

ActionRequest = Dict[str, object]
ActionResult = Dict[str, object]


def _dedupe_targets_preserve_order(targets: Sequence[str]) -> List[str]:
    """Return unique targets while preserving the incoming order."""
    ordered_targets: List[str] = []
    seen_targets = set()
    for target_name in targets:
        normalized_target = str(target_name or "").strip()
        if not normalized_target or normalized_target in seen_targets:
            continue
        seen_targets.add(normalized_target)
        ordered_targets.append(normalized_target)
    return ordered_targets


def _order_run_targets(
    run_base_dir: str,
    current_run: str,
    selected_targets: Sequence[str],
) -> List[str]:
    """Return selected run targets in stable dependency-file order when available."""
    normalized_targets = _dedupe_targets_preserve_order(selected_targets)
    if not normalized_targets or not current_run:
        return normalized_targets

    targets_by_level = parse_dependency_file(run_base_dir, current_run)
    if not targets_by_level:
        return normalized_targets

    dependency_order: Dict[str, int] = {}
    ordered_index = 0
    for level_num in sorted(targets_by_level.keys()):
        for target_name in targets_by_level.get(level_num, []):
            if target_name in dependency_order:
                continue
            dependency_order[target_name] = ordered_index
            ordered_index += 1

    fallback_order = {target_name: index for index, target_name in enumerate(normalized_targets)}
    return sorted(
        normalized_targets,
        key=lambda target_name: (
            0 if target_name in dependency_order else 1,
            dependency_order.get(target_name, fallback_order[target_name]),
        ),
    )


def build_action_request(
    run_base_dir: str,
    current_run: str,
    action: str,
    selected_targets: Sequence[str],
) -> ActionRequest:
    """Build the execution request for a flow action."""
    run_dir = os.path.join(run_base_dir, current_run)
    argv: List[str] = shlex.split(action)
    action_targets = (
        _order_run_targets(run_base_dir, current_run, selected_targets)
        if action == "XMeta_run"
        else _dedupe_targets_preserve_order(selected_targets)
    )
    if action != "XMeta_run all":
        argv.extend(action_targets)

    command = f"cd {shlex.quote(run_dir)} && {shlex.join(argv)}"
    if action == "XMeta_run all":
        log_message = f"{current_run}, {action}."
    else:
        log_message = f"{current_run}, {action} {' '.join(action_targets)}."

    run_sync = action in SYNC_REFRESH_ACTIONS
    timeout: Optional[int]
    if action in LONG_RUNNING_ACTIONS:
        timeout = None
    else:
        timeout = SYNC_ACTION_TIMEOUT_SECONDS if run_sync else ASYNC_ACTION_TIMEOUT_SECONDS
    return {
        "command": command,
        "argv": argv,
        "cwd": run_dir,
        "log_message": log_message,
        "run_sync": run_sync,
        "timeout": timeout,
    }


def execute_shell_command(argv: Sequence[str], timeout: Optional[int], cwd: str) -> ActionResult:
    """Execute a command and return decoded output metadata."""
    process = subprocess.Popen(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
    )

    try:
        if timeout is None:
            stdout, stderr = process.communicate()
        else:
            stdout, stderr = process.communicate(timeout=timeout)
        return {
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "returncode": process.returncode,
            "timed_out": False,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "timed_out": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "timed_out": False,
            "error": exc,
        }
