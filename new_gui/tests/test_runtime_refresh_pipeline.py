import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from new_gui.main import MainWindow
from new_gui.model.services import tree_rows
from new_gui.model.services import run_views, view_run_selection
from new_gui.model.services import runtime_watchers
from new_gui.presentation.presenters import action_controller, runtime_controller, view_controller


class _FakeWatcher:
    def __init__(self):
        self.paths = set()

    def addPath(self, path: str):
        self.paths.add(path)

    def addPaths(self, paths):
        self.paths.update(paths or [])

    def removePaths(self, paths):
        for path in list(paths or []):
            self.paths.discard(path)


class _FakeDebounceTimer:
    def __init__(self):
        self._active = False
        self.start_calls = 0

    def isActive(self) -> bool:
        return self._active

    def start(self, _ms: int):
        self._active = True
        self.start_calls += 1


class _FakeBackupTimer:
    def __init__(self):
        self._active = False
        self.start_calls = 0
        self.stop_calls = 0

    def isActive(self) -> bool:
        return self._active

    def start(self, _ms: int):
        self._active = True
        self.start_calls += 1

    def stop(self):
        self._active = False
        self.stop_calls += 1


class _FakeExecutor:
    def __init__(self):
        self.shutdown_calls = []

    def shutdown(self, wait: bool = True, cancel_futures: bool = False):
        self.shutdown_calls.append(
            {"wait": wait, "cancel_futures": cancel_futures}
        )


class _FakeCombo:
    def __init__(self, entries=None, current_text: str = "", enabled: bool = True):
        self._entries = list(entries or [])
        self._enabled = bool(enabled)
        self._signals_blocked = False
        self._current_index = 0 if self._entries else -1
        if current_text and current_text in self._entries:
            self._current_index = self._entries.index(current_text)

    def count(self) -> int:
        return len(self._entries)

    def itemText(self, index: int) -> str:
        return self._entries[index]

    def blockSignals(self, value: bool) -> bool:
        previous_state = self._signals_blocked
        self._signals_blocked = bool(value)
        return previous_state

    def clear(self) -> None:
        self._entries = []
        self._current_index = -1

    def addItems(self, entries) -> None:
        for entry in list(entries or []):
            self.addItem(entry)

    def addItem(self, entry: str) -> None:
        self._entries.append(entry)
        if self._current_index < 0:
            self._current_index = 0

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def isEnabled(self) -> bool:
        return self._enabled

    def setCurrentIndex(self, index: int) -> None:
        self._current_index = index

    def findText(self, text: str) -> int:
        try:
            return self._entries.index(text)
        except ValueError:
            return -1

    def currentText(self) -> str:
        if 0 <= self._current_index < len(self._entries):
            return self._entries[self._current_index]
        return ""


class RuntimeWatcherStatusFileTests(unittest.TestCase):
    def test_shutdown_runtime_observers_stops_timers_watchers_and_executor(self) -> None:
        window = type("Window", (), {})()
        window.status_watcher = _FakeWatcher()
        window.tune_watcher = _FakeWatcher()
        window.dependency_watcher = _FakeWatcher()
        window.watched_status_dirs = {"/runs/run1/status"}
        window.watched_status_files = {"/runs/run1/status/a.finish"}
        window.watched_tune_dirs = {"/runs/run1", "/runs/run1/tune"}
        window.watched_tune_files = {"/runs/run1/tune/a/a.tcl"}
        window.watched_dependency_dirs = {"/runs/run1"}
        window.watched_dependency_files = {"/runs/run1/.target_dependency.csh"}
        window.status_watcher.paths.update(window.watched_status_dirs | window.watched_status_files)
        window.tune_watcher.paths.update(window.watched_tune_dirs | window.watched_tune_files)
        window.dependency_watcher.paths.update(
            window.watched_dependency_dirs | window.watched_dependency_files
        )
        window.backup_timer = _FakeBackupTimer()
        window.debounce_timer = _FakeBackupTimer()
        window.status_snapshot_timer = _FakeBackupTimer()
        for timer in (window.backup_timer, window.debounce_timer, window.status_snapshot_timer):
            timer.start(1)
        window._executor = _FakeExecutor()

        runtime_controller.shutdown_runtime_observers(window)

        self.assertEqual(set(), window.watched_status_dirs)
        self.assertEqual(set(), window.watched_status_files)
        self.assertEqual(set(), window.watched_tune_dirs)
        self.assertEqual(set(), window.watched_tune_files)
        self.assertEqual(set(), window.watched_dependency_dirs)
        self.assertEqual(set(), window.watched_dependency_files)
        self.assertEqual(set(), window.status_watcher.paths)
        self.assertEqual(set(), window.tune_watcher.paths)
        self.assertEqual(set(), window.dependency_watcher.paths)
        self.assertFalse(window.backup_timer.isActive())
        self.assertFalse(window.debounce_timer.isActive())
        self.assertFalse(window.status_snapshot_timer.isActive())
        self.assertEqual(
            [{"wait": False, "cancel_futures": True}],
            window._executor.shutdown_calls,
        )

    def test_setup_status_watcher_registers_directory_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_dir = os.path.join(tmp_dir, "status")
            os.makedirs(status_dir, exist_ok=True)
            file_a = os.path.join(status_dir, "a.status")
            file_b = os.path.join(status_dir, "b.status")
            with open(file_a, "w", encoding="utf-8") as handle:
                handle.write("a")
            with open(file_b, "w", encoding="utf-8") as handle:
                handle.write("b")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.status_watcher = _FakeWatcher()
            window.watched_status_dirs = set()
            window.watched_status_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window.setup_status_watcher = lambda: runtime_watchers.setup_status_watcher(window)

            runtime_watchers.setup_status_watcher(window)

            self.assertIn(status_dir, window.watched_status_dirs)
            self.assertEqual({file_a, file_b}, window.watched_status_files)
            self.assertTrue({status_dir, file_a, file_b}.issubset(window.status_watcher.paths))

    def test_status_file_changed_re_registers_file_and_schedules_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_dir = os.path.join(tmp_dir, "status")
            os.makedirs(status_dir, exist_ok=True)
            file_a = os.path.join(status_dir, "a.status")
            with open(file_a, "w", encoding="utf-8") as handle:
                handle.write("a")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.status_watcher = _FakeWatcher()
            window.watched_status_dirs = {status_dir}
            window.watched_status_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window.setup_status_watcher = lambda: runtime_watchers.setup_status_watcher(window)

            runtime_watchers.on_status_file_changed(window, file_a)
            self.assertIn(file_a, window.watched_status_files)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_deleted_status_file_rebuilds_watched_paths_and_schedules_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_dir = os.path.join(tmp_dir, "status")
            os.makedirs(status_dir, exist_ok=True)
            deleted_file = os.path.join(status_dir, "alpha.running")
            remaining_file = os.path.join(status_dir, "beta.finish")
            with open(remaining_file, "w", encoding="utf-8") as handle:
                handle.write("beta")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.status_watcher = _FakeWatcher()
            window.watched_status_dirs = {status_dir}
            window.watched_status_files = {deleted_file, remaining_file}
            window.status_watcher.paths.update(
                window.watched_status_dirs | window.watched_status_files
            )
            window.debounce_timer = _FakeDebounceTimer()
            window.setup_status_watcher = lambda: runtime_watchers.setup_status_watcher(window)

            runtime_watchers.on_status_file_changed(window, deleted_file)

            self.assertEqual({remaining_file}, window.watched_status_files)
            self.assertNotIn(deleted_file, window.status_watcher.paths)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_status_snapshot_poll_detects_deleted_file_and_schedules_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_dir = os.path.join(tmp_dir, "status")
            os.makedirs(status_dir, exist_ok=True)
            deleted_file = os.path.join(status_dir, "alpha.finish")
            with open(deleted_file, "w", encoding="utf-8") as handle:
                handle.write("finish")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.status_watcher = _FakeWatcher()
            window.watched_status_dirs = set()
            window.watched_status_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window.setup_status_watcher = lambda: runtime_watchers.setup_status_watcher(window)

            runtime_watchers.setup_status_watcher(window)
            self.assertIn(deleted_file, window.watched_status_files)

            os.remove(deleted_file)
            runtime_watchers.poll_status_directory_snapshot(window)

            self.assertEqual(set(), window.watched_status_files)
            self.assertNotIn(deleted_file, window.status_watcher.paths)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_setup_status_watcher_clears_existing_paths_when_run_selection_is_missing(self) -> None:
        window = type("Window", (), {})()
        window.combo_sel = None
        window.status_watcher = _FakeWatcher()
        window.watched_status_dirs = {"/runs/run1/status"}
        window.watched_status_files = {"/runs/run1/status/a.finish"}
        window.status_watcher.paths.update(window.watched_status_dirs | window.watched_status_files)

        runtime_watchers.setup_status_watcher(window)

        self.assertEqual(set(), window.watched_status_dirs)
        self.assertEqual(set(), window.watched_status_files)
        self.assertEqual(set(), window.status_watcher.paths)

    def test_setup_tune_watcher_clears_existing_paths_when_run_selection_is_missing(self) -> None:
        window = type("Window", (), {})()
        window.combo_sel = None
        window.tune_watcher = _FakeWatcher()
        window.watched_tune_dirs = {"/runs/run1", "/runs/run1/tune"}
        window.watched_tune_files = {"/runs/run1/tune/alpha/alpha.foo.tcl"}
        window.tune_watcher.paths.update(window.watched_tune_dirs | window.watched_tune_files)

        runtime_watchers.setup_tune_watcher(window)

        self.assertEqual(set(), window.watched_tune_dirs)
        self.assertEqual(set(), window.watched_tune_files)
        self.assertEqual(set(), window.tune_watcher.paths)

    def test_setup_tune_watcher_registers_directories_and_tune_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tune_target_dir = os.path.join(tmp_dir, "tune", "alpha")
            os.makedirs(tune_target_dir, exist_ok=True)
            tune_file = os.path.join(tune_target_dir, "alpha.foo.tcl")
            with open(tune_file, "w", encoding="utf-8") as handle:
                handle.write("foo")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.tune_watcher = _FakeWatcher()
            window.watched_tune_dirs = set()
            window.watched_tune_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window.setup_tune_watcher = lambda: runtime_watchers.setup_tune_watcher(window)

            runtime_watchers.setup_tune_watcher(window)

            self.assertTrue(
                {
                    tmp_dir,
                    os.path.join(tmp_dir, "tune"),
                    tune_target_dir,
                }.issubset(window.watched_tune_dirs)
            )
            self.assertEqual({tune_file}, window.watched_tune_files)
            self.assertTrue({tune_file}.issubset(window.tune_watcher.paths))

    def test_setup_tune_watcher_registers_new_file_after_target_directory_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tune_target_dir = os.path.join(tmp_dir, "tune", "alpha")
            os.makedirs(tune_target_dir, exist_ok=True)

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.tune_watcher = _FakeWatcher()
            window.watched_tune_dirs = set()
            window.watched_tune_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window._pending_tune_refresh = False
            window.setup_tune_watcher = lambda: runtime_watchers.setup_tune_watcher(window)

            runtime_watchers.setup_tune_watcher(window)
            tune_file = os.path.join(tune_target_dir, "alpha.foo.tcl")
            with open(tune_file, "w", encoding="utf-8") as handle:
                handle.write("foo")

            runtime_watchers.on_tune_directory_changed(window, tune_target_dir)

            self.assertIn(tune_file, window.watched_tune_files)
            self.assertTrue(window._pending_tune_refresh)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_tune_file_changed_re_registers_file_and_schedules_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tune_target_dir = os.path.join(tmp_dir, "tune", "alpha")
            os.makedirs(tune_target_dir, exist_ok=True)
            tune_file = os.path.join(tune_target_dir, "alpha.foo.tcl")
            with open(tune_file, "w", encoding="utf-8") as handle:
                handle.write("foo")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.tune_watcher = _FakeWatcher()
            window.watched_tune_dirs = {tmp_dir, os.path.join(tmp_dir, "tune"), tune_target_dir}
            window.watched_tune_files = set()
            window.tune_watcher.paths.update(window.watched_tune_dirs)
            window.debounce_timer = _FakeDebounceTimer()
            window._pending_tune_refresh = False
            window.setup_tune_watcher = lambda: runtime_watchers.setup_tune_watcher(window)

            runtime_watchers.on_tune_file_changed(window, tune_file)

            self.assertIn(tune_file, window.watched_tune_files)
            self.assertTrue(window._pending_tune_refresh)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_setup_dependency_watcher_registers_dependency_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dependency_file = os.path.join(tmp_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\n')

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.dependency_watcher = _FakeWatcher()
            window.watched_dependency_files = set()

            runtime_watchers.setup_dependency_watcher(window)

            self.assertEqual({dependency_file}, window.watched_dependency_files)
            self.assertIn(dependency_file, window.dependency_watcher.paths)

    def test_dependency_file_changed_re_registers_file_and_schedules_structural_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dependency_file = os.path.join(tmp_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\n')

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.dependency_watcher = _FakeWatcher()
            window.watched_dependency_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window._pending_dependency_refresh = False
            window.marked_dirty = False
            window.setup_dependency_watcher = lambda: runtime_watchers.setup_dependency_watcher(window)
            window._mark_dependency_graph_dirty = lambda: setattr(window, "marked_dirty", True)

            runtime_watchers.on_dependency_file_changed(window, dependency_file)

            self.assertIn(dependency_file, window.watched_dependency_files)
            self.assertTrue(window._pending_dependency_refresh)
            self.assertTrue(window.marked_dirty)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_dependency_file_removed_rebuilds_watched_paths_and_schedules_structural_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            deleted_file = os.path.join(tmp_dir, ".target_dependency.csh")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.dependency_watcher = _FakeWatcher()
            window.watched_dependency_files = {deleted_file}
            window.dependency_watcher.paths.add(deleted_file)
            window.debounce_timer = _FakeDebounceTimer()
            window._pending_dependency_refresh = False
            window.setup_dependency_watcher = lambda: runtime_watchers.setup_dependency_watcher(window)

            runtime_watchers.on_dependency_file_changed(window, deleted_file)

            self.assertEqual(set(), window.watched_dependency_files)
            self.assertNotIn(deleted_file, window.dependency_watcher.paths)
            self.assertTrue(window._pending_dependency_refresh)
            self.assertEqual(1, window.debounce_timer.start_calls)

    def test_dependency_file_created_after_setup_schedules_structural_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dependency_file = os.path.join(tmp_dir, ".target_dependency.csh")

            window = type("Window", (), {})()
            window.combo_sel = tmp_dir
            window.dependency_watcher = _FakeWatcher()
            window.watched_dependency_dirs = set()
            window.watched_dependency_files = set()
            window.debounce_timer = _FakeDebounceTimer()
            window._pending_dependency_refresh = False
            window.setup_dependency_watcher = lambda: runtime_watchers.setup_dependency_watcher(window)

            runtime_watchers.setup_dependency_watcher(window)
            self.assertIn(tmp_dir, window.watched_dependency_dirs)

            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\n')

            runtime_watchers.on_dependency_directory_changed(window, tmp_dir)

            self.assertIn(dependency_file, window.watched_dependency_files)
            self.assertTrue(window._pending_dependency_refresh)
            self.assertEqual(1, window.debounce_timer.start_calls)


class TuneRuntimeRefreshIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _run_event_loop(self, milliseconds: int) -> None:
        QTimer.singleShot(milliseconds, self._app.quit)
        self._app.exec_()
        self._app.processEvents()

    def _visible_target_names(self, window) -> list:
        targets = []

        def walk(parent_item=None):
            row_count = parent_item.rowCount() if parent_item is not None else window.model.rowCount()
            for row_idx in range(row_count):
                row_items = tree_rows.get_row_items(window.model, row_idx, parent_item)
                target_item = row_items[1] if len(row_items) > 1 else None
                target_name = tree_rows.get_row_target_name(target_item)
                if target_name:
                    targets.append(target_name)
                level_item = row_items[0] if row_items else None
                if level_item and level_item.hasChildren():
                    walk(level_item)

        walk()
        return targets

    def test_new_tune_file_refreshes_tree_without_switching_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "sample_run")
            os.makedirs(os.path.join(run_dir, "status"), exist_ok=True)
            with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\\n')

            window = MainWindow()
            window.show()
            self._app.processEvents()

            window.run_base_dir = tmp_dir
            window.combo.blockSignals(True)
            window.combo.clear()
            window.combo.addItem("sample_run")
            window.combo.setCurrentIndex(0)
            window.combo.blockSignals(False)
            window.combo_sel = run_dir
            window.refresh_left_sidebar_categories = lambda run_dir=None: None
            window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
            window.setup_status_watcher = lambda: None
            window._build_status_cache("sample_run")
            window.populate_data(force_rebuild=True)
            self._app.processEvents()

            self.assertEqual("", window.model.item(0, 3).text())

            tune_target_dir = os.path.join(run_dir, "tune", "alpha")
            os.makedirs(tune_target_dir, exist_ok=True)
            tune_file = os.path.join(tune_target_dir, "alpha.foo.tcl")
            with open(tune_file, "w", encoding="utf-8") as handle:
                handle.write("# tune\\n")

            runtime_watchers.on_tune_directory_changed(window, tune_target_dir)
            self._app.processEvents()
            self.assertTrue(window._pending_tune_refresh)

            window.change_run()
            self._app.processEvents()

            self.assertEqual("foo", window.model.item(0, 3).text())

    def test_dependency_file_update_rebuilds_tree_without_switching_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "sample_run")
            os.makedirs(os.path.join(run_dir, "status"), exist_ok=True)
            dependency_file = os.path.join(run_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\n')

            window = MainWindow()
            window.show()
            self._app.processEvents()

            window.run_base_dir = tmp_dir
            window.combo.blockSignals(True)
            window.combo.clear()
            window.combo.addItem("sample_run")
            window.combo.setCurrentIndex(0)
            window.combo.blockSignals(False)
            window.combo_sel = run_dir
            window.refresh_left_sidebar_categories = lambda run_dir=None: None
            window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
            window.setup_status_watcher = lambda: None
            window.setup_tune_watcher = lambda: None
            window._build_status_cache("sample_run")
            window.populate_data(force_rebuild=True)
            self._app.processEvents()

            self.assertEqual("alpha", window.model.item(0, 1).text())

            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha beta"\n')

            runtime_watchers.on_dependency_file_changed(window, dependency_file)
            self._app.processEvents()
            self.assertTrue(window._pending_dependency_refresh)

            window.change_run()
            self._app.processEvents()

            self.assertEqual(["alpha", "beta"], self._visible_target_names(window))

    def test_deleted_terminal_status_file_clears_current_run_without_switching_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "sample_run")
            status_dir = os.path.join(run_dir, "status")
            os.makedirs(status_dir, exist_ok=True)
            dependency_file = os.path.join(run_dir, ".target_dependency.csh")
            status_file = os.path.join(status_dir, "alpha.finish")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha"\n')
            with open(status_file, "w", encoding="utf-8") as handle:
                handle.write("finish")

            window = MainWindow()
            window.show()
            self._app.processEvents()

            try:
                window.run_base_dir = tmp_dir
                window.combo.blockSignals(True)
                window.combo.clear()
                window.combo.addItem("sample_run")
                window.combo.setCurrentIndex(0)
                window.combo.blockSignals(False)
                window.combo_sel = run_dir
                window.refresh_left_sidebar_categories = lambda run_dir=None: None
                window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
                window.setup_tune_watcher = lambda: None
                window.setup_dependency_watcher = lambda: None
                window._build_status_cache("sample_run")
                window.populate_data(force_rebuild=True)
                window.setup_status_watcher()
                self._app.processEvents()

                self.assertEqual("finish", window.model.item(0, 2).text())

                with mock.patch.object(runtime_controller, "BACKUP_TIMER_INTERVAL_MS", 50):
                    runtime_controller.update_backup_timer_state(window)
                    self.assertTrue(window.backup_timer.isActive())

                    os.remove(status_file)
                    self._run_event_loop(180)

                self.assertEqual("", window.model.item(0, 2).text())
            finally:
                window.close()


class MissingRunSelectionTests(unittest.TestCase):
    class _Window:
        def __init__(self):
            self.run_base_dir = "/runs"
            self.combo = _FakeCombo(["run1"], current_text="run1", enabled=True)
            self.combo_sel = "/runs/run1"
            self.is_all_status_view = False
            self.cached_targets_by_level = {1: ["alpha"]}
            self._cached_targets_run = "run1"
            self.cached_collapsible_target_groups = {"Generic": ["alpha"]}
            self._cached_collapsible_target_groups_run = "run1"
            self._status_cache = {"run": "run1", "statuses": {"alpha": "running"}, "times": {}}
            self._pending_tune_refresh = True
            self._terminal_follow_run = True
            self._runtime_observer_pause_depth = 0
            self._action_refresh_window_until = 0.0
            self.backup_timer = _FakeBackupTimer()
            self.notifications = []
            self.calls = []
            self.status_watcher = _FakeWatcher()
            self.tune_watcher = _FakeWatcher()
            self.watched_status_dirs = {"/runs/run1/status"}
            self.watched_status_files = {"/runs/run1/status/alpha.running"}
            self.watched_tune_dirs = {"/runs/run1", "/runs/run1/tune"}
            self.status_watcher.paths.update(self.watched_status_dirs | self.watched_status_files)
            self.tune_watcher.paths.update(self.watched_tune_dirs)
            self._embedded_terminal = type(
                "Terminal",
                (),
                {
                    "stopped": False,
                    "messages": [],
                    "stop_terminal": lambda terminal_self: setattr(terminal_self, "stopped", True),
                    "_show_message": lambda terminal_self, message: terminal_self.messages.append(message),
                },
            )()

        def isVisible(self) -> bool:
            return True

        def isMinimized(self) -> bool:
            return False

        def show_notification(self, title: str, message: str, notification_type: str) -> None:
            self.notifications.append((title, message, notification_type))

        def refresh_left_sidebar_categories(self, run_dir=None) -> None:
            self.calls.append(("refresh_sidebar", run_dir))

        def setup_status_watcher(self) -> None:
            runtime_watchers.setup_status_watcher(self)

        def setup_tune_watcher(self) -> None:
            runtime_watchers.setup_tune_watcher(self)

        def _invalidate_main_view_snapshot(self) -> None:
            self.calls.append("invalidate_main_snapshot")

        def _invalidate_search_view_snapshot(self) -> None:
            self.calls.append("invalidate_search_snapshot")

        def _reset_main_tree_model(self) -> None:
            self.calls.append("reset_main_tree_model")

        def _set_main_run_tab_state(self) -> None:
            self.calls.append("set_main_run_tab_state")

        def update_status_bar(self) -> None:
            self.calls.append("update_status_bar")

        def _update_column_visibility_control_state(self) -> None:
            self.calls.append("update_column_visibility")

        def _mark_dependency_graph_dirty(self) -> None:
            self.calls.append("mark_dependency_graph_dirty")

        def set_terminal_follow_run_enabled(self, enabled: bool) -> None:
            self._terminal_follow_run = bool(enabled)
            self.calls.append(("terminal_follow", bool(enabled)))

    def test_refresh_run_list_keeps_missing_selected_run_visible_and_clears_runtime_state(self) -> None:
        window = self._Window()

        with mock.patch.object(view_controller.run_repository, "list_available_runs", return_value=["run2"]):
            refresh_state = view_controller.refresh_run_list(window, activate_if_selection_changed=True)

        self.assertEqual(
            ["run1 (missing)", "run2"],
            [window.combo.itemText(index) for index in range(window.combo.count())],
        )
        self.assertEqual("run1 (missing)", window.combo.currentText())
        self.assertTrue(window.combo.isEnabled())
        self.assertIsNone(window.combo_sel)
        self.assertTrue(refresh_state["missing_selected_run"])
        self.assertEqual("run1", refresh_state["selected_run"])
        self.assertEqual("run1", getattr(window, "_missing_selected_run_name", ""))
        self.assertEqual({}, window.cached_targets_by_level)
        self.assertEqual("", window._cached_targets_run)
        self.assertEqual({}, window.cached_collapsible_target_groups)
        self.assertEqual("", window._cached_collapsible_target_groups_run)
        self.assertEqual({"run": "", "statuses": {}, "times": {}}, window._status_cache)
        self.assertFalse(window._pending_tune_refresh)
        self.assertFalse(window._terminal_follow_run)
        self.assertEqual(1, len(window.notifications))
        self.assertIn("removed from disk", window.notifications[0][1])
        self.assertIn("Choose another run", window.notifications[0][1])
        self.assertEqual(set(), window.watched_status_dirs)
        self.assertEqual(set(), window.watched_status_files)
        self.assertEqual(set(), window.watched_tune_dirs)
        self.assertTrue(window._embedded_terminal.stopped)
        self.assertTrue(any("run1" in message for message in window._embedded_terminal.messages))

        with mock.patch.object(view_controller.run_repository, "list_available_runs", return_value=["run2"]):
            view_controller.refresh_run_list(window, activate_if_selection_changed=True)

        self.assertEqual(1, len(window.notifications))

    def test_missing_run_placeholder_is_not_a_valid_selection_state(self) -> None:
        self.assertIsNone(run_views.build_run_selection_state("run1 (missing)", "/runs"))
        self.assertTrue(view_run_selection.is_missing_run_label("run1 (missing)"))


class RuntimeForcedRefreshWindowTests(unittest.TestCase):
    class _FakeTimer:
        def __init__(self):
            self._active = False
            self.start_calls = 0

        def isActive(self) -> bool:
            return self._active

        def start(self, _ms: int):
            self._active = True
            self.start_calls += 1

        def stop(self):
            self._active = False

    class _FakeCombo:
        def currentText(self) -> str:
            return "sample_run"

    class _FakeLabel:
        def text(self) -> str:
            return "Category: STAGE / Alpha"

    class _Window:
        def __init__(self):
            self._runtime_observer_pause_depth = 0
            self.is_all_status_view = False
            self.is_search_mode = False
            self._active_content_mode = "main"
            self._action_refresh_window_until = 0.0
            self._status_cache = {"run": "sample_run", "statuses": {"t1": "finish"}}
            self.combo = RuntimeForcedRefreshWindowTests._FakeCombo()
            self.tab_label = RuntimeForcedRefreshWindowTests._FakeLabel()
            self.backup_timer = RuntimeForcedRefreshWindowTests._FakeTimer()

        def isVisible(self) -> bool:
            return True

        def isMinimized(self) -> bool:
            return False

    def test_action_refresh_window_forces_backup_timer_outside_main_mode(self) -> None:
        window = self._Window()
        self.assertFalse(runtime_controller.should_backup_timer_run(window))

        runtime_controller.start_action_refresh_window(window, seconds=1.0, source="unit_test")
        self.assertTrue(runtime_controller.should_backup_timer_run(window))
        self.assertEqual(1, window.backup_timer.start_calls)


class ActionControllerAsyncRefreshTests(unittest.TestCase):
    def test_async_action_requests_ui_refresh(self) -> None:
        class _FakeUi:
            def __init__(self):
                self.run_base_dir = "/tmp"
                self.requests = []
                self.cleared = False

            def get_selected_action_targets(self):
                return ["target_a"]

            def build_search_context(self, _selected_targets=None):
                return {"is_search_mode": False, "search_text": "", "selected_targets": ["target_a"], "scroll_value": 7}

            def current_run_name(self):
                return "sample_run"

            def submit_background(self, func, *args):
                func(*args)

            def append_ui_log(self, *args, **kwargs):
                del args, kwargs

            def request_action_refresh(self, search_context: dict, command: str = ""):
                self.requests.append({"search_context": dict(search_context or {}), "command": command})

            def clear_tree_selection(self):
                self.cleared = True

        fake_ui = _FakeUi()
        action_request = {
            "command": "cd /tmp/sample_run && XMeta_invalid target_a",
            "argv": ["XMeta_invalid", "target_a"],
            "cwd": "/tmp/sample_run",
            "log_message": "sample_run, XMeta_invalid target_a.",
            "run_sync": False,
            "timeout": 300,
        }

        with mock.patch.object(action_controller, "_bridge", return_value=fake_ui):
            with mock.patch.object(action_controller.action_flow, "build_action_request", return_value=action_request):
                with mock.patch.object(
                    action_controller.action_flow,
                    "execute_shell_command",
                    return_value={"stdout": "", "stderr": "", "returncode": 0, "timed_out": False, "error": None},
                ):
                    action_controller.start(object(), "XMeta_invalid")

        self.assertEqual(1, len(fake_ui.requests))
        self.assertTrue(fake_ui.requests[0]["command"].endswith("XMeta_invalid target_a"))
        self.assertTrue(fake_ui.cleared)

    def test_long_running_action_uses_detached_dispatch_and_immediate_refresh(self) -> None:
        class _FakeUi:
            def __init__(self):
                self.run_base_dir = "/tmp"
                self.requests = []
                self.detached_logs = []
                self.background_calls = 0
                self.cleared = False

            def get_selected_action_targets(self):
                return ["target_a"]

            def build_search_context(self, _selected_targets=None):
                return {"is_search_mode": False, "search_text": "", "selected_targets": ["target_a"], "scroll_value": 9}

            def current_run_name(self):
                return "sample_run"

            def submit_background(self, func, *args):
                self.background_calls += 1
                func(*args)

            def append_ui_log(self, level, source, message, command="", details=""):
                self.detached_logs.append(
                    {"level": level, "source": source, "message": message, "command": command, "details": details}
                )

            def request_action_refresh(self, search_context: dict, command: str = ""):
                self.requests.append({"search_context": dict(search_context or {}), "command": command})

            def clear_tree_selection(self):
                self.cleared = True

        fake_ui = _FakeUi()
        action_request = {
            "command": "cd /tmp/sample_run && XMeta_run target_a",
            "argv": ["XMeta_run", "target_a"],
            "cwd": "/tmp/sample_run",
            "log_message": "sample_run, XMeta_run target_a.",
            "run_sync": False,
            "timeout": None,
            "detached": True,
        }

        with mock.patch.object(action_controller, "_bridge", return_value=fake_ui):
            with mock.patch.object(action_controller.action_flow, "build_action_request", return_value=action_request):
                with mock.patch.object(
                    action_controller.action_flow,
                    "execute_shell_command_detached",
                    return_value={
                        "stdout": "",
                        "stderr": "",
                        "returncode": 0,
                        "timed_out": False,
                        "error": None,
                        "pid": 12345,
                        "detached": True,
                    },
                ):
                    action_controller.start(object(), "XMeta_run")

        self.assertEqual(0, fake_ui.background_calls)
        self.assertEqual(1, len(fake_ui.requests))
        self.assertTrue(fake_ui.requests[0]["command"].endswith("XMeta_run target_a"))
        self.assertEqual(1, len(fake_ui.detached_logs))
        self.assertTrue(fake_ui.cleared)


if __name__ == "__main__":
    unittest.main()
