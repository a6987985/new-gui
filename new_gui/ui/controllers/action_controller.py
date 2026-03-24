"""Action and file-operation helpers for MainWindow."""

import os

from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from new_gui.config.settings import logger
from new_gui.services import action_flow
from new_gui.services import file_actions
from new_gui.services import run_repository
from new_gui.services import search_flow
from new_gui.services import tree_editing
from new_gui.services import tune_actions
from new_gui.services import view_tabs
from new_gui.ui.controllers.action_window_bridge import ActionWindowBridge
from new_gui.ui.dialogs.tune_dialogs import CopyTuneSelectDialog, SelectTuneDialog
from new_gui.ui.widgets.cell_option_popup import CellOptionPopup


def _bridge(window) -> ActionWindowBridge:
    """Return the narrow MainWindow bridge used by action-controller flows."""
    return ActionWindowBridge(window)


def copy_selected_target(window) -> None:
    """Copy selected target names to the clipboard."""
    ui = _bridge(window)
    targets = exit_search_mode_and_get_targets(window)
    if not targets:
        targets = ui.get_selected_action_targets()

    if not targets:
        ui.notify("Copy", "No target names available for the current selection", "info")
        return

    clipboard = QApplication.clipboard()
    clipboard_text = "\n".join(targets)
    clipboard.setText(clipboard_text, QClipboard.Clipboard)
    if clipboard.supportsSelection():
        clipboard.setText(clipboard_text, QClipboard.Selection)

    ui.notify("Copied", f"Copied {len(targets)} target(s)", "success")


def refresh_after_action(window, search_context) -> None:
    """Refresh the view after an action while preserving search state."""
    ui = _bridge(window)
    current_run = ui.current_run_name()
    search_flow.refresh_after_action(
        search_context,
        current_run,
        ui.build_status_cache,
        ui.rebuild_main_tree_now,
        ui.filter_tree,
        ui.restore_scroll_value,
    )


def exit_search_mode_and_get_targets(window):
    """Exit search mode if needed and return selected target names."""
    ui = _bridge(window)
    if ui.is_search_mode_active():
        selected_targets = ui.get_selected_targets()
        search_context = ui.build_search_context(selected_targets)
        logger.info(f"Exiting search mode with {len(selected_targets)} selected targets")

        return search_flow.exit_search_mode(
            search_context,
            ui.clear_search_ui_state,
            ui.rebuild_main_tree_now,
            ui.select_targets_in_tree,
        )
    return ui.get_selected_targets()


def log_action_result(window, command: str, result: dict, include_returncode: bool = False) -> None:
    """Log the outcome of a shell action using the current UI logging policy."""
    ui = _bridge(window)
    details = []
    level = "INFO"
    message = "Command completed successfully."

    if result.get("stdout"):
        logger.info(result["stdout"], extra={"ui_skip": True, "ui_source": "action"})
        details.append(f"STDOUT\n{result['stdout'].strip()}")
    if result.get("stderr"):
        logger.error(result["stderr"], extra={"ui_skip": True, "ui_source": "action"})
        details.append(f"STDERR\n{result['stderr'].strip()}")
        level = "ERROR"
        message = "Command produced stderr output."
    if result.get("timed_out"):
        logger.error(
            f"Command timed out: {command}",
            extra={"ui_skip": True, "ui_source": "action"},
        )
        details.append("The command exceeded the configured timeout.")
        level = "ERROR"
        message = "Command timed out."
    if result.get("error") is not None:
        logger.error(
            f"Error executing command: {result['error']}",
            extra={"ui_skip": True, "ui_source": "action"},
        )
        details.append(f"EXCEPTION\n{result['error']}")
        level = "ERROR"
        message = "Command execution failed."
    if include_returncode and result.get("returncode") not in (None, 0):
        logger.error(
            f"Command exited with code {result['returncode']}",
            extra={"ui_skip": True, "ui_source": "action"},
        )
        details.append(f"Return code: {result['returncode']}")
        level = "ERROR"
        message = f"Command exited with code {result['returncode']}."

    ui.append_ui_log(
        level,
        "action",
        message,
        command=command,
        details="\n\n".join(part for part in details if part),
    )


def start(window, action) -> None:
    """Execute a flow action and refresh the view when needed."""
    ui = _bridge(window)
    selected_targets = ui.get_selected_action_targets()
    search_context = ui.build_search_context(selected_targets)

    if action != "XMeta_run all" and not selected_targets:
        logger.warning(f"No targets selected for action: {action}", extra={"ui_source": "action"})
        return

    current_run = ui.current_run_name()
    action_request = action_flow.build_action_request(
        ui.run_base_dir,
        current_run,
        action,
        selected_targets,
    )
    logger.info(action_request["log_message"], extra={"ui_source": "action"})

    if action_request["run_sync"]:
        result = action_flow.execute_shell_command(
            action_request["argv"],
            action_request["timeout"],
            action_request["cwd"],
        )
        log_action_result(window, action_request["command"], result)
        refresh_after_action(window, search_context)
    else:
        def run_command():
            result = action_flow.execute_shell_command(
                action_request["argv"],
                action_request["timeout"],
                action_request["cwd"],
            )
            log_action_result(
                window,
                action_request["command"],
                result,
                include_returncode=True,
            )

        ui.submit_background(run_command)

    ui.clear_tree_selection()


def on_tree_double_clicked(window, index) -> None:
    """Handle tree double-clicks for run copy or BSUB editing."""
    ui = _bridge(window)
    if ui.is_all_status_view:
        run_name = tree_editing.get_all_status_run_name(ui.model, index)
        if run_name:
            clipboard = QApplication.clipboard()
            clipboard.setText(run_name)
            logger.info(f"Copied run name to clipboard: {run_name}")
        return

    edit_context = tree_editing.build_bsub_edit_context(ui.model, index)
    if not edit_context:
        return

    target = edit_context["target_name"]
    param_type = edit_context["param_type"]
    current_value = edit_context["current_value"]
    header = edit_context["header_text"]

    if param_type == "queue":
        new_value, ok = _select_queue_value(window, ui, index, current_value)
    elif param_type == "cores":
        new_value, ok = _select_core_value(window, index, current_value)
    elif param_type == "memory":
        new_value, ok = _select_memory_value(window, index, current_value)
    else:
        new_value, ok = QInputDialog.getText(
            window,
            f"Edit {header}",
            f"Enter new {param_type} value for '{target}':",
            QLineEdit.Normal,
            current_value,
        )

    if ok and new_value != current_value:
        validation_error = tree_editing.validate_bsub_value(param_type, new_value)
        if validation_error:
            QMessageBox.warning(window, "Invalid Input", validation_error)
            return

        if ui.save_bsub_param(ui.combo_sel, target, param_type, new_value):
            ui.set_model_data(index, new_value)
            ui.notify("Saved", f"Updated {param_type} to {new_value} for {target}", "success")
        else:
            QMessageBox.warning(
                window,
                "Error",
                f"Failed to update {param_type} for {target}. Check if .csh file exists.",
            )


def _select_queue_value(window, ui, index, current_value: str) -> tuple:
    """Prompt the user to choose one queue from the discovered queue list."""
    if current_value and not run_repository.is_editable_queue_name(current_value):
        QMessageBox.information(
            window,
            "Queue Selection",
            "Only queues starting with 'pd_' can be changed in the GUI.",
        )
        return current_value, False

    def discover():
        return run_repository.discover_available_queues(
            ui.combo_sel,
            ui.run_base_dir,
            current_value,
        )

    discovery_result = discover()
    queue_options = [
        {"value": queue_name, "label": queue_name}
        for queue_name in discovery_result.get("queues", [])
    ]
    if not queue_options:
        QMessageBox.information(
            window,
            "Queue Selection",
            "No editable queues starting with 'pd_' are available.",
        )
        return current_value, False

    selected_queue = _choose_cell_option(window, index, queue_options, current_value)
    if not selected_queue:
        return current_value, False

    return selected_queue, True


def _select_core_value(window, index, current_value: str) -> tuple:
    """Prompt the user to choose one fixed core value with recommendations."""
    selected_value = _choose_cell_option(window, index, tree_editing.CORE_VALUE_OPTIONS, current_value)
    if not selected_value:
        return current_value, False

    if selected_value == "32":
        confirmed = QMessageBox.warning(
            window,
            "Confirm 32 Cores",
            "32 cores is strongly discouraged. Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmed != QMessageBox.Yes:
            return current_value, False

    return selected_value, True


def _select_memory_value(window, index, current_value: str) -> tuple:
    """Prompt the user to choose one fixed memory value."""
    selected_value = _choose_cell_option(window, index, tree_editing.MEMORY_VALUE_OPTIONS, current_value)
    if not selected_value:
        return current_value, False
    return selected_value, True


def _choose_cell_option(window, index, options, current_value: str) -> str:
    """Open one compact popup anchored to the edited tree cell."""
    visual_rect = window.tree.visualRect(index)
    popup_pos = window.tree.viewport().mapToGlobal(visual_rect.bottomLeft())
    popup = CellOptionPopup(options, current_value=current_value, parent=window.tree)
    return popup.choose_at(popup_pos, min_width=max(visual_rect.width(), 120)).strip()


def open_file_with_editor(window, filepath: str, editor: str = "gvim", use_popen: bool = False) -> None:
    """Open a file with the configured editor in a background task."""
    _bridge(window).submit_background(file_actions.open_file_with_editor, filepath, editor, use_popen)


def handle_csh(window) -> None:
    """Open the shell file for the selected target."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        return

    target = selected_targets[0]
    shell_file = file_actions.get_shell_file(ui.combo_sel, target)

    if shell_file:
        ui.open_file_with_editor(shell_file)
    else:
        logger.warning(f"Shell file not found for target: {target}")


def handle_log(window) -> None:
    """Open the log file for the selected target."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        return

    target = selected_targets[0]
    log_file = file_actions.get_log_file(ui.combo_sel, target)

    if log_file:
        ui.open_file_with_editor(log_file, use_popen=True)
    else:
        logger.warning(f"Log file not found for target: {target}")


def handle_cmd(window) -> None:
    """Open the command file for the selected target."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        return

    target = selected_targets[0]
    cmd_file = file_actions.get_cmd_file(ui.combo_sel, target)

    if cmd_file:
        ui.open_file_with_editor(cmd_file)
    else:
        logger.warning(f"Command file not found for target: {target}")


def create_tune(window) -> None:
    """Create a tune file from tunesource entries and open it."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not ui.combo_sel or len(selected_targets) != 1:
        QMessageBox.information(window, "Info", "Select exactly one target to create tune.")
        return

    target = selected_targets[0]
    candidates = ui.get_tune_candidates_from_cmd(target)
    if not candidates:
        QMessageBox.information(
            window,
            "Info",
            f"No tunesource entries found in cmds/{target}.cmd",
        )
        return

    dialog = SelectTuneDialog(
        target,
        candidates,
        window,
        title_prefix="Create Tune",
        instruction_text="Select a tune file name to create:",
    )
    if dialog.exec_() != QDialog.Accepted:
        return

    selected_tune = dialog.get_selected_tune()
    if not selected_tune:
        return

    tune_file = selected_tune[1]
    try:
        created = tune_actions.ensure_tune_file(tune_file)
        if created:
            ui.notify(
                "Tune",
                f"Created tune file: {os.path.basename(tune_file)}",
                "success",
            )
        else:
            ui.notify(
                "Tune",
                f"Tune file already exists: {os.path.basename(tune_file)}",
                "info",
            )

        ui.invalidate_tune_cache(ui.combo_sel, target)
        ui.refresh_tune_cells_for_target(target)
        ui.open_tune_file(tune_file)
    except Exception as exc:
        logger.error(f"Failed to create tune file {tune_file}: {exc}")
        QMessageBox.warning(
            window,
            "Warning",
            f"Failed to create tune file:\n{tune_file}\n\n{exc}",
        )


def handle_tune(window) -> None:
    """Open a tune file for the selected target."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        return

    target = selected_targets[0]
    tune_files = ui.get_tune_files(target)

    if not tune_files:
        QMessageBox.information(window, "Info", f"No tune file found for: {target}")
        return

    if len(tune_files) == 1:
        ui.open_tune_file(tune_files[0][1])
        return

    dialog = SelectTuneDialog(target, tune_files, window)
    if dialog.exec_() == QDialog.Accepted:
        selected = dialog.get_selected_tune()
        if selected:
            ui.open_tune_file(selected[1])


def open_tune_file(window, tune_file) -> None:
    """Open a tune file with the configured editor."""
    _bridge(window).open_tune_file(tune_file)


def copy_tune_to_runs(window) -> None:
    """Copy selected tune files to other runs."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        return

    target = selected_targets[0]
    tune_files = ui.get_tune_files(target)

    if not tune_files:
        QMessageBox.information(window, "Info", f"No tune file found for: {target}")
        return

    available_runs = run_repository.list_available_runs(ui.run_base_dir)
    if not available_runs:
        QMessageBox.warning(window, "Warning", "No other runs available")
        return

    current_run = os.path.basename(ui.combo_sel) if os.path.isabs(ui.combo_sel) else ui.combo_sel

    dialog = CopyTuneSelectDialog(current_run, target, tune_files, available_runs, window)
    if dialog.exec_() != QDialog.Accepted:
        return

    selected_runs = dialog.get_selected_runs()
    selected_tunes = dialog.get_selected_tune_suffixes()
    if not selected_runs or not selected_tunes:
        return

    result = tune_actions.copy_tune_files_to_runs(
        selected_tunes,
        selected_runs,
        ui.run_base_dir,
        target,
    )
    total_success = result["total_success"]

    for run in selected_runs:
        run_dir = os.path.join(ui.run_base_dir, run)
        ui.invalidate_tune_cache(run_dir, target)

    tune_names = ", ".join([suffix for suffix, _ in selected_tunes])
    QMessageBox.information(
        window,
        "Copy Complete",
        f"Copied {len(selected_tunes)} tune file(s) ({tune_names})\nto {total_success}/{len(selected_runs)} runs",
    )


def open_terminal(window) -> None:
    """Open the embedded terminal panel or fall back to an external terminal."""
    ui = _bridge(window)
    if not ui.combo_sel:
        return

    if ui.show_embedded_terminal_panel(ui.combo_sel):
        ui.append_ui_log(
            "INFO",
            "terminal",
            "Opened embedded terminal panel.",
            details=ui.combo_sel,
        )
        return

    ui.append_ui_log(
        "WARNING",
        "terminal",
        "Embedded terminal unavailable. Falling back to the external terminal.",
        details=ui.embedded_terminal_status_message(),
    )

    open_external_terminal(window, log_request=False)


def open_external_terminal(window, log_request: bool = True) -> None:
    """Open the external terminal in the current run directory."""
    ui = _bridge(window)
    if not ui.combo_sel:
        return

    if log_request:
        ui.append_ui_log(
            "INFO",
            "terminal",
            "Opening external terminal.",
            details=ui.combo_sel,
        )

    ui.submit_background(
        file_actions.open_terminal,
        ui.combo_sel,
        "XMeta_term",
        ui.current_xmeta_background_color(),
    )


def retrace_tab(window, inout) -> None:
    """Execute trace filtering in place for the selected target."""
    ui = _bridge(window)
    selected_targets = exit_search_mode_and_get_targets(window)
    if not selected_targets or not ui.combo_sel:
        logger.warning("No target selected for trace", extra={"ui_source": "action"})
        return

    selected_target = selected_targets[0]
    logger.info(f"Trace {inout} for target: {selected_target}", extra={"ui_source": "action"})

    related_targets = ui.get_retrace_target(selected_target, inout)
    if selected_target not in related_targets:
        if inout == "in":
            related_targets.append(selected_target)
        else:
            related_targets.insert(0, selected_target)

    if not related_targets:
        logger.info("No dependencies found.", extra={"ui_source": "action"})
        return

    ui.filter_tree_by_targets(set(related_targets))

    direction = "Up" if inout == "in" else "Down"
    label_text = f"Trace {direction}: {selected_target}"
    ui.apply_tab_state(view_tabs.get_trace_tab_state(label_text))
