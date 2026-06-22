"""Runtime watcher and timer setup helpers for MainWindow."""

import os
import time

from PyQt5.QtCore import QFileSystemWatcher, QTimer

from new_gui.shared.config.settings import (
    BACKUP_TIMER_INTERVAL_MS,
    STATUS_SNAPSHOT_POLL_INTERVAL_MS,
    logger,
)
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_modes

ACTION_REFRESH_WINDOW_SECONDS = 20.0


def init_runtime_observers(window) -> None:
    """Initialize status/tune file watchers and periodic refresh timers."""
    window._runtime_observer_pause_depth = 0
    window._runtime_refresh_pending = False
    window._runtime_resume_refresh_scheduled = False
    window._runtime_backup_timer_was_active = False
    window._action_refresh_window_until = 0.0
    window.status_watcher = QFileSystemWatcher(window)
    window.status_watcher.directoryChanged.connect(window.on_status_directory_changed)
    window.status_watcher.fileChanged.connect(window.on_status_file_changed)
    window.watched_status_dirs = set()
    window.watched_status_files = set()
    window.setup_status_watcher()

    window.tune_watcher = QFileSystemWatcher(window)
    window.tune_watcher.directoryChanged.connect(window.on_tune_directory_changed)
    window.tune_watcher.fileChanged.connect(window.on_tune_file_changed)
    window.watched_tune_dirs = set()
    window.watched_tune_files = set()
    window.setup_tune_watcher()

    window.dependency_watcher = QFileSystemWatcher(window)
    window.dependency_watcher.directoryChanged.connect(window.on_dependency_directory_changed)
    window.dependency_watcher.fileChanged.connect(window.on_dependency_file_changed)
    window.watched_dependency_dirs = set()
    window.watched_dependency_files = set()
    window.setup_dependency_watcher()

    window.backup_timer = QTimer(window)
    window.backup_timer.timeout.connect(window.change_run)

    window.debounce_timer = QTimer(window)
    window.debounce_timer.setSingleShot(True)
    window.debounce_timer.timeout.connect(window.change_run)
    window.status_snapshot_timer = QTimer(window)
    window.status_snapshot_timer.timeout.connect(window.poll_status_directory_snapshot)
    update_backup_timer_state(window)
    update_status_snapshot_timer_state(window)


def _clear_watcher_paths(window, watcher_name: str, path_set_names: list) -> None:
    """Remove all watched paths tracked by one watcher."""
    watcher = getattr(window, watcher_name, None)
    for path_set_name in path_set_names:
        watched_paths = getattr(window, path_set_name, None)
        if watched_paths:
            if watcher is not None:
                watcher.removePaths(list(watched_paths))
            watched_paths.clear()


def _stop_timer(window, timer_name: str) -> None:
    """Stop one timer when it exists and is active."""
    timer = getattr(window, timer_name, None)
    if timer is not None and timer.isActive():
        timer.stop()


def shutdown_runtime_observers(window) -> None:
    """Stop runtime refresh sources and background work during application exit."""
    window._runtime_observer_pause_depth = 1
    window._runtime_refresh_pending = False
    window._runtime_resume_refresh_scheduled = False
    window._runtime_backup_timer_was_active = False
    window._runtime_status_snapshot_timer_was_active = False

    for timer_name in ("backup_timer", "debounce_timer", "status_snapshot_timer"):
        _stop_timer(window, timer_name)

    _clear_watcher_paths(
        window,
        "status_watcher",
        ["watched_status_dirs", "watched_status_files"],
    )
    _clear_watcher_paths(
        window,
        "tune_watcher",
        ["watched_tune_dirs", "watched_tune_files"],
    )
    _clear_watcher_paths(
        window,
        "dependency_watcher",
        ["watched_dependency_dirs", "watched_dependency_files"],
    )

    executor = getattr(window, "_executor", None)
    if executor is not None:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=False)


def _is_window_refresh_visible(window) -> bool:
    """Return whether the main window is visible enough for polling refreshes."""
    if not hasattr(window, "isVisible") or not window.isVisible():
        return False
    if hasattr(window, "isMinimized") and window.isMinimized():
        return False
    return True


def _is_tree_refresh_mode_active(window) -> bool:
    """Return whether row-level runtime refresh should stay active."""
    if bool(getattr(window, "is_all_status_view", False)):
        return False
    if bool(getattr(window, "is_search_mode", False)):
        return False
    active_content_mode = view_mode_state.get_content_mode(window)
    if active_content_mode == "graph":
        return True

    return view_modes.get_active_view_mode(window) == "main"


def _has_active_run_targets(window) -> bool:
    """Return whether the current run still has active targets that need polling."""
    combo = getattr(window, "combo", None)
    current_run = combo.currentText() if combo is not None else ""
    if not current_run or current_run == "No runs found":
        return False

    status_cache = getattr(window, "_status_cache", None) or {}
    if status_cache.get("run") != current_run:
        return False

    statuses = status_cache.get("statuses", {}) or {}
    active_statuses = {"running", "scheduled", "pending"}
    return any(status in active_statuses for status in statuses.values())


def _has_watched_status_files(window) -> bool:
    """Return whether the current run has status files that need deletion polling."""
    watched_files = getattr(window, "watched_status_files", set()) or set()
    return any(os.path.isfile(path) for path in watched_files)


def _has_action_refresh_window(window) -> bool:
    """Return whether one action-forced refresh window is still active."""
    deadline = float(getattr(window, "_action_refresh_window_until", 0.0) or 0.0)
    return deadline > time.monotonic()


def start_action_refresh_window(window, seconds: float = ACTION_REFRESH_WINDOW_SECONDS, source: str = "") -> None:
    """Keep backup polling active briefly after actions so delayed writes are reflected."""
    duration = max(1.0, float(seconds or ACTION_REFRESH_WINDOW_SECONDS))
    deadline = time.monotonic() + duration
    window._action_refresh_window_until = max(
        float(getattr(window, "_action_refresh_window_until", 0.0) or 0.0),
        deadline,
    )
    update_backup_timer_state(window)
    if source:
        source_text = str(source).strip()
        if source_text:
            logger.info(
                f"Started action refresh window ({duration:.1f}s): {source_text}",
                extra={"ui_source": "runtime"},
            )


def should_backup_timer_run(window) -> bool:
    """Return whether the backup polling timer should be running now."""
    if runtime_observers_paused(window):
        return False
    if not _is_window_refresh_visible(window):
        return False
    if _has_action_refresh_window(window):
        return True
    if not _is_tree_refresh_mode_active(window):
        return False
    return _has_active_run_targets(window) or _has_watched_status_files(window)


def update_backup_timer_state(window) -> None:
    """Start or stop the backup polling timer based on current UI/runtime state."""
    backup_timer = getattr(window, "backup_timer", None)
    if backup_timer is None:
        return

    if should_backup_timer_run(window):
        if not backup_timer.isActive():
            backup_timer.start(BACKUP_TIMER_INTERVAL_MS)
        return

    if backup_timer.isActive():
        backup_timer.stop()


def should_status_snapshot_timer_run(window) -> bool:
    """Return whether missed status-file events should be polled for this view."""
    if runtime_observers_paused(window):
        return False
    if not _is_window_refresh_visible(window):
        return False
    if not _is_tree_refresh_mode_active(window):
        return False
    return _has_watched_status_files(window)


def update_status_snapshot_timer_state(window) -> None:
    """Start or stop the status snapshot poller for the current run."""
    snapshot_timer = getattr(window, "status_snapshot_timer", None)
    if snapshot_timer is None:
        return

    if should_status_snapshot_timer_run(window):
        if not snapshot_timer.isActive():
            snapshot_timer.start(STATUS_SNAPSHOT_POLL_INTERVAL_MS)
        return

    if snapshot_timer.isActive():
        snapshot_timer.stop()


def runtime_observers_paused(window) -> bool:
    """Return whether runtime-triggered refresh sources are currently paused."""
    return int(getattr(window, "_runtime_observer_pause_depth", 0)) > 0


def mark_runtime_refresh_pending(window) -> None:
    """Remember that one refresh should run once observers resume."""
    window._runtime_refresh_pending = True


def _schedule_resume_refresh(window) -> None:
    """Queue one deferred refresh after paused observers resume."""
    if getattr(window, "_runtime_resume_refresh_scheduled", False):
        return

    window._runtime_resume_refresh_scheduled = True

    def run_if_ready() -> None:
        window._runtime_resume_refresh_scheduled = False
        if runtime_observers_paused(window):
            mark_runtime_refresh_pending(window)
            return
        if not getattr(window, "_runtime_refresh_pending", False):
            return
        window._runtime_refresh_pending = False
        if hasattr(window, "change_run"):
            window.change_run()

    QTimer.singleShot(0, run_if_ready)


def pause_runtime_observers(window) -> None:
    """Temporarily pause watcher/timer refresh sources during tree filtering."""
    depth = int(getattr(window, "_runtime_observer_pause_depth", 0))
    window._runtime_observer_pause_depth = depth + 1
    if depth > 0:
        return

    status_watcher = getattr(window, "status_watcher", None)
    if status_watcher is not None:
        window._runtime_status_watcher_was_blocked = status_watcher.signalsBlocked()
        status_watcher.blockSignals(True)

    tune_watcher = getattr(window, "tune_watcher", None)
    if tune_watcher is not None:
        window._runtime_tune_watcher_was_blocked = tune_watcher.signalsBlocked()
        tune_watcher.blockSignals(True)

    dependency_watcher = getattr(window, "dependency_watcher", None)
    if dependency_watcher is not None:
        window._runtime_dependency_watcher_was_blocked = dependency_watcher.signalsBlocked()
        dependency_watcher.blockSignals(True)

    backup_timer = getattr(window, "backup_timer", None)
    window._runtime_backup_timer_was_active = should_backup_timer_run(window)
    if backup_timer is not None and backup_timer.isActive():
        backup_timer.stop()

    snapshot_timer = getattr(window, "status_snapshot_timer", None)
    window._runtime_status_snapshot_timer_was_active = should_status_snapshot_timer_run(window)
    if snapshot_timer is not None and snapshot_timer.isActive():
        snapshot_timer.stop()

    debounce_timer = getattr(window, "debounce_timer", None)
    if debounce_timer is not None and debounce_timer.isActive():
        debounce_timer.stop()
        mark_runtime_refresh_pending(window)

    if getattr(window, "_pending_tune_refresh", False):
        mark_runtime_refresh_pending(window)
    if getattr(window, "_pending_dependency_refresh", False):
        mark_runtime_refresh_pending(window)


def resume_runtime_observers(window) -> None:
    """Resume watcher/timer refresh sources after tree filtering stabilizes."""
    depth = int(getattr(window, "_runtime_observer_pause_depth", 0))
    if depth <= 0:
        return

    depth -= 1
    window._runtime_observer_pause_depth = depth
    if depth > 0:
        return

    status_watcher = getattr(window, "status_watcher", None)
    if status_watcher is not None:
        status_watcher.blockSignals(bool(getattr(window, "_runtime_status_watcher_was_blocked", False)))

    tune_watcher = getattr(window, "tune_watcher", None)
    if tune_watcher is not None:
        tune_watcher.blockSignals(bool(getattr(window, "_runtime_tune_watcher_was_blocked", False)))

    dependency_watcher = getattr(window, "dependency_watcher", None)
    if dependency_watcher is not None:
        dependency_watcher.blockSignals(
            bool(getattr(window, "_runtime_dependency_watcher_was_blocked", False))
        )

    if bool(getattr(window, "_runtime_backup_timer_was_active", False)):
        update_backup_timer_state(window)
    if bool(getattr(window, "_runtime_status_snapshot_timer_was_active", False)):
        update_status_snapshot_timer_state(window)

    if getattr(window, "_runtime_refresh_pending", False):
        _schedule_resume_refresh(window)
