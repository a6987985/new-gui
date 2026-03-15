"""Action and file-operation helpers for MainWindow."""

import os

from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit, QMessageBox

from new_gui.config.settings import logger
from new_gui.services import action_flow
from new_gui.services import file_actions
from new_gui.services import run_repository
from new_gui.services import search_flow
from new_gui.services import tree_editing
from new_gui.services import tune_actions
from new_gui.services import view_tabs
from new_gui.ui.dialogs.tune_dialogs import CopyTuneSelectDialog, SelectTuneDialog


def copy_selected_target(window) -> None:
    """Copy selected target names to the clipboard."""
    targets = window._exit_search_mode_and_get_targets()
    if not targets:
        targets = window.get_selected_action_targets()

    if not targets:
        window.show_notification("Copy", "No target names available for the current selection", "info")
        return

    clipboard = QApplication.clipboard()
    clipboard_text = "\n".join(targets)
    clipboard.setText(clipboard_text, QClipboard.Clipboard)
    if clipboard.supportsSelection():
        clipboard.setText(clipboard_text, QClipboard.Selection)

    window.show_notification("Copied", f"Copied {len(targets)} target(s)", "success")


def get_selected_targets_keep_search(window):
    """Get selected targets while preserving the active search state."""
    selected_targets = window.get_selected_targets()
    return selected_targets, window._build_search_context(selected_targets)


def refresh_after_action(window, search_context) -> None:
    """Refresh the view after an action while preserving search state."""
    current_run = window.combo.currentText()
    search_flow.refresh_after_action(
        search_context,
        current_run,
        window._build_status_cache,
        window._rebuild_main_tree_now,
        window.filter_tree,
        window.tree.verticalScrollBar().setValue,
    )


def exit_search_mode_and_get_targets(window):
    """Exit search mode if needed and return selected target names."""
    if window.is_search_mode:
        selected_targets = window.get_selected_targets()
        search_context = window._build_search_context(selected_targets)
        logger.info(f"Exiting search mode with {len(selected_targets)} selected targets")

        return search_flow.exit_search_mode(
            search_context,
            window._clear_search_ui_state,
            window._rebuild_main_tree_now,
            window._select_targets_in_tree,
        )
    return window.get_selected_targets()


def log_action_result(window, command: str, result: dict, include_returncode: bool = False) -> None:
    """Log the outcome of a shell action using the current UI logging policy."""
    del window
    if result.get("stdout"):
        logger.info(result["stdout"])
    if result.get("stderr"):
        logger.error(result["stderr"])
    if result.get("timed_out"):
        logger.error(f"Command timed out: {command}")
    if result.get("error") is not None:
        logger.error(f"Error executing command: {result['error']}")
    if include_returncode and result.get("returncode") not in (None, 0):
        logger.error(f"Command exited with code {result['returncode']}")


def start(window, action) -> None:
    """Execute a flow action and refresh the view when needed."""
    selected_targets = window.get_selected_action_targets()
    search_context = window._build_search_context(selected_targets)

    if action != "XMeta_run all" and not selected_targets:
        logger.warning(f"No targets selected for action: {action}")
        return

    current_run = window.combo.currentText()
    action_request = action_flow.build_action_request(
        window.run_base_dir,
        current_run,
        action,
        selected_targets,
    )
    logger.info(action_request["log_message"])

    if action_request["run_sync"]:
        result = action_flow.execute_shell_command(
            action_request["argv"],
            action_request["timeout"],
            action_request["cwd"],
        )
        window._log_action_result(action_request["command"], result)
        window._refresh_after_action(search_context)
    else:
        def run_command():
            result = action_flow.execute_shell_command(
                action_request["argv"],
                action_request["timeout"],
                action_request["cwd"],
            )
            window._log_action_result(
                action_request["command"],
                result,
                include_returncode=True,
            )

        window._executor.submit(run_command)

    window.tree.clearSelection()


def on_tree_double_clicked(window, index) -> None:
    """Handle tree double-clicks for run copy or BSUB editing."""
    if window.is_all_status_view:
        run_name = tree_editing.get_all_status_run_name(window.model, index)
        if run_name:
            clipboard = QApplication.clipboard()
            clipboard.setText(run_name)
            logger.info(f"Copied run name to clipboard: {run_name}")
        return

    edit_context = tree_editing.build_bsub_edit_context(window.model, index)
    if not edit_context:
        return

    target = edit_context["target_name"]
    param_type = edit_context["param_type"]
    current_value = edit_context["current_value"]
    header = edit_context["header_text"]

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

        if window.save_bsub_param(window.combo_sel, target, param_type, new_value):
            window.model.setData(index, new_value)
            window.show_notification("Saved", f"Updated {param_type} to {new_value} for {target}", "success")
        else:
            QMessageBox.warning(
                window,
                "Error",
                f"Failed to update {param_type} for {target}. Check if .csh file exists.",
            )


def open_file_with_editor(window, filepath: str, editor: str = "gvim", use_popen: bool = False) -> None:
    """Open a file with the configured editor in a background task."""
    window._executor.submit(file_actions.open_file_with_editor, filepath, editor, use_popen)


def handle_csh(window) -> None:
    """Open the shell file for the selected target."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        return

    target = selected_targets[0]
    shell_file = file_actions.get_shell_file(window.combo_sel, target)

    if shell_file:
        window._open_file_with_editor(shell_file)
    else:
        logger.warning(f"Shell file not found for target: {target}")


def handle_log(window) -> None:
    """Open the log file for the selected target."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        return

    target = selected_targets[0]
    log_file = file_actions.get_log_file(window.combo_sel, target)

    if log_file:
        window._open_file_with_editor(log_file, use_popen=True)
    else:
        logger.warning(f"Log file not found for target: {target}")


def handle_cmd(window) -> None:
    """Open the command file for the selected target."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        return

    target = selected_targets[0]
    cmd_file = file_actions.get_cmd_file(window.combo_sel, target)

    if cmd_file:
        window._open_file_with_editor(cmd_file)
    else:
        logger.warning(f"Command file not found for target: {target}")


def create_tune(window) -> None:
    """Create a tune file from tunesource entries and open it."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not window.combo_sel or len(selected_targets) != 1:
        QMessageBox.information(window, "Info", "Select exactly one target to create tune.")
        return

    target = selected_targets[0]
    candidates = window.get_tune_candidates_from_cmd(window.combo_sel, target)
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
            window.show_notification(
                "Tune",
                f"Created tune file: {os.path.basename(tune_file)}",
                "success",
            )
        else:
            window.show_notification(
                "Tune",
                f"Tune file already exists: {os.path.basename(tune_file)}",
                "info",
            )

        window._invalidate_tune_cache(window.combo_sel, target)
        window._refresh_tune_cells_for_target(target)
        window._open_tune_file(tune_file)
    except Exception as exc:
        logger.error(f"Failed to create tune file {tune_file}: {exc}")
        QMessageBox.warning(
            window,
            "Warning",
            f"Failed to create tune file:\n{tune_file}\n\n{exc}",
        )


def handle_tune(window) -> None:
    """Open a tune file for the selected target."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        return

    target = selected_targets[0]
    tune_files = window.get_tune_files(window.combo_sel, target)

    if not tune_files:
        QMessageBox.information(window, "Info", f"No tune file found for: {target}")
        return

    if len(tune_files) == 1:
        window._open_tune_file(tune_files[0][1])
        return

    dialog = SelectTuneDialog(target, tune_files, window)
    if dialog.exec_() == QDialog.Accepted:
        selected = dialog.get_selected_tune()
        if selected:
            window._open_tune_file(selected[1])


def open_tune_file(window, tune_file) -> None:
    """Open a tune file with the configured editor."""
    window._open_file_with_editor(tune_file)


def copy_tune_to_runs(window) -> None:
    """Copy selected tune files to other runs."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        return

    target = selected_targets[0]
    tune_files = window.get_tune_files(window.combo_sel, target)

    if not tune_files:
        QMessageBox.information(window, "Info", f"No tune file found for: {target}")
        return

    available_runs = run_repository.list_available_runs(
        window.run_base_dir if hasattr(window, "run_base_dir") else ""
    )
    if not available_runs:
        QMessageBox.warning(window, "Warning", "No other runs available")
        return

    current_run = os.path.basename(window.combo_sel) if os.path.isabs(window.combo_sel) else window.combo_sel

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
        window.run_base_dir if hasattr(window, "run_base_dir") else "",
        target,
    )
    total_success = result["total_success"]

    for run in selected_runs:
        run_dir = os.path.join(window.run_base_dir, run) if hasattr(window, "run_base_dir") else run
        window._invalidate_tune_cache(run_dir, target)

    tune_names = ", ".join([suffix for suffix, _ in selected_tunes])
    QMessageBox.information(
        window,
        "Copy Complete",
        f"Copied {len(selected_tunes)} tune file(s) ({tune_names})\nto {total_success}/{len(selected_runs)} runs",
    )


def open_terminal(window) -> None:
    """Open a terminal in the current run directory."""
    if not window.combo_sel:
        return

    window._executor.submit(file_actions.open_terminal, window.combo_sel)


def retrace_tab(window, inout) -> None:
    """Execute trace filtering in place for the selected target."""
    selected_targets = window._exit_search_mode_and_get_targets()
    if not selected_targets or not window.combo_sel:
        logger.warning("No target selected for trace")
        return

    selected_target = selected_targets[0]
    logger.info(f"Trace {inout} for target: {selected_target}")

    related_targets = window.get_retrace_target(selected_target, inout)
    if selected_target not in related_targets:
        if inout == "in":
            related_targets.append(selected_target)
        else:
            related_targets.insert(0, selected_target)

    if not related_targets:
        logger.info("No dependencies found.")
        return

    window.filter_tree_by_targets(set(related_targets))

    direction = "Up" if inout == "in" else "Down"
    label_text = f"Trace {direction}: {selected_target}"
    window._apply_tab_state(view_tabs.get_trace_tab_state(label_text))
