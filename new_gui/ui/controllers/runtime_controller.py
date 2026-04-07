"""Runtime watcher and timer setup helpers for MainWindow."""

from PyQt5.QtCore import QFileSystemWatcher, QTimer

from new_gui.config.settings import BACKUP_TIMER_INTERVAL_MS
from new_gui.services import view_modes


def init_runtime_observers(window) -> None:
    """Initialize status/tune file watchers and periodic refresh timers."""
    window._runtime_observer_pause_depth = 0
    window._runtime_refresh_pending = False
    window._runtime_resume_refresh_scheduled = False
    window._runtime_backup_timer_was_active = False
    window.status_watcher = QFileSystemWatcher(window)
    window.status_watcher.directoryChanged.connect(window.on_status_directory_changed)
    window.status_watcher.fileChanged.connect(window.on_status_file_changed)
    window.watched_status_dirs = set()
    window.setup_status_watcher()

    window.tune_watcher = QFileSystemWatcher(window)
    window.tune_watcher.directoryChanged.connect(window.on_tune_directory_changed)
    window.watched_tune_dirs = set()
    window.setup_tune_watcher()

    window.backup_timer = QTimer(window)
    window.backup_timer.timeout.connect(window.change_run)

    window.debounce_timer = QTimer(window)
    window.debounce_timer.setSingleShot(True)
    window.debounce_timer.timeout.connect(window.change_run)
    update_backup_timer_state(window)


def _is_window_refresh_visible(window) -> bool:
    """Return whether the main window is visible enough for polling refreshes."""
    if not hasattr(window, "isVisible") or not window.isVisible():
        return False
    if hasattr(window, "isMinimized") and window.isMinimized():
        return False
    return True


def _is_main_tree_view_active(window) -> bool:
    """Return whether the UI is currently on the main run view."""
    if bool(getattr(window, "is_all_status_view", False)):
        return False
    if bool(getattr(window, "is_search_mode", False)):
        return False

    tab_label = ""
    if hasattr(window, "tab_label"):
        tab_label = window.tab_label.text()
    return view_modes.get_active_view_mode(bool(getattr(window, "is_all_status_view", False)), tab_label) == "main"


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


def should_backup_timer_run(window) -> bool:
    """Return whether the backup polling timer should be running now."""
    if runtime_observers_paused(window):
        return False
    if not _is_window_refresh_visible(window):
        return False
    if not _is_main_tree_view_active(window):
        return False
    return _has_active_run_targets(window)


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

    backup_timer = getattr(window, "backup_timer", None)
    window._runtime_backup_timer_was_active = should_backup_timer_run(window)
    if backup_timer is not None and backup_timer.isActive():
        backup_timer.stop()

    debounce_timer = getattr(window, "debounce_timer", None)
    if debounce_timer is not None and debounce_timer.isActive():
        debounce_timer.stop()
        mark_runtime_refresh_pending(window)

    if getattr(window, "_pending_tune_refresh", False):
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

    if bool(getattr(window, "_runtime_backup_timer_was_active", False)):
        update_backup_timer_state(window)

    if getattr(window, "_runtime_refresh_pending", False):
        _schedule_resume_refresh(window)
