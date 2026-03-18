"""Context-menu construction helpers for MainWindow."""

from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtWidgets import QApplication, QMenu

from new_gui.config.settings import STYLES


def build_execute_menu(window, menu: QMenu) -> None:
    """Build the Execute submenu."""
    exec_menu = menu.addMenu("▶ Execute")

    run_all_action = exec_menu.addAction("▶ Run All")
    run_all_action.setToolTip("Run all targets (Ctrl+Shift+Enter)")
    run_all_action.triggered.connect(lambda: window.start("XMeta_run all"))

    run_action = exec_menu.addAction("▶ Run Selected")
    run_action.setToolTip("Run selected targets (Ctrl+Enter)")
    run_action.triggered.connect(lambda: window.start("XMeta_run"))

    stop_action = exec_menu.addAction("■ Stop")
    stop_action.setToolTip("Stop selected targets")
    stop_action.triggered.connect(lambda: window.start("XMeta_stop"))

    exec_menu.addSeparator()

    skip_action = exec_menu.addAction("○ Skip")
    skip_action.setToolTip("Skip selected targets")
    skip_action.triggered.connect(lambda: window.start("XMeta_skip"))

    unskip_action = exec_menu.addAction("● Unskip")
    unskip_action.setToolTip("Unskip selected targets")
    unskip_action.triggered.connect(lambda: window.start("XMeta_unskip"))

    invalid_action = exec_menu.addAction("✕ Invalid")
    invalid_action.setToolTip("Mark selected targets as invalid")
    invalid_action.triggered.connect(lambda: window.start("XMeta_invalid"))


def build_file_menu(window, menu: QMenu) -> None:
    """Build the Files submenu."""
    file_menu = menu.addMenu("📁 Files")

    terminal_action = file_menu.addAction("⌘ Terminal")
    terminal_action.setToolTip("Open the embedded terminal panel in the current run directory")
    terminal_action.triggered.connect(window.open_terminal)

    csh_action = file_menu.addAction("📄 csh")
    csh_action.setToolTip("Open shell file for selected target")
    csh_action.triggered.connect(window.handle_csh)

    log_action = file_menu.addAction("📋 Log")
    log_action.setToolTip("Open log file for selected target")
    log_action.triggered.connect(window.handle_log)

    cmd_action = file_menu.addAction("⚡ cmd")
    cmd_action.setToolTip("Open command file for selected target")
    cmd_action.triggered.connect(window.handle_cmd)


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

    trace_up_action = trace_menu.addAction("⬆ Trace Up (Ctrl+U)")
    trace_up_action.setToolTip("Trace upstream dependencies")
    trace_up_action.triggered.connect(lambda: window.retrace_tab("in"))

    trace_down_action = trace_menu.addAction("⬇ Trace Down (Ctrl+D)")
    trace_down_action.setToolTip("Trace downstream dependencies")
    trace_down_action.triggered.connect(lambda: window.retrace_tab("out"))

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
