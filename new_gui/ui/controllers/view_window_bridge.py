"""Slim view-controller bridge exposing only required MainWindow surface."""

from __future__ import annotations

from new_gui.services import view_state
from new_gui.ui.controllers import output_controller, runtime_controller


class ViewWindowBridge:
    """Provide a narrow adapter between view-controller flows and MainWindow."""

    def __init__(self, window):
        self._window = window

    @property
    def run_base_dir(self):
        return self._window.run_base_dir

    @property
    def combo_sel(self):
        return self._window.combo_sel

    @combo_sel.setter
    def combo_sel(self, value):
        self._window.combo_sel = value

    @property
    def is_all_status_view(self):
        return bool(self._window.is_all_status_view)

    @is_all_status_view.setter
    def is_all_status_view(self, value):
        self._window.is_all_status_view = value

    @property
    def main_tree_visible_columns(self):
        return self._window._main_tree_visible_columns

    @property
    def cached_targets_by_level(self):
        return self._window.cached_targets_by_level

    @cached_targets_by_level.setter
    def cached_targets_by_level(self, value):
        self._window.cached_targets_by_level = value

    @property
    def model(self):
        return self._window.model

    @property
    def tree(self):
        return self._window.tree

    @property
    def colors(self):
        return self._window.colors

    def tab_label_text(self):
        return self._window.tab_label.text() if hasattr(self._window, "tab_label") else ""

    def header_filter_text(self):
        return self._window.header.get_filter_text() if hasattr(self._window, "header") else ""

    def header_filter_options(self):
        if hasattr(self._window, "header") and hasattr(self._window.header, "get_filter_options"):
            return self._window.header.get_filter_options()
        return {}

    def restore_normal_view(self):
        self._window.restore_normal_view()

    def set_filtered_main_view_tab_state(self):
        self._window._set_filtered_main_view_tab_state()

    def restore_main_view_snapshot(self):
        return self._window._restore_main_view_snapshot()

    def capture_search_view_snapshot(self):
        self._window._capture_search_view_snapshot()

    def restore_search_view_snapshot(self):
        return self._window._restore_search_view_snapshot()

    def invalidate_search_view_snapshot(self):
        self._window._invalidate_search_view_snapshot()

    def has_search_view_snapshot(self):
        return bool(getattr(self._window, "_search_view_snapshot", None))

    def search_view_snapshot(self):
        return getattr(self._window, "_search_view_snapshot", None)

    def populate_data(self, force_rebuild=False):
        self._window.populate_data(force_rebuild=force_rebuild)

    def clear_trace_filter(self):
        view_state.clear_trace_filter(self._window.tree, self._window.model)

    def filter_tree(self, text):
        self._window.filter_tree(text)

    def filter_tree_by_targets(self, targets):
        self._window.filter_tree_by_targets(targets)

    def apply_status_filter(self, status):
        self._window._apply_status_filter(status)

    def hide_tree(self):
        self._window.tree.hide()

    def hide_tab_bar(self):
        self._window.tab_bar.hide()

    def set_search_mode(self, active):
        self._window.is_search_mode = bool(active)

    def clear_model(self):
        self._window.model.clear()

    def current_run_name(self):
        return self._window.combo.currentText()

    def parse_dependency_file(self, run_name):
        return self._window.parse_dependency_file(run_name)

    def parse_collapsible_target_groups(self, run_name):
        return self._window.parse_collapsible_target_groups(run_name)

    def set_cached_target_data(self, run_name, targets_by_level, collapsible_groups):
        self._window.cached_targets_by_level = targets_by_level
        self._window.cached_collapsible_target_groups = collapsible_groups
        self._window._cached_collapsible_target_groups_run = run_name

    def set_tree_updates_enabled(self, enabled):
        self._window.tree.setUpdatesEnabled(enabled)

    def reset_main_tree_model(self):
        self._window._reset_main_tree_model()

    def build_display_level_groups(self, grouped_targets, run_name=None):
        return self._window._build_display_level_groups(grouped_targets, run_name=run_name)

    def append_target_groups_to_model(self, display_groups, run_name=None, status_value=None):
        self._window._append_target_groups_to_model(
            display_groups,
            run_name=run_name,
            status_value=status_value,
        )

    def expand_tree_all(self):
        self._window.tree.expandAll()

    def capture_main_view_snapshot(self):
        self._window._capture_main_view_snapshot()

    def get_retrace_target(self, target_name, direction):
        return self._window.get_retrace_target(target_name, direction)

    def show_notification(self, title, message, notification_type):
        self._window.show_notification(title, message, notification_type)

    def set_all_status_tab_state(self):
        self._window._set_all_status_tab_state()

    def populate_all_status_overview(self, overview_rows):
        self._window._populate_all_status_overview(overview_rows)

    def apply_all_status_column_widths(self):
        self._window._apply_all_status_column_widths()

    def update_column_visibility_control_state(self):
        self._window._update_column_visibility_control_state()

    def activate_selected_run_view(self, current_run, invalidate_snapshot=True):
        self._window._activate_selected_run_view(current_run, invalidate_snapshot=invalidate_snapshot)

    def invalidate_main_view_snapshot(self):
        self._window._invalidate_main_view_snapshot()

    def set_main_run_tab_state(self):
        self._window._set_main_run_tab_state()

    def build_status_cache(self, run_name):
        self._window._build_status_cache(run_name)

    def apply_main_tree_column_visibility(self, visible_columns, save_state=False):
        self._window._apply_main_tree_column_visibility(visible_columns, save_state=save_state)

    def has_status_watcher(self):
        return hasattr(self._window, "status_watcher")

    def setup_status_watcher(self):
        self._window.setup_status_watcher()

    def has_tune_watcher(self):
        return hasattr(self._window, "tune_watcher")

    def setup_tune_watcher(self):
        self._window.setup_tune_watcher()

    def pause_runtime_observers(self):
        runtime_controller.pause_runtime_observers(self._window)

    def resume_runtime_observers(self):
        runtime_controller.resume_runtime_observers(self._window)

    def runtime_observers_paused(self):
        return runtime_controller.runtime_observers_paused(self._window)

    def mark_runtime_refresh_pending(self):
        runtime_controller.mark_runtime_refresh_pending(self._window)

    def update_status_bar(self):
        self._window.update_status_bar()

    def refresh_xmeta_background(self, run_dir=None):
        if hasattr(self._window, "refresh_xmeta_background"):
            self._window.refresh_xmeta_background(run_dir=run_dir, announce=False)

    def is_terminal_follow_run_enabled(self):
        return output_controller.is_terminal_follow_run_enabled(self._window)

    def sync_embedded_terminal_run_dir(self, run_dir):
        return output_controller.sync_embedded_terminal_run_dir(self._window, run_dir)

    def build_current_view_restore_plan(self, scroll_value):
        return self._window._build_current_view_restore_plan(scroll_value)

    def restore_view_from_plan(self, restore_plan):
        return self._window._restore_view_from_plan(restore_plan)

    def restore_scroll_value(self, value):
        self._window.tree.verticalScrollBar().setValue(value)

    def current_scroll_value(self):
        return self._window.tree.verticalScrollBar().value()

    def apply_adaptive_target_column_width(self):
        self._window._apply_adaptive_target_column_width()

    def expand_tree_default(self):
        self._window.expand_tree_default()

    def get_target_status(self, run_name, target_name):
        return self._window.get_target_status(run_name, target_name)

    def get_target_times(self, run_name, target_name):
        return self._window.get_target_times(run_name, target_name)

    def get_bsub_params(self, run_dir, target_name):
        return self._window.get_bsub_params(run_dir, target_name)

    def invalidate_bsub_cache(self, run_dir=None, target_name=None):
        self._window._invalidate_bsub_cache(run_dir, target_name)

    def get_tune_files(self, run_dir, target_name):
        return self._window.get_tune_files(run_dir, target_name)

    def invalidate_tune_cache(self, run_dir=None, target_name=None):
        self._window._invalidate_tune_cache(run_dir, target_name)

    def consume_pending_tune_refresh(self):
        pending = bool(getattr(self._window, "_pending_tune_refresh", False))
        self._window._pending_tune_refresh = False
        return pending

    def minimum_size_hint_width(self):
        return self._window.minimumSizeHint().width()

    def resize_window(self, width, height):
        self._window.resize(width, height)

    def tab_close_show_callback(self):
        if hasattr(self._window, "tab_close_btn"):
            return self._window.tab_close_btn.show
        return None

    def apply_tab_state(self, tab_state):
        self._window._apply_tab_state(tab_state)

    def set_tab_label(self, text):
        if hasattr(self._window, "tab_label"):
            self._window.tab_label.setText(text)

    def set_tab_label_style(self, style_sheet):
        if hasattr(self._window, "tab_label"):
            self._window.tab_label.setStyleSheet(style_sheet)

    def set_tab_close_button_visible(self, visible):
        if not hasattr(self._window, "tab_close_btn"):
            return
        if visible:
            self._window.tab_close_btn.show()
        else:
            self._window.tab_close_btn.hide()
