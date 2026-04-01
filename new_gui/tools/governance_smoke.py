"""Cheap governance regression harness for the new_gui package."""

from __future__ import annotations

import os
import py_compile
import sys
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


def smoke_main_window(app: QApplication) -> None:
    """Verify the main window still supports the key governance seams."""
    window = MainWindow()
    window.show()
    _process_events(app)

    window.header.show_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header search editor did not appear.")

    window.header.filter_edit.setText("a")
    _process_events(app)
    _require(window.header.get_filter_text() == "a", "Header search text failed to update.")

    window.header.filter_edit.setText("abc")
    _process_events(app)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    QTest.keyClick(window.header.filter_edit, Qt.Key_Backspace)
    _process_events(app)
    _require(window.header.get_filter_text() == "", "Header search text did not clear cleanly.")

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

    window.header.hide_filter()
    _process_events(app)
    _require(window.header.filter_edit is not None, "Header search editor was unexpectedly destroyed.")

    initial_entries = window._session_log_widget.entry_count()
    window.show_notification("Smoke", "Notification mirroring check", "warning")
    _process_events(app)
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


def main() -> int:
    """Run the governance smoke suite and print a compact report."""
    compiled_count = run_py_compile_check()
    app = _ensure_app()

    smoke_bottom_output_panel(app)
    smoke_main_window(app)
    smoke_dependency_graph_dialog(app)

    print(f"Governance smoke passed. Compiled {compiled_count} Python files under new_gui/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
