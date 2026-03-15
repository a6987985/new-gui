"""Helpers for executing flow actions and preserving refresh behavior."""

import os
import shlex
import subprocess
from typing import Dict, List, Sequence


SYNC_REFRESH_ACTIONS = {"XMeta_unskip", "XMeta_skip"}
SYNC_ACTION_TIMEOUT_SECONDS = 30
ASYNC_ACTION_TIMEOUT_SECONDS = 300

ActionRequest = Dict[str, object]
ActionResult = Dict[str, object]


def build_action_request(
    run_base_dir: str,
    current_run: str,
    action: str,
    selected_targets: Sequence[str],
) -> ActionRequest:
    """Build the execution request for a flow action."""
    run_dir = os.path.join(run_base_dir, current_run)
    argv: List[str] = shlex.split(action)
    if action != "XMeta_run all":
        argv.extend(selected_targets)

    command = f"cd {shlex.quote(run_dir)} && {shlex.join(argv)}"
    if action == "XMeta_run all":
        log_message = f"{current_run}, {action}."
    else:
        log_message = f"{current_run}, {action} {' '.join(selected_targets)}."

    run_sync = action in SYNC_REFRESH_ACTIONS
    return {
        "command": command,
        "argv": argv,
        "cwd": run_dir,
        "log_message": log_message,
        "run_sync": run_sync,
        "timeout": SYNC_ACTION_TIMEOUT_SECONDS if run_sync else ASYNC_ACTION_TIMEOUT_SECONDS,
    }


def execute_shell_command(argv: Sequence[str], timeout: int, cwd: str) -> ActionResult:
    """Execute a command and return decoded output metadata."""
    process = subprocess.Popen(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
    )

    try:
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
