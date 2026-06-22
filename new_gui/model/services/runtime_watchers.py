"""Runtime watcher setup and event handlers for MainWindow."""

import os

from new_gui.shared.config.settings import DEBOUNCE_DELAY_MS, logger

DEPENDENCY_FILE_NAME = ".target_dependency.csh"


def _status_directory_signature(status_dir: str) -> tuple:
    """Return a stable signature for files inside one status directory."""
    if not status_dir or not os.path.isdir(status_dir):
        return ()

    entries = []
    try:
        for entry_name in sorted(os.listdir(status_dir)):
            entry_path = os.path.join(status_dir, entry_name)
            if not os.path.isfile(entry_path):
                continue
            try:
                stat_result = os.stat(entry_path)
            except OSError:
                continue
            entries.append((entry_name, int(stat_result.st_mtime_ns), int(stat_result.st_size)))
    except OSError as exc:
        logger.error(f"Failed to poll status directory {status_dir}: {exc}")
    return tuple(entries)


def _start_debounce_timer(window) -> None:
    """Start the shared debounce timer when it is not already active."""
    if not window.debounce_timer.isActive():
        window.debounce_timer.start(DEBOUNCE_DELAY_MS)


def _dependency_file_signature(dependency_file: str) -> tuple:
    """Return a stable signature for the watched dependency file."""
    if not dependency_file or not os.path.isfile(dependency_file):
        return (False, 0, 0)

    stat_result = os.stat(dependency_file)
    return (True, int(stat_result.st_mtime_ns), int(stat_result.st_size))


def setup_status_watcher(window) -> None:
    """Setup file system watcher for the current run status directory."""
    if window.watched_status_dirs:
        window.status_watcher.removePaths(list(window.watched_status_dirs))
        window.watched_status_dirs.clear()
    if getattr(window, "watched_status_files", None):
        window.status_watcher.removePaths(list(window.watched_status_files))
        window.watched_status_files.clear()

    if not window.combo_sel:
        window._status_directory_signature = ()
        if hasattr(window, "_update_status_snapshot_timer_state"):
            window._update_status_snapshot_timer_state()
        return

    status_dir = os.path.join(window.combo_sel, "status")

    if os.path.exists(status_dir):
        window.status_watcher.addPath(status_dir)
        window.watched_status_dirs.add(status_dir)
        watched_status_files = []
        try:
            for entry_name in sorted(os.listdir(status_dir)):
                entry_path = os.path.join(status_dir, entry_name)
                if os.path.isfile(entry_path):
                    watched_status_files.append(entry_path)
        except OSError as exc:
            logger.error(f"Failed to enumerate status directory {status_dir}: {exc}")

        if watched_status_files:
            window.status_watcher.addPaths(watched_status_files)
            window.watched_status_files.update(watched_status_files)
        logger.debug(f"Now watching status directory: {status_dir}")
    window._status_directory_signature = _status_directory_signature(status_dir)
    if hasattr(window, "_update_status_snapshot_timer_state"):
        window._update_status_snapshot_timer_state()


def poll_status_directory_snapshot(window) -> None:
    """Detect missed status-file create/delete events and schedule a refresh."""
    if not getattr(window, "combo_sel", None):
        return

    status_dir = os.path.join(window.combo_sel, "status")
    previous_signature = getattr(window, "_status_directory_signature", ())
    current_signature = _status_directory_signature(status_dir)
    if current_signature == previous_signature:
        return

    window.setup_status_watcher()
    _start_debounce_timer(window)


def setup_dependency_watcher(window) -> None:
    """Setup file system watcher for the current run dependency file."""
    if not hasattr(window, "watched_dependency_dirs"):
        window.watched_dependency_dirs = set()
    if not hasattr(window, "watched_dependency_files"):
        window.watched_dependency_files = set()

    if getattr(window, "watched_dependency_dirs", None):
        old_dirs = list(window.watched_dependency_dirs)
        window.dependency_watcher.removePaths(old_dirs)
        window.watched_dependency_dirs.clear()
    if getattr(window, "watched_dependency_files", None):
        old_files = list(window.watched_dependency_files)
        window.dependency_watcher.removePaths(old_files)
        window.watched_dependency_files.clear()

    if not window.combo_sel:
        window._dependency_file_signature = (False, 0, 0)
        return

    dependency_file = os.path.join(window.combo_sel, DEPENDENCY_FILE_NAME)
    if os.path.isdir(window.combo_sel):
        window.dependency_watcher.addPath(window.combo_sel)
        window.watched_dependency_dirs.add(window.combo_sel)
    if os.path.isfile(dependency_file):
        window.dependency_watcher.addPath(dependency_file)
        window.watched_dependency_files.add(dependency_file)
        logger.debug(f"Now watching dependency file: {dependency_file}")
    window._dependency_file_signature = _dependency_file_signature(dependency_file)


def setup_tune_watcher(window) -> None:
    """Setup file system watcher for the current run tune directories."""
    if window.watched_tune_dirs:
        old_dirs = list(window.watched_tune_dirs)
        window.tune_watcher.removePaths(old_dirs)
        window.watched_tune_dirs.clear()
    if getattr(window, "watched_tune_files", None):
        old_files = list(window.watched_tune_files)
        window.tune_watcher.removePaths(old_files)
        window.watched_tune_files.clear()

    if not window.combo_sel:
        return

    run_dir = window.combo_sel
    tune_root = os.path.join(run_dir, "tune")

    watched_dirs = [run_dir]
    watched_files = []
    if os.path.isdir(tune_root):
        watched_dirs.append(tune_root)
        try:
            for entry in os.listdir(tune_root):
                target_dir = os.path.join(tune_root, entry)
                if os.path.isdir(target_dir):
                    watched_dirs.append(target_dir)
                    for filename in os.listdir(target_dir):
                        file_path = os.path.join(target_dir, filename)
                        if os.path.isfile(file_path):
                            watched_files.append(file_path)
        except OSError as exc:
            logger.error(f"Failed to enumerate tune directory {tune_root}: {exc}")

    existing_dirs = [path for path in watched_dirs if os.path.isdir(path)]
    if existing_dirs:
        window.tune_watcher.addPaths(existing_dirs)
        window.watched_tune_dirs.update(existing_dirs)
        logger.debug(f"Now watching tune directories: {existing_dirs}")
    existing_files = [path for path in watched_files if os.path.isfile(path)]
    if existing_files:
        window.tune_watcher.addPaths(existing_files)
        window.watched_tune_files.update(existing_files)
        logger.debug(f"Now watching tune files: {existing_files}")


def on_status_directory_changed(window, path: str) -> None:
    """Handle status directory content changes."""
    logger.debug(f"Status directory changed: {path}")
    window.setup_status_watcher()
    if not window.debounce_timer.isActive():
        window.debounce_timer.start(DEBOUNCE_DELAY_MS)


def on_status_file_changed(window, path: str) -> None:
    """Handle watched status file modifications."""
    logger.debug(f"Status file changed: {path}")
    if path and os.path.isfile(path):
        window.status_watcher.addPath(path)
        window.watched_status_files.add(path)
    else:
        window.setup_status_watcher()
    if not window.debounce_timer.isActive():
        window.debounce_timer.start(DEBOUNCE_DELAY_MS)


def on_tune_directory_changed(window, path: str) -> None:
    """Handle tune directory tree changes for the current run."""
    logger.debug(f"Tune directory changed: {path}")

    if not window.combo_sel:
        return

    run_dir = os.path.normpath(window.combo_sel)
    tune_root = os.path.normpath(os.path.join(window.combo_sel, "tune"))
    changed_path = os.path.normpath(path)

    if changed_path == run_dir or changed_path.startswith(tune_root + os.sep) or changed_path == tune_root:
        window.setup_tune_watcher()

    window._pending_tune_refresh = True
    _start_debounce_timer(window)


def on_tune_file_changed(window, path: str) -> None:
    """Handle watched tune-file modifications."""
    logger.debug(f"Tune file changed: {path}")
    if path and os.path.isfile(path):
        window.tune_watcher.addPath(path)
        window.watched_tune_files.add(path)
    window._pending_tune_refresh = True
    _start_debounce_timer(window)


def on_dependency_file_changed(window, path: str) -> None:
    """Handle watched target dependency file modifications."""
    logger.debug(f"Dependency file changed: {path}")
    window.setup_dependency_watcher()
    window._pending_dependency_refresh = True
    window._pending_tune_refresh = True
    if hasattr(window, "_mark_dependency_graph_dirty"):
        window._mark_dependency_graph_dirty()
    _start_debounce_timer(window)


def on_dependency_directory_changed(window, path: str) -> None:
    """Handle dependency-directory changes that may add or replace the file."""
    logger.debug(f"Dependency directory changed: {path}")
    if not window.combo_sel:
        return

    dependency_file = os.path.join(window.combo_sel, DEPENDENCY_FILE_NAME)
    previous_signature = getattr(window, "_dependency_file_signature", (False, 0, 0))
    current_signature = _dependency_file_signature(dependency_file)

    window.setup_dependency_watcher()
    if current_signature == previous_signature:
        return

    window._pending_dependency_refresh = True
    window._pending_tune_refresh = True
    if hasattr(window, "_mark_dependency_graph_dirty"):
        window._mark_dependency_graph_dirty()
    _start_debounce_timer(window)
