import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QStyleOptionViewItem, QTreeView

from new_gui.main import MainWindow
from new_gui.model.services import tree_rows
from new_gui.model.services import view_layout
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_tabs
from new_gui.presentation.presenters.content_tab_controller import _apply_category_scope_to_graph_data


def _sample_graph_data():
    return {
        "nodes": [
            ("root_target", "finish"),
            ("mid_target", "running"),
            ("leaf_target", "failed"),
        ],
        "edges": [
            ("root_target", "mid_target"),
            ("mid_target", "leaf_target"),
        ],
        "levels": {
            0: ["root_target"],
            1: ["mid_target"],
            2: ["leaf_target"],
        },
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


def _graph_data_for_run(run_name: str):
    target_name = f"{run_name}_target"
    return {
        "nodes": [(target_name, "finish")],
        "edges": [],
        "levels": {0: [target_name]},
        "trace_targets": {
            "upstream": {target_name: []},
            "downstream": {target_name: []},
        },
        "node_meta": {
            target_name: {
                "display_name": target_name,
                "kind": "target",
                "members": [target_name],
                "representative_target": target_name,
                "status_text": "finish",
            }
        },
        "target_to_node": {target_name: target_name},
    }


class MainContentGraphTabsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    @staticmethod
    def _force_sample_run(window, run_name: str = "sample_run") -> None:
        window.combo.blockSignals(True)
        window.combo.clear()
        window.combo.addItem(run_name)
        window.combo.setCurrentIndex(0)
        window.combo.blockSignals(False)
        window.combo_sel = f"/tmp/{run_name}"

    @staticmethod
    def _visible_tree_targets(window) -> list[str]:
        visible_targets = []

        def walk(parent_item=None, parent_index=QModelIndex()) -> None:
            row_count = parent_item.rowCount() if parent_item is not None else window.model.rowCount()
            for row in range(row_count):
                if window.tree.isRowHidden(row, parent_index):
                    continue
                row_items = tree_rows.get_row_items(window.model, row, parent_item)
                level_item = row_items[0] if row_items else None
                target_item = row_items[1] if len(row_items) > 1 else None
                target_name = tree_rows.get_row_target_name(target_item)
                if target_name:
                    visible_targets.append(target_name)
                if level_item is not None and level_item.hasChildren():
                    walk(level_item, level_item.index())

        walk()
        return visible_targets

    def test_main_window_builds_content_mode_tab_shell_with_main_page_active(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        self.assertTrue(hasattr(window, "_content_mode_tabs"))
        self.assertEqual(2, window._content_mode_tabs.count())
        self.assertEqual("TreeView", window._content_mode_tabs.tabText(0))
        self.assertEqual("Dependency Graph", window._content_mode_tabs.tabText(1))
        self.assertEqual("main", window._active_content_mode)
        self.assertTrue(window._dependency_graph_dirty)
        self.assertFalse(window._dependency_graph_initialized)
        self.assertEqual({}, window._dependency_graph_return_context)
        self.assertIs(window._main_view_page, window._content_mode_tabs.currentWidget())
        self.assertIs(window._main_view_page, window._content_mode_tabs.widget(0))
        self.assertIs(window._graph_view_page, window._content_mode_tabs.widget(1))
        self.assertIs(window._main_view_page, window._content_splitter.parentWidget())
        self.assertIsNone(window._dependency_graph_panel)
        self.assertTrue(window.left_sidebar.isVisible())
        self.assertTrue(hasattr(window, "dependency_graph_toggle"))
        self.assertFalse(window.dependency_graph_toggle.isChecked())

    def test_startup_window_width_preserves_default_target_column_with_sidebar_visible(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        default_target_width = window._get_main_view_default_column_widths()[1]

        self.assertTrue(window.left_sidebar.isVisible())
        self.assertGreaterEqual(window.tree.columnWidth(1), default_target_width)

    def test_startup_time_columns_keep_full_timestamp_width_when_sidebar_is_visible(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        probe_tree = QTreeView()
        probe_tree.setFont(window.tree.font())
        probe_tree.setStyleSheet(window.tree.styleSheet())
        probe_model = QStandardItemModel(1, 1, probe_tree)
        probe_model.setItem(0, 0, QStandardItem(view_layout.MAIN_TREE_TIME_FORMAT_SAMPLE))
        probe_tree.setModel(probe_model)

        probe_option = QStyleOptionViewItem()
        probe_option.initFrom(probe_tree)
        expected_width = probe_tree.itemDelegate().sizeHint(
            probe_option,
            probe_model.index(0, 0),
        ).width()

        self.assertTrue(window.left_sidebar.isVisible())
        self.assertGreaterEqual(window.tree.columnWidth(4), expected_width)
        self.assertGreaterEqual(window.tree.columnWidth(5), expected_width)

    def test_graph_tab_is_present_but_disabled_in_task1_shell(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        self.assertEqual(0, window._content_mode_tabs.currentIndex())
        self.assertTrue(window._content_mode_tabs.isTabEnabled(1))
        self.assertEqual("main", window._active_content_mode)
        self.assertIs(window._main_view_page, window._content_mode_tabs.currentWidget())

    def test_dependency_graph_panel_renders_and_emits_locate_callback(self) -> None:
        from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

        located = []
        panel = DependencyGraphPanel(
            _sample_graph_data(),
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="mid_target",
            locate_target_callback=located.append,
        )

        self._app.processEvents()

        self.assertTrue(panel.scene.items())

        panel.select_node("mid_target")
        panel.locate_selected_target_in_tree()
        self._app.processEvents()

        self.assertEqual(["mid_target"], located)

    def test_empty_sidebar_category_scope_returns_empty_dependency_graph(self) -> None:
        filtered_graph = _apply_category_scope_to_graph_data(_sample_graph_data(), set())

        self.assertEqual([], filtered_graph["nodes"])
        self.assertEqual([], filtered_graph["edges"])
        self.assertEqual({}, filtered_graph["levels"])

    def test_dependency_graph_panel_skips_redraw_when_graph_data_is_unchanged(self) -> None:
        from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

        panel = DependencyGraphPanel(
            _sample_graph_data(),
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="mid_target",
        )
        self._app.processEvents()

        draw_calls = []
        original_draw_graph = panel.draw_graph

        def counted_draw_graph():
            draw_calls.append("draw")
            original_draw_graph()

        panel.draw_graph = counted_draw_graph

        located = []
        locate_callback = located.append
        panel.set_graph_data(
            _sample_graph_data(),
            initial_target="leaf_target",
            locate_target_callback=locate_callback,
            preserve_viewport=True,
        )
        self._app.processEvents()

        self.assertEqual([], draw_calls)
        self.assertEqual("leaf_target", panel.initial_target)
        self.assertIs(panel._locate_target_callback, locate_callback)

    def test_dependency_graph_panel_same_data_resets_local_scope(self) -> None:
        from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

        panel = DependencyGraphPanel(
            _sample_graph_data(),
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="mid_target",
        )
        self._app.processEvents()
        panel.select_node("mid_target")
        panel.show_local_subgraph()
        self._app.processEvents()

        draw_calls = []
        original_draw_graph = panel.draw_graph

        def counted_draw_graph():
            draw_calls.append("draw")
            original_draw_graph()

        panel.draw_graph = counted_draw_graph

        panel.set_graph_data(
            _sample_graph_data(),
            initial_target="leaf_target",
            preserve_viewport=True,
        )
        self._app.processEvents()

        self.assertEqual(["draw"], draw_calls)
        self.assertEqual("full", panel._scope_mode)
        self.assertEqual(_sample_graph_data(), panel.graph_data)

    def test_graph_trace_uses_canonical_trace_targets_across_level_gaps(self) -> None:
        from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

        graph_data = {
            "nodes": [
                ("root_target", "finish"),
                ("mid_target", "running"),
                ("leaf_target", "failed"),
            ],
            "edges": [
                ("root_target", "leaf_target"),
            ],
            "levels": {
                0: ["root_target"],
                1: ["mid_target"],
                2: ["leaf_target"],
            },
            "trace_targets": {
                "upstream": {
                    "root_target": [],
                    "mid_target": [],
                    "leaf_target": ["root_target"],
                },
                "downstream": {
                    "root_target": ["leaf_target"],
                    "mid_target": [],
                    "leaf_target": [],
                },
            },
        }
        panel = DependencyGraphPanel(
            graph_data,
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="root_target",
        )
        self._app.processEvents()

        panel.select_node("root_target")
        panel.highlight_downstream()

        self.assertEqual({"root_target", "leaf_target"}, panel.highlighted_nodes)

        panel.select_node("leaf_target")
        panel.highlight_upstream()

        self.assertEqual({"root_target", "leaf_target"}, panel.highlighted_nodes)

    def test_dependency_graph_dialog_wraps_dependency_graph_panel(self) -> None:
        from new_gui.presentation.views.dialogs.dependency_graph import DependencyGraphDialog
        from new_gui.presentation.views.widgets.dependency_graph_panel import DependencyGraphPanel

        dialog = DependencyGraphDialog(
            _sample_graph_data(),
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="mid_target",
        )

        self.assertIsInstance(dialog.graph_panel, DependencyGraphPanel)

    def test_dependency_graph_dialog_preserves_legacy_graph_surface(self) -> None:
        from new_gui.presentation.views.dialogs.dependency_graph import DependencyGraphDialog

        located = []
        dialog = DependencyGraphDialog(
            _sample_graph_data(),
            {
                "finish": "#98fb98",
                "running": "#87ceeb",
                "failed": "#ffb6c1",
                "": "#dfe7ef",
            },
            initial_target="mid_target",
            locate_target_callback=located.append,
        )

        self._app.processEvents()

        self.assertTrue(dialog.scene.items())

        dialog.select_node("mid_target")
        self.assertEqual("mid_target", dialog.selected_node)

        dialog.show_local_subgraph()
        self._app.processEvents()
        self.assertEqual("local", dialog._scope_mode)

        dialog._search_input.setText("leaf")
        self._app.processEvents()
        dialog.find_next_target()
        self.assertEqual("leaf_target", dialog.selected_node)

        dialog.selected_node = "mid_target"
        dialog.locate_selected_target_in_tree()
        self._app.processEvents()

        self.assertEqual(["mid_target"], located)

    def test_show_dependency_graph_lazily_builds_panel_and_hides_sidebar(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

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
        self.assertTrue(window.left_sidebar.isVisible())
        self.assertTrue(window.dependency_graph_toggle.isChecked())

    def test_toggling_dependency_graph_switch_activates_graph_page(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertIsNone(window._dependency_graph_panel)

        window.dependency_graph_toggle.setChecked(True)
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)
        self.assertIsNotNone(window._dependency_graph_panel)
        self.assertTrue(window.dependency_graph_toggle.isChecked())

    def test_turning_off_dependency_graph_switch_returns_main_view(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.dependency_graph_toggle.setChecked(True)
        self._app.processEvents()
        self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)

        window.dependency_graph_toggle.setChecked(False)
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertTrue(window.left_sidebar.isVisible())

    def test_dependency_graph_switch_uses_full_slider_hit_area(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        toggle = window.dependency_graph_toggle
        self.assertTrue(toggle.hitButton(QPoint(0, 0)))
        self.assertTrue(toggle.hitButton(QPoint(toggle.width() - 1, toggle.height() - 1)))

    def test_dependency_graph_label_turns_blue_when_switch_enabled(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.dependency_graph_toggle.setChecked(True)
        self._app.processEvents()
        self.assertIn("#2f7adf", window._dependency_graph_toggle_label.styleSheet())

        window.dependency_graph_toggle.setChecked(False)
        self._app.processEvents()
        self.assertIn("#51697f", window._dependency_graph_toggle_label.styleSheet())

    def test_graph_mode_hides_internal_graph_vertical_scrollbar(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()

        window.dependency_graph_toggle.setChecked(True)
        self._app.processEvents()

        self.assertIsNotNone(window._dependency_graph_panel)
        self.assertEqual(
            Qt.ScrollBarAlwaysOff,
            window._dependency_graph_panel.view.verticalScrollBarPolicy(),
        )

    def test_graph_mode_hides_only_internal_graph_controls(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()

        self.assertTrue(window._top_button_container.isVisible())
        self.assertTrue(window._status_bar.isVisible())

        window.show_dependency_graph()
        self._app.processEvents()

        panel = window._dependency_graph_panel
        self.assertIsNotNone(panel)
        self.assertTrue(window._top_button_container.isVisible())
        self.assertTrue(window._status_bar.isVisible())
        self.assertFalse(panel._auxiliary_controls_container.isVisible())

        window.show_main_view_tab()
        self._app.processEvents()

        self.assertTrue(window._top_button_container.isVisible())
        self.assertTrue(window._status_bar.isVisible())

    def test_returning_to_main_view_restores_sidebar_visibility(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        window.show_main_view_tab()
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertTrue(window.left_sidebar.isVisible())

    def test_sidebar_category_change_rebuilds_graph_in_graph_mode(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        build_calls = []
        window.build_dependency_graph = lambda _run_name: (build_calls.append("build") or _sample_graph_data())
        window.combo_sel = "/tmp/sample_run"

        window.show_dependency_graph()
        self._app.processEvents()
        self.assertEqual(["build"], build_calls)

        window._apply_sidebar_category_filter_in_place = lambda: True
        window.on_left_sidebar_category_changed("stage", "dummy_category")
        self._app.processEvents()

        self.assertEqual(["build", "build"], build_calls)
        self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)

    def test_marking_graph_dirty_defers_rebuild_until_graph_tab_is_reactivated(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

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

    def test_run_change_rebuilds_graph_panel_when_graph_mode_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for run_name in ("run_a", "run_b"):
                run_dir = os.path.join(tmp_dir, run_name)
                os.makedirs(run_dir, exist_ok=True)
                with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                    handle.write("")

            window = MainWindow()
            window.show()
            self._app.processEvents()

            window.run_base_dir = tmp_dir
            window.combo.blockSignals(True)
            window.combo.clear()
            window.combo.addItems(["run_a", "run_b"])
            window.combo.setCurrentIndex(0)
            window.combo.blockSignals(False)
            window.combo_sel = os.path.join(tmp_dir, "run_a")

            window.refresh_left_sidebar_categories = lambda run_dir=None: None
            window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
            window._build_status_cache = lambda run_name: None
            window.populate_data = lambda force_rebuild=False: None
            window._apply_main_tree_column_visibility = lambda visible_columns, save_state=False: None
            window.update_status_bar = lambda: None
            window.setup_status_watcher = lambda: None
            window.setup_tune_watcher = lambda: None
            dependency_setup_calls = []
            window.setup_dependency_watcher = lambda: dependency_setup_calls.append(window.combo_sel)
            window.build_dependency_graph = lambda run_name: _graph_data_for_run(run_name)

            window.show_dependency_graph()
            self._app.processEvents()

            self.assertEqual([("run_a_target", "finish")], window._dependency_graph_panel.graph_data["nodes"])
            self.assertEqual("Dependency Graph", window.tab_label.text())

            window.combo.setCurrentIndex(1)
            self._app.processEvents()

            self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)
            self.assertEqual("Dependency Graph", window.tab_label.text())
            self.assertEqual([("run_b_target", "finish")], window._dependency_graph_panel.graph_data["nodes"])
            self.assertIn(os.path.join(tmp_dir, "run_b"), dependency_setup_calls)

    def test_run_change_clears_graph_category_overlay_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for run_name in ("run_a", "run_b"):
                run_dir = os.path.join(tmp_dir, run_name)
                os.makedirs(run_dir, exist_ok=True)
                with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                    handle.write("")

            window = MainWindow()
            window.show()
            self._app.processEvents()

            window.run_base_dir = tmp_dir
            window.combo.blockSignals(True)
            window.combo.clear()
            window.combo.addItems(["run_a", "run_b"])
            window.combo.setCurrentIndex(0)
            window.combo.blockSignals(False)
            window.combo_sel = os.path.join(tmp_dir, "run_a")

            window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
            window._build_status_cache = lambda run_name: None
            window.populate_data = lambda force_rebuild=False: None
            window._apply_main_tree_column_visibility = lambda visible_columns, save_state=False: None
            window.update_status_bar = lambda: None
            window.setup_status_watcher = lambda: None
            window.setup_tune_watcher = lambda: None
            window.build_dependency_graph = lambda run_name: _graph_data_for_run(run_name)
            window._apply_sidebar_category_filter_in_place = lambda: True

            def refresh_left_sidebar_categories(run_dir=None):
                del run_dir
                window._stage_categories = []
                window._type_categories = []
                window.left_sidebar.set_stage_categories([])
                window.left_sidebar.set_type_categories([])
                window._selected_stage_category_id = window.left_sidebar.selected_category_id("stage")
                window._selected_type_category_id = window.left_sidebar.selected_category_id("type")

            window.refresh_left_sidebar_categories = refresh_left_sidebar_categories

            stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["run_a_target"]}]
            window.left_sidebar.set_stage_categories(stage_categories)
            window._stage_categories = list(stage_categories)
            self._app.processEvents()

            window.show_dependency_graph()
            self._app.processEvents()
            window.left_sidebar._category_buttons[0].click()
            self._app.processEvents()

            window.combo.setCurrentIndex(1)
            window.on_run_changed()
            self._app.processEvents()

            self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)
            self.assertEqual("Dependency Graph", window.tab_label.text())
            self.assertFalse(view_mode_state.is_category_overlay_active(window))
            self.assertEqual("", window.left_sidebar.selected_category_id("stage"))
            self.assertEqual(
                {
                    "mode": "main",
                    "scroll": 0,
                },
                window._dependency_graph_return_context.get("restore_plan"),
            )

    def test_show_all_status_from_graph_mode_switches_back_to_main_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            window = MainWindow()
            window.show()
            self._app.processEvents()
            self._force_sample_run(window)
            window.run_base_dir = tmp_dir
            window.build_dependency_graph = lambda _run_name: _sample_graph_data()

            window.show_dependency_graph()
            self._app.processEvents()

            self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)
            self.assertEqual("graph", window._active_content_mode)

            window.show_all_status()
            self._app.processEvents()

            self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
            self.assertEqual("main", window._active_content_mode)
            self.assertTrue(window.is_all_status_view)
            self.assertEqual("All Status Overview", window.tab_label.text())

    def test_missing_run_in_graph_mode_returns_to_main_content_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "run_a")
            os.makedirs(run_dir, exist_ok=True)
            with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                handle.write("")

            window = MainWindow()
            window.show()
            self._app.processEvents()
            window.run_base_dir = tmp_dir
            window.combo.blockSignals(True)
            window.combo.clear()
            window.combo.addItem("run_a")
            window.combo.setCurrentIndex(0)
            window.combo.blockSignals(False)
            window.combo_sel = run_dir

            window.refresh_left_sidebar_categories = lambda run_dir=None: None
            window.refresh_xmeta_background = lambda run_dir=None, announce=False: None
            window._build_status_cache = lambda run_name: None
            window.populate_data = lambda force_rebuild=False: None
            window._apply_main_tree_column_visibility = lambda visible_columns, save_state=False: None
            window.update_status_bar = lambda: None
            window.setup_status_watcher = lambda: None
            window.setup_tune_watcher = lambda: None
            window.build_dependency_graph = lambda run_name: _graph_data_for_run(run_name)

            window.show_dependency_graph()
            self._app.processEvents()
            self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)

            os.remove(os.path.join(run_dir, ".target_dependency.csh"))
            os.rmdir(run_dir)
            window.refresh_available_runs()
            self._app.processEvents()

            self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
            self.assertEqual("main", window._active_content_mode)
            self.assertEqual("TreeView", window.tab_label.text())
            self.assertEqual({}, window._dependency_graph_return_context)

    def test_restore_plan_uses_explicit_status_state_even_if_tab_label_drifts(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        view_mode_state.set_tree_mode_status(window, "running")
        window.tab_label.setText("Main View")

        restore_plan = window._build_current_view_restore_plan(23)

        self.assertEqual(
            {
                "mode": "status",
                "status": "running",
                "scroll": 23,
            },
            restore_plan,
        )

    def test_status_badge_filter_from_graph_mode_routes_back_to_main_view_before_filtering(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        filter_calls = []

        def record_status_filter(status, update_tab=True):
            filter_calls.append(
                (
                    status,
                    update_tab,
                    window._content_mode_tabs.currentWidget(),
                    window._active_content_mode,
                )
            )

        window._apply_status_filter = record_status_filter

        window.on_status_badge_double_clicked("running")
        self._app.processEvents()

        self.assertEqual(
            [("running", True, window._main_view_page, "main")],
            filter_calls,
        )

    def test_graph_return_context_search_matching_respects_regex_options(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()

        return_context = {
            "run_name": "sample_run",
            "is_all_status_view": False,
            "restore_plan": {
                "mode": "search",
                "search_text": "mid_.*",
                "search_options": {
                    "case_sensitive": False,
                    "whole_word": False,
                    "regex": True,
                },
            },
        }

        self.assertTrue(
            window._target_matches_graph_return_context("mid_target", "sample_run", return_context)
        )

    def test_close_tree_view_uses_explicit_trace_mode_even_if_tab_label_drifts(self) -> None:
        class _FakeScrollBar:
            def __init__(self, initial_value: int):
                self._value = initial_value

            def value(self) -> int:
                return self._value

            def setValue(self, value: int) -> None:
                self._value = int(value)

        window = MainWindow()
        window.show()
        self._app.processEvents()

        fake_scrollbar = _FakeScrollBar(41)
        window.tree.verticalScrollBar = lambda: fake_scrollbar
        view_mode_state.set_tree_mode_trace(window, "mid_target", "in")
        window._trace_return_scroll_value = 137
        window.tab_label.setText("Main View")

        populate_calls = []
        window.populate_data = lambda force_rebuild=False: populate_calls.append(force_rebuild)

        window.close_tree_view()
        self._app.processEvents()

        self.assertEqual([True], populate_calls)
        self.assertEqual(137, fake_scrollbar.value())
        self.assertEqual("TreeView", window.tab_label.text())

    def test_category_close_restores_previous_status_restore_plan(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        view_mode_state.set_tree_mode_status(window, "running")
        window._apply_tab_state(view_tabs.get_status_tab_state("running"))
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window._stage_categories = list(stage_categories)
        window.left_sidebar.set_stage_categories(stage_categories)
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        self._app.processEvents()

        restore_calls = []
        window.show_full_target_view = lambda force_rebuild=False: restore_calls.append(("show_full", force_rebuild))
        window._restore_view_from_plan = lambda plan: restore_calls.append(("restore_plan", dict(plan))) or plan.get("mode", "")

        category_button = window.left_sidebar._category_buttons[0]
        category_button.click()
        self._app.processEvents()

        window.close_tree_view()
        self._app.processEvents()

        self.assertIn(("show_full", False), restore_calls)
        self.assertIn(
            (
                "restore_plan",
                {
                    "mode": "status",
                    "status": "running",
                    "scroll": 0,
                },
            ),
            restore_calls,
        )

    def test_locate_target_in_tree_switches_back_to_main_view_tab(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

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

    def test_locate_target_in_tree_restores_category_tab_state_from_graph_context(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None

        selected_targets = []
        window._select_targets_in_tree = lambda names: selected_targets.extend(names)

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        category_button = window.left_sidebar._category_buttons[0]
        category_button.click()
        self._app.processEvents()

        self.assertEqual("Category: STAGE / Stage Alpha", window.tab_label.text())

        window.show_dependency_graph()
        self._app.processEvents()
        window.locate_target_in_tree("mid_target", window._dependency_graph_return_context)
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertEqual("Category: STAGE / Stage Alpha", window.tab_label.text())
        self.assertEqual("stage_a", window.left_sidebar.selected_category_id("stage"))
        self.assertEqual(["mid_target"], selected_targets)

    def test_show_dependency_graph_reuses_existing_panel_until_marked_dirty(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

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

    def test_graph_selected_node_supplies_action_targets_for_top_buttons(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        panel = window._dependency_graph_panel
        panel.select_node("mid_target")
        self._app.processEvents()

        self.assertEqual(["mid_target"], window.get_selected_targets())
        self.assertEqual(["mid_target"], window.get_selected_action_targets())

    def test_graph_mode_action_target_falls_back_from_synthetic_group_id(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        panel = window._dependency_graph_panel
        panel.selected_node = "__group__sample"
        panel._node_members = lambda _node: ["__group__sample"]
        panel._node_representative_target = lambda _node: "leaf_target"

        self.assertEqual(["leaf_target"], window.get_selected_targets())
        self.assertEqual(["leaf_target"], window.get_selected_action_targets())

    def test_main_window_selection_uses_graph_panel_public_api(self) -> None:
        class PublicOnlyGraphPanel:
            selected_node = "__group__sample"

            def selected_display_target(self):
                return "leaf_target"

            def selected_action_targets(self):
                return ["alpha_target", "beta_target"]

        window = type("Window", (), {})()
        window._active_content_mode = "graph"
        window._dependency_graph_panel = PublicOnlyGraphPanel()
        window.tree = None
        window.model = None

        self.assertEqual(["leaf_target"], MainWindow.get_selected_targets(window))
        self.assertEqual(
            ["alpha_target", "beta_target"],
            MainWindow.get_selected_action_targets(window),
        )

    def test_graph_mode_reuses_top_tab_and_restores_main_label_after_switch_back(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()

        window._apply_tab_state({"text": "Status: running", "style": "color: #334455;", "show_close_button": True})
        self._app.processEvents()
        self.assertEqual("Status: running", window.tab_label.text())
        self.assertTrue(window.tab_close_btn.isVisible())

        window.show_dependency_graph()
        self._app.processEvents()
        self.assertEqual("Dependency Graph", window.tab_label.text())
        self.assertFalse(window.tab_close_btn.isVisible())

        window.show_main_view_tab()
        self._app.processEvents()
        self.assertEqual("Status: running", window.tab_label.text())
        self.assertTrue(window.tab_close_btn.isVisible())

    def test_graph_mode_top_tab_click_and_double_click_target_graph_panel(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        panel = window._dependency_graph_panel
        self.assertIsNotNone(panel)

        fit_calls = []
        original_fit_view = panel.fit_view

        def recording_fit_view():
            fit_calls.append("fit")
            original_fit_view()

        panel.fit_view = recording_fit_view
        window.tab_label.clicked.emit()
        self._app.processEvents()
        self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)

        window.tab_label.doubleClicked.emit()
        self._app.processEvents()
        self.assertEqual(["fit"], fit_calls)

    def test_header_filter_editor_stays_attached_to_header_viewport_and_accepts_typing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "sample_run")
            os.makedirs(run_dir, exist_ok=True)
            with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha beta gamma"\\n')

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

            header_rect = window.header._section_content_rect(window.header.filter_column)
            QTest.mouseDClick(window.header.viewport(), Qt.LeftButton, pos=header_rect.center())
            self._app.processEvents()

            filter_edit = window.header.filter_edit
            self.assertIsNotNone(filter_edit)
            self.assertIs(filter_edit.parentWidget(), window.header.viewport())
            self.assertTrue(filter_edit.isVisible())
            self.assertTrue(filter_edit.hasFocus())

            QTest.keyClicks(filter_edit, "alpha")
            self._app.processEvents()
            self.assertEqual("alpha", filter_edit.text())
            self.assertEqual("alpha", window.header.get_filter_text())

            QTest.keyClick(filter_edit, Qt.Key_Backspace)
            self._app.processEvents()
            self.assertEqual("alph", filter_edit.text())
            self.assertEqual("alph", window.header.get_filter_text())

            QTest.keyClick(filter_edit, Qt.Key_Escape)
            self._app.processEvents()
            self.assertFalse(filter_edit.isVisible())
            self.assertFalse(window.header._filter_visible)

    def test_retrace_actions_route_to_graph_panel_in_graph_mode(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window.show_dependency_graph()
        self._app.processEvents()

        panel = window._dependency_graph_panel
        self.assertIsNotNone(panel)

        trace_calls = []

        def record_upstream():
            trace_calls.append("up")

        def record_downstream():
            trace_calls.append("down")

        panel.highlight_upstream = record_upstream
        panel.highlight_downstream = record_downstream

        window.retrace_tab("in")
        window.retrace_tab("out")
        self._app.processEvents()

        self.assertEqual(["up", "down"], trace_calls)

    def test_closing_trace_view_restores_pre_trace_main_scroll_position(self) -> None:
        class _FakeScrollBar:
            def __init__(self, initial_value: int):
                self._value = initial_value

            def value(self) -> int:
                return self._value

            def setValue(self, value: int) -> None:
                self._value = int(value)

        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)

        fake_scrollbar = _FakeScrollBar(137)
        window.tree.verticalScrollBar = lambda: fake_scrollbar
        window.get_selected_targets = lambda: ["mid_target"]
        window.get_retrace_target = lambda target, direction: ["root_target"]
        window.filter_tree_by_targets = lambda targets_to_show: None

        window.retrace_tab("in")
        self._app.processEvents()

        self.assertTrue(window.tab_label.text().startswith("Trace Up:"))

        window.populate_data = lambda force_rebuild=False: fake_scrollbar.setValue(0)
        window.close_tree_view()
        self._app.processEvents()

        self.assertEqual("TreeView", window.tab_label.text())
        self.assertEqual(137, fake_scrollbar.value())

    def test_stage_category_selection_sets_closable_category_tab_in_main_mode(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_full_target_view = lambda force_rebuild=False: window._set_main_run_tab_state()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        category_button = window.left_sidebar._category_buttons[0]
        category_button.click()
        self._app.processEvents()

        self.assertTrue(window.tab_label.text().startswith("Category: STAGE / Stage Alpha"))
        self.assertTrue(window.tab_close_btn.isVisible())

        window.close_tree_view()
        self._app.processEvents()

        self.assertEqual("TreeView", window.tab_label.text())
        self.assertFalse(window.tab_close_btn.isVisible())

    def test_closing_stage_category_restores_full_tree_targets_in_main_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = os.path.join(tmp_dir, "sample_run")
            os.makedirs(run_dir, exist_ok=True)
            with open(os.path.join(run_dir, ".target_dependency.csh"), "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "first_target second_target"\\n')

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

            self.assertEqual(
                ["first_target", "second_target"],
                self._visible_tree_targets(window),
            )

            stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["first_target"]}]
            window.left_sidebar.set_stage_categories(stage_categories)
            window._stage_categories = list(stage_categories)
            self._app.processEvents()
            window.left_sidebar._category_buttons[0].click()
            self._app.processEvents()

            self.assertEqual(["first_target"], self._visible_tree_targets(window))

            window.tab_close_btn.click()
            self._app.processEvents()

            self.assertEqual(
                ["first_target", "second_target"],
                self._visible_tree_targets(window),
            )
            self.assertEqual("TreeView", window.tab_label.text())
            self.assertFalse(view_mode_state.is_category_overlay_active(window))

    def test_stage_category_selection_supports_close_to_rollback_in_graph_mode(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_dependency_graph()
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        category_button = window.left_sidebar._category_buttons[0]
        category_button.click()
        self._app.processEvents()

        self.assertTrue(window.tab_label.text().startswith("Category: STAGE / Stage Alpha"))
        self.assertTrue(window.tab_close_btn.isVisible())

        window.close_tree_view()
        self._app.processEvents()

        self.assertEqual("Dependency Graph", window.tab_label.text())
        self.assertFalse(window.tab_close_btn.isVisible())
        self.assertIs(window._content_mode_tabs.currentWidget(), window._graph_view_page)

    def test_switching_from_graph_category_overlay_to_main_preserves_category_tab_state(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_dependency_graph()
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        window.left_sidebar._category_buttons[0].click()
        self._app.processEvents()

        window.show_main_view_tab()
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertTrue(window.tab_label.text().startswith("Category: STAGE / Stage Alpha"))
        self.assertTrue(window.tab_close_btn.isVisible())
        self.assertTrue(view_mode_state.is_category_overlay_active(window))

    def test_closing_graph_originated_category_overlay_after_switching_to_main_stays_in_main_view(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_dependency_graph()
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        window.left_sidebar._category_buttons[0].click()
        self._app.processEvents()

        window.show_main_view_tab()
        self._app.processEvents()
        window.close_tree_view()
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertEqual("main", window._active_content_mode)
        self.assertEqual("TreeView", window.tab_label.text())
        self.assertFalse(view_mode_state.is_category_overlay_active(window))

    def test_category_close_uses_visible_main_view_even_if_content_state_drifts(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None

        window.show_dependency_graph()
        self._app.processEvents()
        window.show_main_view_tab()
        self._app.processEvents()
        view_mode_state.set_content_mode(window, "graph")

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        window.left_sidebar._category_buttons[0].click()
        self._app.processEvents()

        window.tab_close_btn.click()
        self._app.processEvents()

        self.assertIs(window._content_mode_tabs.currentWidget(), window._main_view_page)
        self.assertEqual("main", window._active_content_mode)
        self.assertEqual("TreeView", window.tab_label.text())
        self.assertFalse(view_mode_state.is_category_overlay_active(window))

    def test_hiding_sidebar_clears_graph_category_overlay_state(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window.build_dependency_graph = lambda _run_name: _sample_graph_data()
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_dependency_graph()
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        window.left_sidebar._category_buttons[0].click()
        self._app.processEvents()

        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        self.assertFalse(view_mode_state.is_category_overlay_active(window))
        self.assertEqual("Dependency Graph", window.tab_label.text())
        self.assertEqual("", window.left_sidebar.selected_category_id("stage"))

    def test_category_close_restores_previous_status_tab_state(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._force_sample_run(window)
        window._apply_sidebar_category_filter_in_place = lambda: True
        window.populate_data = lambda force_rebuild=False: None
        window.show_full_target_view = lambda force_rebuild=False: None

        previous_state = {"text": "Status: running", "style": "color: #334455;", "show_close_button": True}
        view_mode_state.set_tree_mode_status(window, "running")
        window._apply_tab_state(previous_state)
        window._restore_view_from_plan = lambda plan: window._apply_tab_state(previous_state) or plan.get("mode", "")
        self._app.processEvents()

        stage_categories = [{"id": "stage_a", "label": "Stage Alpha", "targets": ["mid_target"]}]
        window.left_sidebar.set_stage_categories(stage_categories)
        window._stage_categories = list(stage_categories)
        self._app.processEvents()
        category_button = window.left_sidebar._category_buttons[0]
        category_button.click()
        self._app.processEvents()
        self.assertTrue(window.tab_label.text().startswith("Category: STAGE / Stage Alpha"))

        window.close_tree_view()
        self._app.processEvents()

        self.assertEqual("Status: running", window.tab_label.text())
        self.assertTrue(window.tab_close_btn.isVisible())

    def test_category_scope_recomputes_group_status_for_remaining_members(self) -> None:
        group_node = "__group__level_0_Generic"
        graph_data = {
            "nodes": [(group_node, "failed")],
            "edges": [],
            "levels": {0: [group_node]},
            "trace_targets": {
                "upstream": {group_node: []},
                "downstream": {group_node: []},
            },
            "node_meta": {
                group_node: {
                    "display_name": "Generic",
                    "kind": "group",
                    "members": ["target_ok", "target_bad"],
                    "representative_target": "target_ok",
                    "status_text": "failed 1/2",
                    "member_statuses": {
                        "target_ok": "finish",
                        "target_bad": "failed",
                    },
                }
            },
            "target_to_node": {
                "target_ok": group_node,
                "target_bad": group_node,
            },
        }

        filtered_graph = _apply_category_scope_to_graph_data(graph_data, {"target_ok"})

        self.assertEqual([(group_node, "finish")], filtered_graph["nodes"])
        self.assertEqual(["target_ok"], filtered_graph["node_meta"][group_node]["members"])
        self.assertEqual("all finish", filtered_graph["node_meta"][group_node]["status_text"])


if __name__ == "__main__":
    unittest.main()
