"""Narrow action-controller access to MainWindow dependencies."""

from __future__ import annotations


class ActionWindowBridge:
    """Expose only the MainWindow surface used by action-controller flows."""

    def __init__(self, window):
        self._window = window

    @property
    def run_base_dir(self) -> str:
        """Return the configured run base directory."""
        return self._window.run_base_dir

    @property
    def is_all_status_view(self) -> bool:
        """Return whether the window is in all-status overview mode."""
        return bool(self._window.is_all_status_view)

    @property
    def combo_sel(self) -> str:
        """Return the currently selected run directory path."""
        return self._window.combo_sel

    @property
    def model(self):
        """Return the shared tree model."""
        return self._window.model

    def current_run_name(self) -> str:
        """Return the current combo-box run selection."""
        return self._window.combo.currentText()

    def is_search_mode_active(self) -> bool:
        """Return whether the main tree is currently filtered by search."""
        return bool(self._window.is_search_mode)

    def get_selected_targets(self):
        """Return the current selected target names."""
        return self._window.get_selected_targets()

    def get_selected_action_targets(self):
        """Return actionable targets from the current selection."""
        return self._window.get_selected_action_targets()

    def build_search_context(self, selected_targets=None):
        """Capture the current search context for action refresh flows."""
        return self._window._build_search_context(selected_targets)

    def clear_search_ui_state(self) -> None:
        """Clear the visible search widgets without rebuilding the tree."""
        self._window._clear_search_ui_state()

    def rebuild_main_tree_now(self) -> None:
        """Rebuild the main tree immediately."""
        self._window._rebuild_main_tree_now()

    def select_targets_in_tree(self, target_names) -> None:
        """Restore selection in the rebuilt main tree."""
        self._window._select_targets_in_tree(target_names)

    def build_status_cache(self, run_name: str) -> None:
        """Refresh cached run status data."""
        self._window._build_status_cache(run_name)

    def filter_tree(self, text: str) -> None:
        """Run the existing tree filter flow."""
        self._window.filter_tree(text)

    def restore_scroll_value(self, value: int) -> None:
        """Restore the current tree scroll position."""
        self._window.tree.verticalScrollBar().setValue(value)

    def submit_background(self, func, *args) -> None:
        """Submit one background task to the shared executor."""
        self._window._executor.submit(func, *args)

    def clear_tree_selection(self) -> None:
        """Clear the current tree selection."""
        self._window.tree.clearSelection()

    def notify(self, title: str, message: str, notification_type: str) -> None:
        """Show a standard notification through the shared window path."""
        self._window.show_notification(title, message, notification_type)

    def save_bsub_param(self, run_dir: str, target: str, param_type: str, value: str) -> bool:
        """Persist one BSUB parameter edit through the window owner."""
        return self._window.save_bsub_param(run_dir, target, param_type, value)

    def set_model_data(self, index, value) -> None:
        """Update the shared tree model at one index."""
        self._window.model.setData(index, value)

    def append_ui_log(
        self,
        level: str,
        source: str,
        message: str,
        command: str = "",
        details: str = "",
    ) -> None:
        """Append a structured entry to the GUI session log when available."""
        if hasattr(self._window, "append_ui_log"):
            self._window.append_ui_log(level, source, message, command=command, details=details)

    def show_embedded_terminal_panel(self, run_dir: str) -> bool:
        """Open the embedded terminal panel when supported."""
        if hasattr(self._window, "show_embedded_terminal_panel"):
            return self._window.show_embedded_terminal_panel(run_dir)
        return False

    def embedded_terminal_status_message(self) -> str:
        """Return the current embedded-terminal status message."""
        if hasattr(self._window, "get_embedded_terminal_status_message"):
            return self._window.get_embedded_terminal_status_message()
        return ""

    def open_file_with_editor(self, filepath: str, editor: str = "gvim", use_popen: bool = False) -> None:
        """Open a file with the window-managed editor flow."""
        self._window._open_file_with_editor(filepath, editor=editor, use_popen=use_popen)

    def get_tune_candidates_from_cmd(self, target: str):
        """Return tune candidates for the current run and target."""
        return self._window.get_tune_candidates_from_cmd(self.combo_sel, target)

    def get_tune_files(self, target: str):
        """Return tune files for the current run and target."""
        return self._window.get_tune_files(self.combo_sel, target)

    def invalidate_tune_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate cached tune data for one run or target."""
        self._window._invalidate_tune_cache(run_dir, target_name)

    def refresh_tune_cells_for_target(self, target: str) -> None:
        """Refresh tune-related tree cells for one target."""
        self._window._refresh_tune_cells_for_target(target)

    def open_tune_file(self, tune_file: str) -> None:
        """Open one tune file through the window-managed flow."""
        self._window._open_tune_file(tune_file)

    def get_retrace_target(self, target: str, direction: str):
        """Return retrace targets for the current target and direction."""
        return self._window.get_retrace_target(target, direction)

    def filter_tree_by_targets(self, targets) -> None:
        """Filter the tree to the provided target set."""
        self._window.filter_tree_by_targets(targets)

    def apply_tab_state(self, tab_state: dict) -> None:
        """Apply one precomputed tab-state payload."""
        self._window._apply_tab_state(tab_state)
