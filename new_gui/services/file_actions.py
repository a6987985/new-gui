"""File path and external action helpers for MainWindow."""

import os
import subprocess
import time
from typing import Optional, Tuple

from new_gui.config.settings import logger


def ensure_user_params_file(run_dir: str) -> Tuple[str, bool]:
    """Ensure user.params exists for a run and return its path plus creation flag."""
    user_params_file = os.path.join(run_dir, "user.params")
    if os.path.exists(user_params_file):
        return user_params_file, False

    with open(user_params_file, "w") as handle:
        handle.write("# User Parameters\n")
        handle.write(f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    return user_params_file, True


def get_tile_params_file(run_dir: str) -> Optional[str]:
    """Return tile.params path when it exists."""
    tile_params_file = os.path.join(run_dir, "tile.params")
    if os.path.exists(tile_params_file):
        return tile_params_file
    return None


def get_shell_file(run_dir: str, target: str) -> Optional[str]:
    """Return make_targets/<target>.csh path when it exists."""
    shell_file = os.path.join(run_dir, "make_targets", f"{target}.csh")
    if os.path.exists(shell_file):
        return shell_file
    return None


def get_log_file(run_dir: str, target: str) -> Optional[str]:
    """Return logs/<target>.log or .log.gz path when available."""
    log_file = os.path.join(run_dir, "logs", f"{target}.log")
    log_file_gz = f"{log_file}.gz"
    if os.path.exists(log_file):
        return log_file
    if os.path.exists(log_file_gz):
        return log_file_gz
    return None


def get_cmd_file(run_dir: str, target: str) -> Optional[str]:
    """Return cmds/<target>.cmd path when it exists."""
    cmd_file = os.path.join(run_dir, "cmds", f"{target}.cmd")
    if os.path.exists(cmd_file):
        return cmd_file
    return None


def open_file_with_editor(filepath: str, editor: str = "gvim", use_popen: bool = False) -> None:
    """Open a file with an external editor."""
    try:
        if use_popen:
            subprocess.Popen([editor, filepath])
        else:
            subprocess.run([editor, filepath], check=True, timeout=5)
    except subprocess.TimeoutExpired:
        pass
    except subprocess.CalledProcessError as exc:
        logger.error(f"{editor} returned error code {exc.returncode}")
    except FileNotFoundError:
        logger.error(f"{editor} not found in PATH")
    except Exception as exc:
        logger.error(f"Error opening file {filepath}: {exc}")


def open_terminal(run_dir: str, terminal_command: str = "XMeta_term") -> None:
    """Open a terminal command in the requested run directory."""
    original_dir = os.getcwd()
    try:
        os.chdir(run_dir)
        subprocess.run([terminal_command], check=False, timeout=5)
    except subprocess.TimeoutExpired:
        pass
    except FileNotFoundError:
        logger.error(f"{terminal_command} not found in PATH")
    except Exception as exc:
        logger.error(f"Error opening terminal: {exc}")
    finally:
        os.chdir(original_dir)
