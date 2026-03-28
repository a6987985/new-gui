"""Service helpers for params editor file IO and command execution."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Dict

from new_gui.config.settings import RE_PARAM_LINE


_PARAM_NAME_RE = re.compile(r"^\w+$")
_PARAM_VALUE_UNQUOTED_RE = re.compile(r"^[\w\.\-]+$")


def load_params_file(params_file: str) -> Dict[str, str]:
    """Load and parse one params file into a key/value dictionary."""
    if not os.path.exists(params_file):
        raise FileNotFoundError(params_file)

    params_data: Dict[str, str] = {}
    with open(params_file, "r") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            match = RE_PARAM_LINE.match(line)
            if not match:
                continue

            param_name = match.group(1)
            value = match.group(2).strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            params_data[param_name] = value

    return params_data


def is_valid_param_name(param_name: str) -> bool:
    """Return whether the provided parameter name is valid."""
    return bool(_PARAM_NAME_RE.match(param_name or ""))


def save_params_file(params_file: str, params_type: str, params_data: Dict[str, str]) -> None:
    """Persist params data to file with backup and stable ordering."""
    if os.path.exists(params_file):
        shutil.copy2(params_file, params_file + ".bak")

    with open(params_file, "w") as handle:
        handle.write(f"# {params_type.title()} Parameters\n")
        handle.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for param_name, value in sorted(params_data.items()):
            normalized_value = str(value)
            if " " in normalized_value or not _PARAM_VALUE_UNQUOTED_RE.match(normalized_value):
                handle.write(f'{param_name} = "{normalized_value}"\n')
            else:
                handle.write(f"{param_name} = {normalized_value}\n")


def build_gen_params_command(run_dir: str) -> str:
    """Return a shell-display command for generating params in one run."""
    command = ["XMeta_gen_params"]
    return f"cd {shlex.quote(run_dir)} && {shlex.join(command)}"


def execute_gen_params(run_dir: str, timeout: int = 60) -> dict:
    """Execute XMeta_gen_params in one run directory and return structured results."""
    command = ["XMeta_gen_params"]
    result = {
        "command_display": build_gen_params_command(run_dir),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "error": "",
    }

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=run_dir,
        )
        stdout, stderr = process.communicate(timeout=timeout)
        result["returncode"] = process.returncode
        result["stdout"] = stdout.decode(errors="replace") if stdout else ""
        result["stderr"] = stderr.decode(errors="replace") if stderr else ""
        return result
    except subprocess.TimeoutExpired:
        process.kill()
        result["timed_out"] = True
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result
