"""Narrow view-controller access to MainWindow dependencies."""

from __future__ import annotations

import os

from new_gui.services import view_state
from new_gui.ui.controllers import output_controller


class ViewWindowBridge:
    """Expose only the MainWindow surface used by view-controller flows."""

    def __init__(self, window):
        self._window = window

    @property
    def run_base_dir(self) -> str:
        """Return the configured run base directory."""
        return self._window.run_base_dir

    @property
    def combo_sel(self) -> str:
        """Return the active run directory selection."""
        return self._window.combo_sel

    @combo_sel.setter
    def combo_sel(self, value: str) -> None:
        """Update the active run directory selection."""
        self._window.combo_sel = value

    @property
    def is_all_status_view(self) -> bool:
        """Return whether the window is in all-status overview mode."""
        return bool(self._window.is_all_status_view)

    @is_all_status_view.setter
    def is_all_status_view(self, value: bool) -> None:
        """Update all-status overview mode."""
        self._window.is_all_status_view = value

    @property
    def main_tree_visible_columns(self):
        """Return the persisted visible main-tree columns."""
        return self._window._main_tree_visible_columns

    @property
    def cached_targets_by_level(self):
        """Return the cached dependency structure for the active run."""
        return self._window.cached_targets_by_level

    @cached_targets_by_level.setter
    def cached_targets_by_level(self, value) -> None:
        """Update the cached dependency structure for the active run."""
        self._window.cached_targets_by_level = value

    @property
    def model(self):
        """Return the shared tree model."""
        return self._window.model

    @property
    def tree(self):
        """Return the shared main tree widget."""
        return self._window.tree

    @property
    def colors(self):
        """Return the current status-color mapping."""
        return self._window.colors

    def tab_label_text(self) -> str:
        """Return the current tab label text."""
        if hasattr(self._window, "tab_label"):
            return self._window.tab_label.text()
        return ""

    def header_filter_text(self) -> str:
        """Return the current header filter text."""
        if hasattr(self._window, "header"):
            return self._window.header.get_filter_text()
        return ""

    def restore_normal_view(self) -> None:
        """Restore the normal single-run view."""
        self._window.restore_normal_view()

    def apply_tab_state(self, tab_state: dict) -> None:
        """Apply one precomputed tab-state payload."""
        self._window._apply_tab_state(tab_state)

    def set_filtered_main_view_tab_state(self) -> None:
        """Reset the tab appearance for an in-place filtered view."""
        self._window._set_filtered_main_view_tab_state()

    def restore_main_view_snapshot(self) -> bool:
        """Restore the cached main-view snapshot if available."""
        return self._window._restore_main_view_snapshot()

    def populate_data(self, force_rebuild: bool = False) -> None:
        """Populate or rebuild the current run view."""
        self._window.populate_data(force_rebuild=force_rebuild)

    def clear_trace_filter(self) -> None:
        """Clear the current trace filter from the main tree."""
        view_state.clear_trace_filter(self._window.tree, self._window.model)

    def filter_tree(self, text: str) -> None:
        """Run the standard tree text-filter flow."""
        self._window.filter_tree(text)

    def filter_tree_by_targets(self, targets) -> None:
        """Filter the tree to one explicit target set."""
        self._window.filter_tree_by_targets(targets)

    def apply_status_filter(self, status: str) -> None:
        """Apply the current status filter flow."""
        self._window._apply_status_filter(status)

    def hide_tree(self) -> None:
        """Hide the main tree widget."""
        self._window.tree.hide()

    def hide_tab_bar(self) -> None:
        """Hide the floating tab bar widget."""
        self._window.tab_bar.hide()

    def set_search_mode(self, active: bool) -> None:
        """Update the window search-mode flag."""
        self._window.is_search_mode = bool(active)

    def clear_model(self) -> None:
        """Clear the current item model."""
        self._window.model.clear()

    def current_run_name(self) -> str:
        """Return the current combo-box run selection."""
        return self._window.combo.currentText()

    def combo_run_names(self):
        """Return all visible combo-box run labels."""
        combo = self._window.combo
        return [combo.itemText(index) for index in range(combo.count())]

    def is_combo_enabled(self) -> bool:
        """Return whether the run combo currently accepts interaction."""
        return self._window.combo.isEnabled()

    def set_combo_run_names(self, run_names, selected_run_name: str = "") -> str:
        """Replace combo-box contents while preserving one preferred selection."""
        combo = self._window.combo
        previous_state = combo.blockSignals(True)
        combo.clear()

        effective_selection = ""
        if run_names:
            combo.addItems(run_names)
            combo.setEnabled(True)
            effective_selection = (
                selected_run_name if selected_run_name in run_names else run_names[0]
            )
            combo.setCurrentIndex(combo.findText(effective_selection))
        else:
            combo.addItem("No runs found")
            combo.setEnabled(False)

        combo.blockSignals(previous_state)
        return effective_selection

    @staticmethod
    def current_working_run_name() -> str:
        """Return the current working directory basename."""
        return os.path.basename(os.getcwd())

    def ensure_cached_targets(self) -> None:
        """Populate run-level target caches when they are currently empty."""
        if getattr(self._window, "cached_targets_by_level", None):
            return
        current_run = self.current_run_name()
        if not current_run or current_run == "No runs found":
            return
        self._window.cached_targets_by_level = self._window.parse_dependency_file(current_run)
        self._window.cached_collapsible_target_groups = self._window.parse_collapsible_target_groups(current_run)
        self._window._cached_collapsible_target_groups_run = current_run

    def parse_dependency_file(self, run_name: str):
        """Parse the dependency file for the provided run."""
        return self._window.parse_dependency_file(run_name)

    def parse_collapsible_target_groups(self, run_name: str):
        """Parse collapsible target groups for the provided run."""
        return self._window.parse_collapsible_target_groups(run_name)

    def set_cached_target_data(self, run_name: str, targets_by_level, collapsible_groups) -> None:
        """Update the cached grouped-target state for one run."""
        self._window.cached_targets_by_level = targets_by_level
        self._window.cached_collapsible_target_groups = collapsible_groups
        self._window._cached_collapsible_target_groups_run = run_name

    def has_cached_targets(self) -> bool:
        """Return whether cached targets currently exist."""
        return bool(getattr(self._window, "cached_targets_by_level", None))

    def set_tree_updates_enabled(self, enabled: bool) -> None:
        """Enable or disable tree updates."""
        self._window.tree.setUpdatesEnabled(enabled)

    def reset_main_tree_model(self) -> None:
        """Reset the main tree model to its default schema."""
        self._window._reset_main_tree_model()

    def build_display_level_groups(self, grouped_targets, run_name: str = None):
        """Build display groups for the provided grouped targets."""
        return self._window._build_display_level_groups(grouped_targets, run_name=run_name)

    def append_target_groups_to_model(self, display_groups, run_name: str = None, status_value: str = None) -> None:
        """Append grouped targets into the current model."""
        self._window._append_target_groups_to_model(
            display_groups,
            run_name=run_name,
            status_value=status_value,
        )

    def expand_tree_all(self) -> None:
        """Expand all visible tree nodes."""
        self._window.tree.expandAll()

    def capture_main_view_snapshot(self) -> None:
        """Capture the current main-view snapshot."""
        self._window._capture_main_view_snapshot()

    def get_retrace_target(self, target_name: str, direction: str):
        """Return retrace targets for one target and direction."""
        return self._window.get_retrace_target(target_name, direction)

    def show_notification(self, title: str, message: str, notification_type: str) -> None:
        """Show a standard notification through the shared window path."""
        self._window.show_notification(title, message, notification_type)

    def set_all_status_tab_state(self) -> None:
        """Apply all-status tab presentation."""
        self._window._set_all_status_tab_state()

    def populate_all_status_overview(self, overview_rows) -> None:
        """Populate the all-status overview rows."""
        self._window._populate_all_status_overview(overview_rows)

    def apply_all_status_column_widths(self) -> None:
        """Apply all-status width policy."""
        self._window._apply_all_status_column_widths()

    def update_column_visibility_control_state(self) -> None:
        """Refresh column visibility control state."""
        self._window._update_column_visibility_control_state()

    def activate_selected_run_view(self, current_run: str, invalidate_snapshot: bool = True) -> None:
        """Activate one selected run view."""
        self._window._activate_selected_run_view(current_run, invalidate_snapshot=invalidate_snapshot)

    def invalidate_main_view_snapshot(self) -> None:
        """Invalidate the cached main-view snapshot."""
        self._window._invalidate_main_view_snapshot()

    def set_main_run_tab_state(self) -> None:
        """Apply the main-run tab presentation."""
        self._window._set_main_run_tab_state()

    def build_status_cache(self, run_name: str) -> None:
        """Refresh cached status data for the active run."""
        self._window._build_status_cache(run_name)

    def apply_main_tree_column_visibility(self, visible_columns, save_state: bool = False) -> None:
        """Apply visible-column state to the main tree."""
        self._window._apply_main_tree_column_visibility(visible_columns, save_state=save_state)

    def has_status_watcher(self) -> bool:
        """Return whether the window has an active status watcher object."""
        return hasattr(self._window, "status_watcher")

    def setup_status_watcher(self) -> None:
        """Refresh status watcher bindings."""
        self._window.setup_status_watcher()

    def update_status_bar(self) -> None:
        """Refresh the visible status bar."""
        self._window.update_status_bar()

    def refresh_xmeta_background(self, run_dir: str = None) -> None:
        """Reload and apply the run-backed XMETA background."""
        if hasattr(self._window, "refresh_xmeta_background"):
            self._window.refresh_xmeta_background(run_dir=run_dir, announce=False)

    def is_terminal_follow_run_enabled(self) -> bool:
        """Return whether the embedded terminal should follow run changes."""
        return output_controller.is_terminal_follow_run_enabled(self._window)

    def sync_embedded_terminal_run_dir(self, run_dir: str) -> bool:
        """Sync the embedded terminal session to the active run when enabled."""
        return output_controller.sync_embedded_terminal_run_dir(self._window, run_dir)

    def build_current_view_restore_plan(self, scroll_value: int) -> dict:
        """Build a restore plan for the current filtered view state."""
        return self._window._build_current_view_restore_plan(scroll_value)

    def restore_view_from_plan(self, restore_plan: dict) -> str:
        """Replay a previously built restore plan."""
        return self._window._restore_view_from_plan(restore_plan)

    def restore_scroll_value(self, value: int) -> None:
        """Restore the tree vertical scroll position."""
        self._window.tree.verticalScrollBar().setValue(value)

    def current_scroll_value(self) -> int:
        """Return the current tree vertical scroll position."""
        return self._window.tree.verticalScrollBar().value()

    def apply_adaptive_target_column_width(self) -> None:
        """Apply the target-column adaptive width policy."""
        self._window._apply_adaptive_target_column_width()

    def expand_tree_default(self) -> None:
        """Expand the main tree using the default expansion policy."""
        self._window.expand_tree_default()

    def get_target_status(self, run_name: str, target_name: str):
        """Return the target status for the provided run."""
        return self._window.get_target_status(run_name, target_name)

    def get_target_times(self, run_name: str, target_name: str):
        """Return the target start and end times for the provided run."""
        return self._window.get_target_times(run_name, target_name)

    def minimum_size_hint_width(self) -> int:
        """Return the current minimum size-hint width of the window."""
        return self._window.minimumSizeHint().width()

    def resize_window(self, width: int, height: int) -> None:
        """Resize the main window."""
        self._window.resize(width, height)

    def tab_close_show_callback(self):
        """Return the tab-close show callback when available."""
        if hasattr(self._window, "tab_close_btn"):
            return self._window.tab_close_btn.show
        return None

    def set_tab_label(self, text: str) -> None:
        """Set the current tab label text."""
        if hasattr(self._window, "tab_label"):
            self._window.tab_label.setText(text)

    def set_tab_label_style(self, style_sheet: str) -> None:
        """Set the current tab label style sheet."""
        if hasattr(self._window, "tab_label"):
            self._window.tab_label.setStyleSheet(style_sheet)

    def set_tab_close_button_visible(self, visible: bool) -> None:
        """Show or hide the tab close button."""
        if not hasattr(self._window, "tab_close_btn"):
            return
        if visible:
            self._window.tab_close_btn.show()
        else:
            self._window.tab_close_btn.hide()
