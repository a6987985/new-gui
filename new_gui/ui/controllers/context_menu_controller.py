"""Context-menu construction helpers for MainWindow."""

from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtWidgets import QApplication, QMenu

from new_gui.config.settings import STYLES
from new_gui.ui.action_registry import (
    get_action_definition,
    get_execute_menu_action_ids,
    get_file_menu_action_ids,
    get_trace_menu_action_ids,
)


def _add_registered_action(window, menu: QMenu, action_id: str):
    """Add one action from the shared action registry to the provided menu."""
    definition = get_action_definition(action_id)
    action = menu.addAction(definition.menu_label)
    action.setToolTip(definition.tooltip)
    action.triggered.connect(lambda _, trigger=definition.trigger: trigger(window))
    return action


def build_execute_menu(window, menu: QMenu) -> None:
    """Build the Execute submenu."""
    exec_menu = menu.addMenu("▶ Execute")
    action_ids = list(get_execute_menu_action_ids())
    for action_id in action_ids[:3]:
        _add_registered_action(window, exec_menu, action_id)
    exec_menu.addSeparator()
    for action_id in action_ids[3:]:
        _add_registered_action(window, exec_menu, action_id)


def build_file_menu(window, menu: QMenu) -> None:
    """Build the Files submenu."""
    file_menu = menu.addMenu("📁 Files")
    for action_id in get_file_menu_action_ids():
        _add_registered_action(window, file_menu, action_id)


def build_tune_menu(window, menu: QMenu, selected_targets: list) -> None:
    """Build the Tune submenu."""
    tune_menu = menu.addMenu("🎵 Tune")
    single_target = len(selected_targets) == 1

    if single_target and window.combo_sel:
        tune_display = window.get_tune_display(window.combo_sel, selected_targets[0])
        if tune_display:
            tune_action = tune_menu.addAction(f"📝 Open Tune ({tune_display})")
        else:
            tune_action = tune_menu.addAction("📝 Open Tune")
    else:
        tune_action = tune_menu.addAction("📝 Open Tune")
    tune_action.setToolTip("Open tune file for selected target")
    tune_action.triggered.connect(window.handle_tune)

    create_tune_action = tune_menu.addAction("➕ Create Tune")
    create_tune_action.setToolTip("Create tune file from cmds/<target>.cmd tunesource entries")
    create_tune_action.triggered.connect(window.create_tune)
    create_tune_action.setEnabled(single_target)

    copy_tune_action = tune_menu.addAction("📋 Copy Tune To...")
    copy_tune_action.setToolTip("Copy tune file to other runs")
    copy_tune_action.triggered.connect(window.copy_tune_to_runs)


def build_params_menu(window, menu: QMenu) -> None:
    """Build the Params submenu."""
    params_menu = menu.addMenu("⚙ Params")

    user_params_action = params_menu.addAction("📝 User Params")
    user_params_action.setToolTip("Edit user.params for current run")
    user_params_action.triggered.connect(window.open_user_params)

    tile_params_action = params_menu.addAction("📋 Tile Params")
    tile_params_action.setToolTip("View tile.params for current run")
    tile_params_action.triggered.connect(window.open_tile_params)


def build_trace_menu(window, menu: QMenu) -> None:
    """Build the Trace submenu."""
    trace_menu = menu.addMenu("🔗 Trace")
    for action_id in get_trace_menu_action_ids():
        _add_registered_action(window, trace_menu, action_id)

    trace_menu.addSeparator()

    graph_action = trace_menu.addAction("📊 Dependency Graph (Ctrl+G)")
    graph_action.setToolTip("Show full dependency graph")
    graph_action.triggered.connect(window.show_dependency_graph)


def build_copy_menu(window, menu: QMenu, single_target: bool, selected_targets: list) -> None:
    """Build the Copy submenu."""
    copy_menu = menu.addMenu("📋 Copy")

    copy_target_action = copy_menu.addAction("Copy Target Name (Ctrl+C)")
    copy_target_action.setToolTip("Copy selected target names to clipboard")
    copy_target_action.triggered.connect(window._copy_selected_target)

    if single_target and selected_targets:
        copy_path_action = copy_menu.addAction("Copy Run Path")
        copy_path_action.setToolTip("Copy the full path of the current run")
        copy_path_action.triggered.connect(window._copy_run_path)


def show_context_menu(window, position) -> None:
    """Show the right-click context menu."""
    index = window.tree.indexAt(position)
    if not index.isValid():
        return

    selection_model = window.tree.selectionModel()
    if not selection_model.isSelected(index):
        selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    menu = QMenu()
    menu.setStyleSheet(STYLES["menu"])

    selected_targets = window.get_selected_targets()
    single_target = len(selected_targets) == 1

    window._build_execute_menu(menu)
    menu.addSeparator()
    window._build_file_menu(menu)
    menu.addSeparator()
    window._build_tune_menu(menu, selected_targets)
    menu.addSeparator()
    window._build_params_menu(menu)
    menu.addSeparator()
    window._build_trace_menu(menu)
    menu.addSeparator()
    window._build_copy_menu(menu, single_target, selected_targets)

    menu.exec_(window.tree.viewport().mapToGlobal(position))


def copy_run_path(window) -> None:
    """Copy the current run path to the clipboard."""
    if window.combo_sel:
        clipboard = QApplication.clipboard()
        clipboard.setText(window.combo_sel)
        window.show_notification("Copied", f"Copied path: {window.combo_sel}", "success")
