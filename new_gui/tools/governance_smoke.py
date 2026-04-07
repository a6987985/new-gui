"""Cheap governance regression harness for the new_gui package."""

from __future__ import annotations

import os
import py_compile
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "new_gui"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPushButton

from new_gui.reproduce_ui import MainWindow
from new_gui.services import action_flow
from new_gui.services import tree_rows
from new_gui.ui.controllers import action_controller
from new_gui.ui.dialogs.dependency_graph import DependencyGraphDialog
from new_gui.ui.widgets.bottom_output_panel import BottomOutputPanel, GuiLogEntry


class SmokeFailure(RuntimeError):
    """Raised when one smoke-check assertion fails."""


def _python_sources():
    """Return all package Python sources that should compile cleanly."""
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _require(condition: bool, message: str) -> None:
    """Raise one structured failure when a smoke assertion does not hold."""
    if not condition:
        raise SmokeFailure(message)


def _ensure_app() -> QApplication:
    """Return the shared QApplication instance for offscreen smokes."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _process_events(app: QApplication) -> None:
    """Process pending Qt events once."""
    app.processEvents()


def _count_visible_target_rows(window: MainWindow) -> int:
    """Count currently visible target rows in the shared tree model."""
    model = window.model
    tree = window.tree

    def walk(parent_item=None, parent_index=None) -> int:
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        visible_count = 0
        for row in range(row_count):
            check_parent = parent_index if parent_index is not None else tree.rootIndex()
            if tree.isRowHidden(row, check_parent):
                continue
            row_items = tree_rows.get_row_items(model, row, parent_item)
            level_item = row_items[0] if row_items else None
            target_item = row_items[1] if len(row_items) > 1 else None
            if tree_rows.get_row_kind(target_item) == tree_rows.ROW_KIND_TARGET:
                visible_count += 1
            if level_item is not None and level_item.hasChildren():
                visible_count += walk(level_item, level_item.index())
        return visible_count

    return walk()


def _collect_model_target_names(window: MainWindow) -> list[str]:
    """Return all target names currently represented in the active model."""
    model = window.model
    collected = []

    def walk(parent_item=None) -> None:
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        for row in range(row_count):
            row_items = tree_rows.get_row_items(model, row, parent_item)
            level_item = row_items[0] if row_items else None
            target_item = row_items[1] if len(row_items) > 1 else None
            target_name = tree_rows.get_row_target_name(target_item)
            if target_name:
                collected.append(target_name)
            if level_item is not None and level_item.hasChildren():
                walk(level_item)

    walk()
    return collected


def _collect_model_group_labels(window: MainWindow) -> list[str]:
    """Return all synthetic group labels currently represented in the active model."""
    model = window.model
    labels = []

    def walk(parent_item=None) -> None:
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        for row in range(row_count):
            row_items = tree_rows.get_row_items(model, row, parent_item)
            level_item = row_items[0] if row_items else None
            target_item = row_items[1] if len(row_items) > 1 else None
            if tree_rows.get_row_kind(target_item) == tree_rows.ROW_KIND_GROUP and target_item is not None:
                labels.append(target_item.text() or "")
            if level_item is not None and level_item.hasChildren():
                walk(level_item)

    walk()
    return labels


def _clear_line_edit_with_keys(edit) -> None:
    """Clear one line edit using keyboard events so textEdited is emitted."""
    edit.selectAll()
    QTest.keyClick(edit, Qt.Key_Delete)


def _replace_line_edit_with_keys(edit, text: str) -> None:
    """Replace one line-edit value via keyboard events without clearing to empty first."""
    edit.selectAll()
    if text:
        QTest.keyClicks(edit, text)


def run_py_compile_check() -> int:
    """Compile all package Python files and return the file count."""
    sources = _python_sources()
    for source_path in sources:
        py_compile.compile(str(source_path), doraise=True)
    return len(sources)


def smoke_bottom_output_panel(app: QApplication) -> None:
    """Verify the shared bottom output widget can switch tabs and accept log entries."""
    panel = BottomOutputPanel()
    panel.append_log_entry(GuiLogEntry.create("INFO", "system", "Bottom output smoke"))
    _require(panel.log_widget.entry_count() == 1, "Bottom output panel did not keep the log entry.")

    panel.show_log_tab()
    _process_events(app)
    _require(panel.current_tab_name() == "Log", "Bottom output panel failed to switch to the Log tab.")

    panel.show_terminal_tab()
    _process_events(app)
    _require(
        panel.current_tab_name() == "Terminal",
        "Bottom output panel failed to switch back to the Terminal tab.",
    )
    panel.deleteLater()


def _row2_button_widths(window: MainWindow) -> dict[str, int]:
    """Return current row2 button widths keyed by button text."""
    container_layout = window._top_button_container.layout()
    if container_layout.count() < 2:
        return {}

    row2_widget = container_layout.itemAt(1).widget()
    if row2_widget is None:
        return {}

    return {
        button.text(): button.width()
        for button in row2_widget.findChildren(QPushButton)
    }


def _build_search_stability_tree(window: MainWindow) -> None:
    """Build a deterministic tree used by search stability checks."""
    window.model.removeRows(0, window.model.rowCount())
    level_row = tree_rows.build_container_row_items(
        "1",
        "Level 1",
        tree_rows.ROW_KIND_LEVEL,
        descendant_targets=["alpha_target", "beta_target"],
    )
    level_item = level_row[0]
    level_item.appendRow(
        tree_rows.build_target_row_items(
            "",
            "alpha_target",
            "finish",
            [],
            "",
            "",
            "pd_sim",
            "4",
            "30000",
            window.colors,
        )
    )
    level_item.appendRow(
        tree_rows.build_target_row_items(
            "",
            "beta_target",
            "finish",
            [],
            "",
            "",
            "pd_sim",
            "4",
            "30000",
            window.colors,
        )
    )
    window.model.appendRow(level_row)
    window.tree.expandAll()


def smoke_search_stability(window: MainWindow, app: QApplication) -> None:
    """Verify repeated search clear/delete transitions remain stable."""
    window.header.show_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header search editor did not appear for stability smoke.")

    for _ in range(25):
        _replace_line_edit_with_keys(window.header.filter_edit, "alpha")
        _process_events(app)
        _clear_line_edit_with_keys(window.header.filter_edit)
        _process_events(app)
        QTest.keyClick(window.header.filter_edit, Qt.Key_Delete)
        _process_events(app)

    _require(
        window.header.get_filter_text() == "",
        "Repeated clear/delete changed search text unexpectedly.",
    )
    _require(
        window.is_search_mode is False,
        "Repeated clear/delete unexpectedly left search mode active.",
    )


def smoke_search_options(window: MainWindow, app: QApplication) -> None:
    """Verify case/whole-word/regex option toggles change matching behavior."""
    current_run = window.combo.currentText()
    window.combo_sel = "/tmp"
    window.cached_targets_by_level = {1: ["AlphaCase", "alphacase"]}
    window.cached_collapsible_target_groups = {}
    window._cached_collapsible_target_groups_run = current_run
    window.is_search_mode = False
    _process_events(app)

    window.header.show_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header filter editor missing for search-option smoke.")
    window.header.set_filter_options(
        {
            "case_sensitive": False,
            "whole_word": False,
            "regex": False,
        }
    )
    _process_events(app)

    case_button = getattr(window.header.filter_edit, "_case_button", None)
    whole_word_button = getattr(window.header.filter_edit, "_whole_word_button", None)
    regex_button = getattr(window.header.filter_edit, "_regex_button", None)
    _require(case_button is not None, "Case-sensitive search button was not created.")
    _require(whole_word_button is not None, "Whole-word search button was not created.")
    _require(regex_button is not None, "Regex search button was not created.")

    _replace_line_edit_with_keys(window.header.filter_edit, "alphacase")
    _process_events(app)
    target_names = _collect_model_target_names(window)
    _require("AlphaCase" in target_names, "Case-insensitive search hid mixed-case row.")
    _require("alphacase" in target_names, "Case-insensitive search hid lowercase row.")

    QTest.mouseClick(case_button, Qt.LeftButton)
    _process_events(app)
    target_names = _collect_model_target_names(window)
    _require("AlphaCase" not in target_names, "Case-sensitive search did not hide mixed-case row.")
    _require("alphacase" in target_names, "Case-sensitive search hid lowercase row unexpectedly.")

    _replace_line_edit_with_keys(window.header.filter_edit, "alpha")
    _process_events(app)
    target_names = _collect_model_target_names(window)
    _require("alphacase" in target_names, "Substring search should still match lowercase row.")
    QTest.mouseClick(whole_word_button, Qt.LeftButton)
    _process_events(app)
    target_names = _collect_model_target_names(window)
    _require("alphacase" not in target_names, "Whole-word search did not tighten substring matching.")

    QTest.mouseClick(whole_word_button, Qt.LeftButton)
    QTest.mouseClick(regex_button, Qt.LeftButton)
    _process_events(app)
    _replace_line_edit_with_keys(window.header.filter_edit, "^alphacase$")
    _process_events(app)
    target_names = _collect_model_target_names(window)
    _require("AlphaCase" not in target_names, "Regex search unexpectedly matched mixed-case row.")
    _require("alphacase" in target_names, "Regex search did not match exact lowercase row.")

    QTest.mouseClick(whole_word_button, Qt.LeftButton)
    QTest.mouseClick(case_button, Qt.LeftButton)
    QTest.mouseClick(regex_button, Qt.LeftButton)
    _clear_line_edit_with_keys(window.header.filter_edit)
    _process_events(app)


def smoke_search_parent_projection(window: MainWindow, app: QApplication) -> None:
    """Verify non-matching parent targets are removed while Generic parent groups stay."""
    current_run = window.combo.currentText()
    window.combo_sel = "/tmp"
    window.cached_targets_by_level = {
        11: [
            "PyPrepScanDef",
            "FmEqvFloorplanVsBase",
            "FmEqvPwrFloorplanVsBase",
            "FmEqvPwrAllUpfSuppliesOnFloorplanVsBase",
        ]
    }
    window.cached_collapsible_target_groups = {
        "GenericFmEqvFloorplan": [
            "FmEqvFloorplanVsBase",
            "FmEqvPwrFloorplanVsBase",
            "FmEqvPwrAllUpfSuppliesOnFloorplanVsBase",
        ]
    }
    window._cached_collapsible_target_groups_run = current_run

    window.header.show_filter()
    _process_events(app)
    window.header.set_filter_options(
        {
            "case_sensitive": False,
            "whole_word": False,
            "regex": False,
        }
    )
    _process_events(app)
    _replace_line_edit_with_keys(window.header.filter_edit, "Floorplan")
    _process_events(app)

    target_names = _collect_model_target_names(window)
    group_labels = _collect_model_group_labels(window)
    _require("PyPrepScanDef" not in target_names, "Search results still included non-matching parent target.")
    _require(
        "GenericFmEqvFloorplan" in group_labels,
        "Search results dropped the Generic parent group for matching children.",
    )


def smoke_tree_expansion_modes(window: MainWindow, app: QApplication) -> None:
    """Verify default expand keeps Generic groups collapsed while full expand opens them."""
    window.model.removeRows(0, window.model.rowCount())

    level_row = tree_rows.build_container_row_items(
        "1",
        "Level 1",
        tree_rows.ROW_KIND_LEVEL,
        descendant_targets=["generic_member_a", "generic_member_b"],
        status_colors=window.colors,
    )
    generic_group_row = tree_rows.build_container_row_items(
        "",
        "Generic Alpha",
        tree_rows.ROW_KIND_GROUP,
        descendant_targets=["generic_member_a", "generic_member_b"],
        status_colors=window.colors,
    )
    generic_group_row[0].appendRow(
        tree_rows.build_target_row_items(
            "",
            "generic_member_a",
            "finish",
            [],
            "",
            "",
            "pd_sim",
            "4",
            "30000",
            window.colors,
        )
    )
    generic_group_row[0].appendRow(
        tree_rows.build_target_row_items(
            "",
            "generic_member_b",
            "finish",
            [],
            "",
            "",
            "pd_sim",
            "4",
            "30000",
            window.colors,
        )
    )
    level_row[0].appendRow(generic_group_row)
    window.model.appendRow(level_row)

    _process_events(app)
    window.expand_tree_default()
    _process_events(app)

    level_index = window.model.index(0, 0)
    generic_index = window.model.index(0, 0, level_index)
    _require(window.tree.isExpanded(level_index), "Default tree expand did not open the level container.")
    _require(
        not window.tree.isExpanded(generic_index),
        "Default tree expand should keep Generic groups collapsed.",
    )

    window.expand_tree_all()
    _process_events(app)
    _require(
        window.tree.isExpanded(generic_index),
        "Full tree expand did not open the Generic target group.",
    )

    window.collapse_tree_all()
    _process_events(app)
    _require(not window.tree.isExpanded(level_index), "Collapse all did not collapse the level container.")


def smoke_main_window(app: QApplication) -> None:
    """Verify the main window still supports the key governance seams."""
    window = MainWindow()
    window.show()
    _process_events(app)

    window.header.show_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header search editor did not appear.")

    _clear_line_edit_with_keys(window.header.filter_edit)
    QTest.keyClicks(window.header.filter_edit, "a")
    _process_events(app)
    _require(window.header.get_filter_text() == "a", "Header search text failed to update.")
    if window.cached_targets_by_level:
        _require(window.is_search_mode is True, "Header search did not enter search mode.")

    _clear_line_edit_with_keys(window.header.filter_edit)
    QTest.keyClicks(window.header.filter_edit, "abc")
    _process_events(app)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    _process_events(app)
    _require(window.header.get_filter_text() == "", "Header search text did not clear cleanly.")
    if window.cached_targets_by_level:
        _require(window.is_search_mode is False, "Header search did not exit search mode after clearing text.")
    QTest.keyClick(window.header.filter_edit, Qt.Key_Delete)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Delete)
    _process_events(app)
    _require(window.header.get_filter_text() == "", "Header search text changed after extra Delete on empty input.")
    _require(window.header.filter_edit.isVisible(), "Header search editor unexpectedly closed after extra Delete.")
    _require(window.is_search_mode is False, "Extra Delete on empty search unexpectedly re-entered search mode.")
    window.tree.setFocus()
    _process_events(app)
    _require(
        window.header.filter_edit.isVisible() is False,
        "Empty header search editor did not close after focus moved away.",
    )

    window.header.show_filter()
    _process_events(app)
    smoke_search_stability(window, app)
    smoke_search_options(window, app)
    smoke_search_parent_projection(window, app)
    smoke_tree_expansion_modes(window, app)
    window._clear_search_ui_state()
    _process_events(app)

    window.model.removeRows(0, window.model.rowCount())
    target_row = tree_rows.build_target_row_items(
        "1",
        "smoke_target",
        "finish",
        [],
        "",
        "",
        "pd_sim",
        "4",
        "30000",
        window.colors,
    )
    window.model.appendRow(target_row)
    selection_flags = window.tree.selectionModel().ClearAndSelect | window.tree.selectionModel().Rows
    window.tree.selectionModel().select(window.model.index(0, 1), selection_flags)
    window.is_search_mode = True
    _process_events(app)

    window.tree.setFocus()
    _process_events(app)
    QTest.keyClick(window.tree, Qt.Key_C, Qt.ControlModifier)
    _process_events(app)
    _require(
        QApplication.clipboard().text() == "smoke_target",
        "Ctrl+C on a selected search result did not copy the target.",
    )
    _require(
        window.header.get_filter_text() == "",
        "Ctrl+C in header search unexpectedly changed the search text.",
    )

    window.model.removeRows(0, window.model.rowCount())
    generic_group_row = tree_rows.build_container_row_items(
        "1",
        "Generic Alpha",
        tree_rows.ROW_KIND_GROUP,
        descendant_targets=["generic_member_a", "generic_member_b"],
    )
    standalone_target_row = tree_rows.build_target_row_items(
        "1",
        "standalone_target",
        "finish",
        [],
        "",
        "",
        "pd_sim",
        "4",
        "30000",
        window.colors,
    )
    window.model.appendRow(generic_group_row)
    window.model.appendRow(standalone_target_row)

    selection_model = window.tree.selectionModel()
    select_flags = selection_model.Select | selection_model.Rows
    selection_model.clearSelection()
    selection_model.select(window.model.index(0, 1), select_flags)
    selection_model.select(window.model.index(1, 1), select_flags)
    _process_events(app)

    QTest.keyClick(window.tree, Qt.Key_C, Qt.ControlModifier)
    _process_events(app)
    _require(
        QApplication.clipboard().text()
        == "generic_member_a\ngeneric_member_b\nstandalone_target",
        "Ctrl+C did not include Generic-group targets when mixed with a leaf target.",
    )

    window.header.hide_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header search editor was unexpectedly destroyed.")

    initial_entries = window._session_log_widget.entry_count()
    window.show_notification("Smoke", "Notification mirroring check", "warning")
    _process_events(app)
    notification = window._notification_manager._notifications[-1]
    _require(
        notification.height() >= notification.sizeHint().height(),
        "Notification card height did not expand to fit its text content.",
    )
    _require(
        window._session_log_widget.entry_count() == initial_entries + 1,
        "Notification mirroring did not append to the GUI session log.",
    )
    _require(
        window._bottom_output_panel.current_tab_name() == "Log",
        "Warning notification did not bring the Log tab to the front.",
    )

    action_controller.log_action_result(
        window,
        "echo governance-smoke",
        {"stdout": "ok", "stderr": "simulated warning", "returncode": 1},
        include_returncode=True,
    )
    _process_events(app)
    _require(
        window._session_log_widget.entry_count() >= initial_entries + 2,
        "Action result logging did not append a GUI log entry.",
    )

    subset_ids = ["run_all", "run", "term", "cmd"]
    full_ids = [
        "run_all",
        "run",
        "term",
        "csh",
        "log",
        "cmd",
        "trace_up",
        "trace_down",
    ]
    window._on_apply_button_visibility(subset_ids)
    _process_events(app)
    subset_widths = _row2_button_widths(window)

    window._on_apply_button_visibility(full_ids)
    _process_events(app)
    full_widths = _row2_button_widths(window)

    for button_name in ("Term", "Cmd"):
        _require(
            subset_widths.get(button_name) == full_widths.get(button_name),
            f"Row2 width drift detected for {button_name!r} between subset and full states.",
        )

    if hasattr(window, "_remove_gui_log_handler"):
        window._remove_gui_log_handler()
    if hasattr(window, "_executor"):
        window._executor.shutdown(wait=False)
    window.close()
    window.deleteLater()


def _sample_graph_data() -> dict:
    """Return a small deterministic dependency graph for dialog smoke tests."""
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


def smoke_dependency_graph_dialog(app: QApplication) -> None:
    """Verify the dependency graph dialog still draws, scopes, and searches."""
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
    _process_events(app)

    _require(bool(dialog.scene.items()), "Dependency graph dialog did not render any scene items.")

    dialog.select_node("mid_target")
    dialog.highlight_downstream()
    _require(
        dialog.highlighted_nodes == {"mid_target", "leaf_target"},
        "Dependency trace highlighting produced an unexpected target set.",
    )

    dialog.select_node("mid_target")
    dialog.show_local_subgraph()
    _process_events(app)
    _require(dialog._scope_mode == "local", "Dependency graph failed to enter local scope mode.")

    dialog._search_input.setText("leaf")
    _process_events(app)
    dialog.find_next_target()
    _require(
        dialog.selected_node == "leaf_target",
        "Dependency graph search did not select the expected target.",
    )

    dialog.show_full_graph()
    _process_events(app)
    _require(dialog._scope_mode == "full", "Dependency graph failed to restore full scope mode.")
    dialog.close()
    dialog.deleteLater()


def smoke_action_flow_policy() -> None:
    """Verify run actions preserve dependency order and stay free of GUI kill timeouts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        run_base_dir = Path(temp_dir)
        run_dir = run_base_dir / "sample_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / ".target_dependency.csh").write_text(
            'set LEVEL_1 = "first_target"\nset LEVEL_2 = "second_target"\n',
            encoding="utf-8",
        )

        request = action_flow.build_action_request(
            str(run_base_dir),
            "sample_run",
            "XMeta_run",
            ["second_target", "first_target"],
        )

        _require(
            request["argv"] == ["XMeta_run", "first_target", "second_target"],
            "Run action request did not normalize target order by dependency level.",
        )
        _require(
            request["timeout"] is None,
            "Run action request should not impose a GUI timeout on XMeta_run.",
        )


def main() -> int:
    """Run the governance smoke suite and print a compact report."""
    compiled_count = run_py_compile_check()
    app = _ensure_app()

    smoke_bottom_output_panel(app)
    smoke_main_window(app)
    smoke_dependency_graph_dialog(app)
    smoke_action_flow_policy()

    print(f"Governance smoke passed. Compiled {compiled_count} Python files under new_gui/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
