"""Runtime watcher and timer setup helpers for MainWindow."""

from PyQt5.QtCore import QFileSystemWatcher, QTimer

from new_gui.config.settings import BACKUP_TIMER_INTERVAL_MS


def init_runtime_observers(window) -> None:
    """Initialize status/tune file watchers and periodic refresh timers."""
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
    window.backup_timer.start(BACKUP_TIMER_INTERVAL_MS)

    window.debounce_timer = QTimer(window)
    window.debounce_timer.setSingleShot(True)
    window.debounce_timer.timeout.connect(window.change_run)
