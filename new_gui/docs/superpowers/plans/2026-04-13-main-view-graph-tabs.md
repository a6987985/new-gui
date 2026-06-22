# Main View Graph Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `Dependency Graph` into the main workspace as a persistent content tab beside `Main View`, with lazy graph loading and no regression in existing `TreeView` behavior.

**Architecture:** Keep the current top pseudo-tab state for tree-only modes, but add a real content-level `QTabWidget` under the main content row. Extract the current graph dialog body into an embeddable `DependencyGraphPanel`, then add a focused `content_tab_controller` to coordinate tab activation, lazy graph rebuilds, sidebar visibility, and graph-to-tree navigation.

**Tech Stack:** Python 3.13, PyQt5, unittest, existing governance smoke harness, existing `new_gui` builder/presenter/service layering.

---

## File Structure

**Create:**

- `new_gui/presentation/presenters/content_tab_controller.py`
- `new_gui/presentation/views/widgets/dependency_graph_panel.py`
- `tests/test_main_content_graph_tabs.py`

**Modify:**

- `new_gui/main.py:724-790`
- `new_gui/main.py:983-1015`
- `new_gui/presentation/views/builders/top_panel_builder.py:42-223`
- `new_gui/presentation/views/dialogs/dependency_graph.py:1-260`
- `new_gui/model/services/dependency_graph_navigation.py:61-137`
- `new_gui/presentation/presenters/theme_controller.py:194-325`
- `new_gui/presentation/presenters/view_controller.py:391-452`
- `new_gui/presentation/presenters/view_window_bridge.py:1-220`
- `new_gui/infrastructure/tools/governance_smoke.py:866-952`

**Keep unchanged unless blocked:**

- `new_gui/presentation/views/builders/menu_builder.py`
- `new_gui/presentation/views/builders/shortcut_builder.py`

Those two already route through `window.show_dependency_graph`. Changing the method semantics is enough unless the implementation exposes a concrete mismatch.

## Task 1: Add the Content Tab Shell

**Files:**

- Create: `tests/test_main_content_graph_tabs.py`
- Modify: `new_gui/main.py:44-118`
- Modify: `new_gui/presentation/views/builders/top_panel_builder.py:42-223`
- Test: `tests/test_main_content_graph_tabs.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from new_gui.main import MainWindow


class MainContentGraphTabsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_main_window_builds_persistent_main_and_graph_content_tabs(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        self.assertEqual(2, window._content_mode_tabs.count())
        self.assertEqual("Main View", window._content_mode_tabs.tabText(0))
        self.assertEqual("Dependency Graph", window._content_mode_tabs.tabText(1))
        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertIs(window._content_mode_tabs.widget(0), window._main_view_page)
        self.assertIs(window._content_mode_tabs.widget(1), window._graph_view_page)
        self.assertIs(window._content_splitter.parentWidget(), window._main_view_page)
        self.assertIsNone(window._dependency_graph_panel)
        self.assertTrue(window.left_sidebar.isVisible())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: FAIL with `AttributeError` or an assertion failure because `_content_mode_tabs`, `_main_view_page`, and `_graph_view_page` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# new_gui/main.py
# append these fields near the end of MainWindow._init_core_variables()
self._active_content_mode = "main"
self._dependency_graph_panel = None
self._dependency_graph_dirty = True
self._dependency_graph_initialized = False
self._dependency_graph_return_context = {}


# new_gui/presentation/views/builders/top_panel_builder.py
from PyQt5.QtWidgets import QSplitter, QSizePolicy, QTabWidget, QTreeView, QVBoxLayout, QWidget


def init_top_panel(window) -> None:
    window._content_splitter = QSplitter(Qt.Vertical)
    window._main_view_page = QWidget(window)
    main_view_layout = QVBoxLayout(window._main_view_page)
    main_view_layout.setContentsMargins(0, 0, 0, 0)
    main_view_layout.setSpacing(0)
    main_view_layout.addWidget(window._content_splitter)

    window._graph_view_page = QWidget(window)
    window._graph_view_layout = QVBoxLayout(window._graph_view_page)
    window._graph_view_layout.setContentsMargins(0, 0, 0, 0)
    window._graph_view_layout.setSpacing(0)

    window._content_mode_tabs = QTabWidget(window._content_row)
    window._content_mode_tabs.addTab(window._main_view_page, "Main View")
    window._content_mode_tabs.addTab(window._graph_view_page, "Dependency Graph")
    window._content_mode_tabs.setCurrentWidget(window._main_view_page)

    content_row_layout.addWidget(window.left_sidebar)
    content_row_layout.addWidget(window._content_mode_tabs, 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: PASS for `test_main_window_builds_persistent_main_and_graph_content_tabs`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_content_graph_tabs.py new_gui/main.py new_gui/presentation/views/builders/top_panel_builder.py
git commit -m "feat: add main content tabs shell"
```

## Task 2: Extract an Embeddable Dependency Graph Panel

**Files:**

- Create: `new_gui/presentation/views/widgets/dependency_graph_panel.py`
- Modify: `new_gui/presentation/views/dialogs/dependency_graph.py:1-260`
- Test: `tests/test_main_content_graph_tabs.py`

- [ ] **Step 1: Write the failing test**

```python
def _sample_graph_data():
    return {
        "nodes": [("root_target", "finish"), ("mid_target", "running"), ("leaf_target", "failed")],
        "edges": [("root_target", "mid_target"), ("mid_target", "leaf_target")],
        "levels": {0: ["root_target"], 1: ["mid_target"], 2: ["leaf_target"]},
        "trace_targets": {
            "upstream": {
                "root_target": [],
                "mid_target": ["root_target"],
                "leaf_target": ["mid_target", "root_target"],
            },
            "downstream": {
                "root_target": ["mid_target", "leaf_target"],
                "mid_target": ["leaf_target"],
                "leaf_target": [],
            },
        },
    }


def test_dependency_graph_panel_renders_and_emits_locate_callback(self) -> None:
    from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

    located = []
    panel = DependencyGraphPanel(
        _sample_graph_data(),
        {"finish": "#98fb98", "running": "#87ceeb", "failed": "#ffb6c1", "": "#dfe7ef"},
        initial_target="mid_target",
        locate_target_callback=located.append,
    )
    self._app.processEvents()

    self.assertTrue(panel.scene.items())
    panel.select_node("mid_target")
    panel.locate_selected_target_in_tree()
    self._app.processEvents()
    self.assertEqual(["mid_target"], located)


def test_dependency_graph_dialog_wraps_dependency_graph_panel(self) -> None:
    from new_gui.presentation.views.dialogs.dependency_graph import DependencyGraphDialog
    from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

    dialog = DependencyGraphDialog(
        _sample_graph_data(),
        {"finish": "#98fb98", "running": "#87ceeb", "failed": "#ffb6c1", "": "#dfe7ef"},
        initial_target="mid_target",
    )
    self._app.processEvents()

    self.assertIsInstance(dialog.graph_panel, DependencyGraphPanel)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: FAIL because `DependencyGraphPanel` does not exist and `DependencyGraphDialog` does not expose `graph_panel`.

- [ ] **Step 3: Write minimal implementation**

```python
# new_gui/presentation/views/widgets/dependency_graph_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene

from new_gui.presentation.views.dialogs.dependency_graph import DependencyGraphView
from new_gui.presentation.views.dialogs.dependency_graph_export import DependencyGraphExportMixin
from new_gui.presentation.views.dialogs.dependency_graph_rendering import DependencyGraphRenderingMixin
from new_gui.presentation.views.dialogs.dependency_graph_state import DependencyGraphStateMixin


class DependencyGraphPanel(
    DependencyGraphExportMixin,
    DependencyGraphRenderingMixin,
    DependencyGraphStateMixin,
    QWidget,
):
    _LEGEND_STATUS_ORDER = ["finish", "running", "failed", "skip", "scheduled", "pending", ""]

    def __init__(self, graph_data, status_colors, initial_target=None, locate_target_callback=None, parent=None):
        super().__init__(parent)
        self._full_graph_data = graph_data
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.initial_target = initial_target
        self._locate_target_callback = locate_target_callback
        self.node_items = {}
        self.edge_items = []
        self.node_rects = {}
        self.node_texts = {}
        self.node_icons = {}
        self.node_levels = {}
        self.level_lane_items = {}
        self.highlighted_nodes = set()
        self.selected_node = None
        self._node_font = QFont("Arial", 9, QFont.Bold)
        self._node_count = 0
        self._edge_count = 0
        self._level_count = 0
        self._search_matches = []
        self._search_match_index = -1
        self._pending_focus_target = initial_target
        self._scope_mode = "full"
        self._scope_target = None
        self._scope_depth = None
        self.setup_ui()
        self.draw_graph()


# new_gui/presentation/views/dialogs/dependency_graph.py
from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel


class DependencyGraphDialog(QDialog):
    def __init__(self, graph_data, status_colors, initial_target=None, locate_target_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dependency Graph")
        self.resize(920, 980)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graph_panel = DependencyGraphPanel(
            graph_data,
            status_colors,
            initial_target=initial_target,
            locate_target_callback=locate_target_callback,
            parent=self,
        )
        layout.addWidget(self.graph_panel)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: PASS for the new panel-rendering and dialog-wrapper tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_content_graph_tabs.py new_gui/presentation/views/widgets/dependency_graph_panel.py new_gui/presentation/views/dialogs/dependency_graph.py
git commit -m "feat: extract embeddable dependency graph panel"
```

## Task 3: Add Lazy Graph Tab Activation and Sidebar Coordination

**Files:**

- Create: `new_gui/presentation/presenters/content_tab_controller.py`
- Modify: `new_gui/main.py:724-790`
- Modify: `new_gui/presentation/views/builders/top_panel_builder.py:192-223`
- Test: `tests/test_main_content_graph_tabs.py`

- [ ] **Step 1: Write the failing test**

```python
def test_show_dependency_graph_lazily_builds_panel_and_hides_sidebar(self) -> None:
    window = MainWindow()
    window.show()
    self._app.processEvents()

    build_calls = []

    def fake_build_dependency_graph(run_name):
        build_calls.append(run_name)
        return _sample_graph_data()

    window.build_dependency_graph = fake_build_dependency_graph

    self.assertEqual([], build_calls)
    self.assertIsNone(window._dependency_graph_panel)

    window.show_dependency_graph()
    self._app.processEvents()

    self.assertEqual([window.combo.currentText()], build_calls)
    self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)
    self.assertIsNotNone(window._dependency_graph_panel)
    self.assertFalse(window.left_sidebar.isVisible())


def test_returning_to_main_view_restores_sidebar_visibility(self) -> None:
    window = MainWindow()
    window.show()
    self._app.processEvents()

    window.build_dependency_graph = lambda _run_name: _sample_graph_data()
    window.show_dependency_graph()
    self._app.processEvents()

    window.show_main_view_tab()
    self._app.processEvents()

    self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
    self.assertTrue(window.left_sidebar.isVisible())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: FAIL because `show_dependency_graph()` still opens the dialog path and `show_main_view_tab()` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# new_gui/presentation/presenters/content_tab_controller.py
def ensure_dependency_graph_panel(window) -> None:
    if getattr(window, "_dependency_graph_panel", None) is not None:
        return

    graph_data = window.build_dependency_graph(window.combo.currentText())
    initial_target = window._resolve_dependency_graph_initial_target()
    return_context = window._build_dependency_graph_return_context(window.combo.currentText())
    panel = DependencyGraphPanel(
        graph_data,
        window.colors,
        initial_target=initial_target,
        locate_target_callback=lambda target_name, context=return_context: window.locate_target_in_tree(
            target_name,
            context,
        ),
        parent=window._graph_view_page,
    )
    window._graph_view_layout.addWidget(panel)
    window._dependency_graph_panel = panel
    window._dependency_graph_initialized = True
    window._dependency_graph_dirty = False
    window._dependency_graph_return_context = return_context


def activate_dependency_graph_tab(window) -> None:
    ensure_dependency_graph_panel(window)
    window._content_mode_tabs.setCurrentWidget(window._graph_view_page)


def activate_main_view_tab(window) -> None:
    window._content_mode_tabs.setCurrentWidget(window._main_view_page)


def on_content_tab_changed(window, index: int) -> None:
    is_graph = window._content_mode_tabs.widget(index) is window._graph_view_page
    window._active_content_mode = "graph" if is_graph else "main"
    window.left_sidebar.setVisible(not is_graph)


# new_gui/main.py
from new_gui.presentation.presenters import content_tab_controller

def show_dependency_graph(self):
    content_tab_controller.activate_dependency_graph_tab(self)

def show_main_view_tab(self):
    content_tab_controller.activate_main_view_tab(self)

def _on_content_mode_tab_changed(self, index: int) -> None:
    content_tab_controller.on_content_tab_changed(self, index)

def _resolve_dependency_graph_initial_target(self):
    selected_targets = [] if getattr(self, "is_all_status_view", False) else self.get_selected_targets()
    return selected_targets[0] if selected_targets else None


# new_gui/presentation/views/builders/top_panel_builder.py
window._graph_view_layout = QVBoxLayout(window._graph_view_page)
window._graph_view_layout.setContentsMargins(0, 0, 0, 0)
window._graph_view_layout.setSpacing(0)
window._content_mode_tabs.currentChanged.connect(window._on_content_mode_tab_changed)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: PASS for lazy graph creation and sidebar restoration.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_content_graph_tabs.py new_gui/main.py new_gui/presentation/presenters/content_tab_controller.py new_gui/presentation/views/builders/top_panel_builder.py
git commit -m "feat: add lazy dependency graph tab activation"
```

## Task 4: Add Dirty Refresh, Locate-In-Tree Return, and Theme Compatibility

**Files:**

- Modify: `new_gui/main.py:855-1015`
- Modify: `new_gui/model/services/dependency_graph_navigation.py:61-137`
- Modify: `new_gui/presentation/presenters/theme_controller.py:194-325`
- Modify: `new_gui/presentation/presenters/view_controller.py:391-452`
- Modify: `new_gui/presentation/presenters/view_window_bridge.py:1-220`
- Test: `tests/test_main_content_graph_tabs.py`

- [ ] **Step 1: Write the failing test**

```python
def test_marking_graph_dirty_defers_rebuild_until_graph_tab_is_reactivated(self) -> None:
    window = MainWindow()
    window.show()
    self._app.processEvents()

    build_calls = []
    window.build_dependency_graph = lambda _run_name: (build_calls.append("build") or _sample_graph_data())

    window.show_dependency_graph()
    self._app.processEvents()
    self.assertEqual(["build"], build_calls)

    window.show_main_view_tab()
    window._mark_dependency_graph_dirty()
    self._app.processEvents()

    self.assertEqual(["build"], build_calls)

    window.show_dependency_graph()
    self._app.processEvents()

    self.assertEqual(["build", "build"], build_calls)


def test_locate_target_in_tree_switches_back_to_main_view_tab(self) -> None:
    window = MainWindow()
    window.show()
    self._app.processEvents()

    window.build_dependency_graph = lambda _run_name: _sample_graph_data()
    window.show_dependency_graph()
    self._app.processEvents()

    window.combo.blockSignals(True)
    window.combo.clear()
    window.combo.addItem("sample_run")
    window.combo.setCurrentIndex(0)
    window.combo.blockSignals(False)

    selected_targets = []
    window._activate_selected_run_view = lambda *args, **kwargs: None
    window._target_matches_graph_return_context = lambda *args, **kwargs: True
    window._apply_dependency_graph_return_context = lambda *args, **kwargs: None
    window._select_targets_in_tree = lambda names: selected_targets.extend(names)
    window.get_selected_targets = lambda: ["mid_target"]

    window.locate_target_in_tree("mid_target", {"run_name": "sample_run", "restore_plan": {"mode": "main"}})
    self._app.processEvents()

    self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
    self.assertEqual(["mid_target"], selected_targets)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: FAIL because `_mark_dependency_graph_dirty()` does not exist and `locate_target_in_tree()` does not switch the content tab.

- [ ] **Step 3: Write minimal implementation**

```python
# new_gui/main.py
def _mark_dependency_graph_dirty(self) -> None:
    self._dependency_graph_dirty = True


# new_gui/presentation/presenters/content_tab_controller.py
def refresh_dependency_graph_panel(window) -> None:
    if getattr(window, "_dependency_graph_panel", None) is None:
        ensure_dependency_graph_panel(window)
        return

    current_run = window.combo.currentText()
    graph_data = window.build_dependency_graph(current_run)
    initial_target = window._resolve_dependency_graph_initial_target()
    return_context = window._build_dependency_graph_return_context(current_run)
    window._dependency_graph_panel.set_graph_data(
        graph_data,
        initial_target=initial_target,
        locate_target_callback=lambda target_name, context=return_context: window.locate_target_in_tree(
            target_name,
            context,
        ),
    )
    window._dependency_graph_dirty = False
    window._dependency_graph_return_context = return_context


def activate_dependency_graph_tab(window) -> None:
    if getattr(window, "_dependency_graph_panel", None) is None:
        ensure_dependency_graph_panel(window)
    elif bool(getattr(window, "_dependency_graph_dirty", False)):
        refresh_dependency_graph_panel(window)
    window._content_mode_tabs.setCurrentWidget(window._graph_view_page)


# new_gui/presentation/views/widgets/dependency_graph_panel.py
def set_graph_data(self, graph_data, initial_target=None, locate_target_callback=None) -> None:
    self._full_graph_data = graph_data
    self.graph_data = graph_data
    self.initial_target = initial_target
    self._pending_focus_target = initial_target
    self._locate_target_callback = locate_target_callback
    self._scope_mode = "full"
    self._scope_target = None
    self._scope_depth = None
    self._reset_search_state()
    self.draw_graph()


# new_gui/model/services/dependency_graph_navigation.py
# add these lines at the top of locate_target_in_tree()
if hasattr(window, "show_main_view_tab"):
    window.show_main_view_tab()


# new_gui/presentation/presenters/view_controller.py
# add this near the end of activate_selected_run_view(), after run-specific UI refresh completes
if hasattr(window, "_mark_dependency_graph_dirty"):
    window._mark_dependency_graph_dirty()


# new_gui/main.py
def on_run_changed(self):
    view_controller.on_run_changed(self)
    self._mark_dependency_graph_dirty()


# new_gui/presentation/presenters/theme_controller.py
if hasattr(window, "_content_mode_tabs"):
    window._content_mode_tabs.setStyleSheet(style_sheets.build_tab_bar_style(tab_widget_bg, "border: none;"))
if hasattr(window, "_dependency_graph_panel") and window._dependency_graph_panel is not None:
    window._dependency_graph_panel.apply_theme(theme_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: PASS for dirty-flag deferral and graph-to-tree tab return.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_content_graph_tabs.py new_gui/main.py new_gui/model/services/dependency_graph_navigation.py new_gui/presentation/presenters/content_tab_controller.py new_gui/presentation/presenters/theme_controller.py new_gui/presentation/presenters/view_controller.py new_gui/presentation/presenters/view_window_bridge.py new_gui/presentation/views/widgets/dependency_graph_panel.py
git commit -m "feat: wire lazy graph refresh and locate return"
```

## Task 5: Add Smoke Coverage and Final Regression Verification

**Files:**

- Modify: `new_gui/infrastructure/tools/governance_smoke.py:866-952`
- Modify: `tests/test_main_content_graph_tabs.py`
- Test: `tests/test_main_content_graph_tabs.py`
- Test: `new_gui/infrastructure/tools/governance_smoke.py`

- [ ] **Step 1: Write the failing smoke/regression tests**

```python
def test_show_dependency_graph_reuses_existing_panel_until_marked_dirty(self) -> None:
    window = MainWindow()
    window.show()
    self._app.processEvents()

    build_calls = []
    window.build_dependency_graph = lambda _run_name: (build_calls.append("build") or _sample_graph_data())

    window.show_dependency_graph()
    first_panel = window._dependency_graph_panel
    self._app.processEvents()

    window.show_main_view_tab()
    window.show_dependency_graph()
    self._app.processEvents()

    self.assertIs(first_panel, window._dependency_graph_panel)
    self.assertEqual(["build"], build_calls)
```

```python
# new_gui/infrastructure/tools/governance_smoke.py
def smoke_main_content_graph_tabs(window: MainWindow, app: QApplication) -> None:
    window.build_dependency_graph = lambda _run_name: _sample_graph_data()
    _process_events(app)

    _require(window._content_mode_tabs.count() == 2, "Main content tabs were not created.")
    _require(
        window._content_mode_tabs.tabText(1) == "Dependency Graph",
        "Dependency Graph tab label is missing from the main content tabs.",
    )

    window.show_dependency_graph()
    _process_events(app)
    _require(window._dependency_graph_panel is not None, "Dependency Graph panel did not lazy-load.")
    _require(not window.left_sidebar.isVisible(), "Sidebar should hide while the graph tab is active.")

    window.show_main_view_tab()
    _process_events(app)
    _require(window.left_sidebar.isVisible(), "Sidebar did not restore after returning to Main View.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: FAIL because panel reuse semantics and governance smoke helper are not implemented yet.

Run: `QT_QPA_PLATFORM=offscreen python3 -m new_gui.infrastructure.tools.governance_smoke`

Expected: FAIL with a missing smoke helper or assertion failure because the graph tab is not covered by smoke yet.

- [ ] **Step 3: Write minimal implementation**

```python
# new_gui/presentation/presenters/content_tab_controller.py
def activate_dependency_graph_tab(window) -> None:
    if getattr(window, "_dependency_graph_panel", None) is None:
        ensure_dependency_graph_panel(window)
    elif bool(getattr(window, "_dependency_graph_dirty", False)):
        refresh_dependency_graph_panel(window)
    window._content_mode_tabs.setCurrentWidget(window._graph_view_page)


# new_gui/infrastructure/tools/governance_smoke.py
def main() -> int:
    smoke_dependency_graph_dialog(app)
    graph_window = MainWindow()
    graph_window.show()
    _process_events(app)
    smoke_main_content_graph_tabs(graph_window, app)
    if hasattr(graph_window, "_remove_gui_log_handler"):
        graph_window._remove_gui_log_handler()
    if hasattr(graph_window, "_executor"):
        graph_window._executor.shutdown(wait=False)
    graph_window.close()
    graph_window.deleteLater()
    smoke_action_flow_policy()
```

- [ ] **Step 4: Run full verification**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`

Expected: PASS for all new graph-tab regression tests.

Run: `QT_QPA_PLATFORM=offscreen python3 -m new_gui.infrastructure.tools.governance_smoke`

Expected: PASS with `Governance smoke passed.`

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_repo_layout -v`

Expected: PASS, confirming repo-level layout still works.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_content_graph_tabs.py new_gui/infrastructure/tools/governance_smoke.py
git commit -m "test: cover main view dependency graph tabs"
```

## Self-Review

### Spec coverage

- Persistent `Main View` and `Dependency Graph` tabs: Tasks 1 and 3
- Graph lazy loading and lazy refresh: Tasks 3 and 4
- Shared run/theme/status/selected-target context only: Tasks 3 and 4
- No `TreeView` filter inheritance: Task 4 keeps graph refresh driven by run and selected target only
- Sidebar hidden or disabled during graph view: Task 3
- `Ctrl+G` and menu path activate graph tab instead of dialog: Task 3 changes `show_dependency_graph()` semantics without touching the callers
- `Locate In Tree` returns from graph to tree: Task 4
- Smoke and regression coverage: Task 5

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” markers remain
- Every code-changing step includes concrete code
- Every test step includes an exact command and expected result

### Type and naming consistency

- `window._content_mode_tabs`, `window._main_view_page`, `window._graph_view_page`
- `window._dependency_graph_panel`, `window._dependency_graph_dirty`, `window._mark_dependency_graph_dirty()`
- `DependencyGraphPanel.set_graph_data(...)`
- `content_tab_controller.activate_dependency_graph_tab(...)`
- `window.show_main_view_tab()`

Those names are used consistently across all tasks and should not be renamed during execution without updating every later task.
