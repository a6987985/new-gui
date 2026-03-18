import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor

# Last Updated: 2026-03-05 19:00
warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from new_gui.config.settings import (
    DEBOUNCE_DELAY_MS,
    STATUS_COLORS,
    STATUS_CONFIG,
    logger,
)
from new_gui.ui.dialogs.dependency_graph import DependencyGraphDialog
from new_gui.ui.dialogs.params_editor import ParamsEditorDialog
from new_gui.services import file_actions
from new_gui.services import run_repository
from new_gui.services import search_flow
from new_gui.services import status_summary
from new_gui.services import tree_rows
from new_gui.services import tree_structure
from new_gui.services import view_tabs
from new_gui.services import view_state
from new_gui.ui.theme_runtime import ThemeManager
from new_gui.ui.builders import menu_builder, shortcut_builder, top_panel_builder, window_builder
from new_gui.ui.widgets.button_visibility_picker import ButtonVisibilityPicker
from new_gui.ui.widgets.column_visibility_picker import ColumnVisibilityPicker
from new_gui.ui.controllers import (
    action_controller,
    context_menu_controller,
    theme_controller,
    view_controller,
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QHeaderView, QMainWindow, QMenu


# ========== Status Bar ==========
class MainWindow(QMainWindow):
    def __init__(self):
        # Initialize core variables FIRST
        self._init_core_variables()

        # Initialize theme manager
        self.theme_manager = ThemeManager()

        # Detect run base directory
        self._detect_run_base_dir()

        # Call parent constructor
        super().__init__()

        # Initialize window
        self._init_window()

        # Initialize UI components
        self._init_menu_bar()
        self._init_central_widget()
        self._init_top_panel()

        # Expand tree initially
        self.expand_tree_default()

    def _init_core_variables(self):
        """Initialize core instance variables."""
        self.level_expanded = {}
        self.combo_sel = None
        self.cached_targets_by_level = {}
        self.cached_collapsible_target_groups = {}
        self._cached_collapsible_target_groups_run = ""
        self.is_tree_expanded = True
        self.is_search_mode = False
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.colors = {k: v["color"] for k, v in STATUS_CONFIG.items()}
        self._tune_files_cache = {}
        self._bsub_params_cache = {}
        self._main_view_snapshot = None
        self._column_resize_guard = False
        self._locked_main_tree_columns = {0, 1}
        self._main_tree_visible_columns = set(range(len(tree_rows.MAIN_TREE_HEADERS)))
        self._column_visibility_picker = None
        self._visible_top_buttons = set(top_panel_builder.DEFAULT_TOP_BUTTON_IDS)
        self._button_visibility_picker = None

    def _invalidate_tune_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate tune-file cache entries."""
        run_repository.invalidate_run_target_cache(
            self._tune_files_cache,
            run_dir,
            target_name,
        )

    def _invalidate_bsub_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate bsub-parameter cache entries."""
        run_repository.invalidate_run_target_cache(
            self._bsub_params_cache,
            run_dir,
            target_name,
        )

    def _invalidate_main_view_snapshot(self) -> None:
        """Drop the in-memory main-view snapshot."""
        self._main_view_snapshot = None

    def _capture_main_view_snapshot(self) -> None:
        """Capture the current main-view tree for fast restore."""
        current_run = self.combo.currentText()
        if not current_run or current_run == "No runs found":
            return
        self._main_view_snapshot = view_state.capture_main_view_snapshot(
            self.model,
            self.tree,
            current_run,
        )

    def _restore_main_view_snapshot(self) -> bool:
        """Restore the cached main-view snapshot if available."""
        return view_state.restore_main_view_snapshot(
            self.model,
            self.tree,
            self._main_view_snapshot,
            self.combo.currentText(),
            STATUS_COLORS,
            self.set_column_widths,
        )

    def _get_xmeta_background_color(self):
        """Return the configured XMETA background color, if any."""
        return theme_controller.get_xmeta_background_color(self)

    def _detect_run_base_dir(self):
        """Detect the run base directory based on environment."""
        if os.path.exists("mock_runs"):
            self.run_base_dir = "mock_runs"
        elif os.path.exists(".target_dependency.csh"):
            self.run_base_dir = ".."
            logger.info(f"Detected run in current directory. Setting base to parent: {os.path.abspath(self.run_base_dir)}")
        else:
            self.run_base_dir = "."

    def _init_window(self):
        """Initialize window properties and animation."""
        window_builder.init_window(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_top_action_buttons()
        self._apply_adaptive_target_column_width()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_adaptive_target_column_width)

    def _position_top_action_buttons(self):
        """Float the top action buttons independently from the main row layout."""
        window_builder.position_top_action_buttons(self)

    def _init_menu_bar(self):
        """Initialize the menu bar."""
        menu_builder.init_menu_bar(self)

    def _init_central_widget(self):
        """Initialize the central widget and main layout."""
        window_builder.init_central_widget(self)

    def _init_top_panel(self):
        """Initialize the top control panel."""
        top_panel_builder.init_top_panel(self)

    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts"""
        shortcut_builder.setup_keyboard_shortcuts(self)

    def _focus_search(self):
        """Focus the search input - shows the embedded filter in header"""
        if hasattr(self, 'quick_search_input'):
            self.quick_search_input.setFocus()
            self.quick_search_input.selectAll()
        elif hasattr(self, 'header'):
            self.header.show_filter()

    def _set_quick_search_text(self, text):
        """Update the persistent search field without triggering another filter pass."""
        if hasattr(self, 'quick_search_input'):
            was_blocked = self.quick_search_input.blockSignals(True)
            self.quick_search_input.setText(text)
            self.quick_search_input.blockSignals(was_blocked)

    def _set_header_filter_text_silent(self, text):
        """Update the header search state without emitting filter_changed again."""
        if not hasattr(self, 'header'):
            return

        self.header._filter_text = text
        if self.header.filter_edit:
            was_blocked = self.header.filter_edit.blockSignals(True)
            self.header.filter_edit.setText(text)
            self.header.filter_edit.blockSignals(was_blocked)

    def _on_top_search_changed(self, text):
        """Keep the header search state in sync with the visible search field."""
        self._set_header_filter_text_silent(text)
        self.filter_tree(text)

    def _on_header_filter_changed(self, text):
        """Mirror header search edits back to the visible search field."""
        self._set_quick_search_text(text)
        self.filter_tree(text)

    def _refresh_view(self):
        """Refresh the current view"""
        current_run = self.combo.currentText()
        if current_run and current_run != "No runs found":
            self._build_status_cache(current_run)
            self.populate_data()
            self.show_notification("Refresh", f"Refreshed view for {current_run}", "info")

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        theme_controller.toggle_theme(self)

    def _copy_selected_target(self):
        """Copy selected target name to clipboard"""
        action_controller.copy_selected_target(self)

    def apply_theme(self, theme_name):
        """Apply a theme to the application"""
        theme_controller.apply_theme(self, theme_name)

    def show_notification(self, title, message, notification_type="info"):
        """Show a notification message"""
        if hasattr(self, '_notification_manager'):
            self._notification_manager.show_notification(title, message, notification_type)

    def update_status_bar(self):
        """Update the status bar with current statistics"""
        if not hasattr(self, '_status_bar'):
            return

        # Get current run
        current_run = self.combo.currentText()
        self._status_bar.update_run(current_run)

        # Always compute stats from the full run graph, not current filtered model.
        stats = self._compute_full_run_stats(current_run)

        self._status_bar.update_stats(stats)

        # Update connection status (always connected for file system)
        self._status_bar.update_connection(True)

    def _compute_full_run_stats(self, run_name):
        """Compute status statistics from the complete target set of a run."""
        if not run_name or run_name == "No runs found":
            return status_summary.build_empty_stats()

        targets_by_level = self.parse_dependency_file(run_name)
        return status_summary.compute_run_stats(
            targets_by_level,
            lambda target_name: self.get_target_status(run_name, target_name),
        )

    def close_tree_view(self):
        """Close the tree view (or clear active filtered view)."""
        view_controller.close_tree_view(self)

    def get_selected_targets(self):
        """Get currently selected targets from tree view."""
        return view_state.get_selected_targets(self.tree, self.model)

    def get_selected_action_targets(self):
        """Get actionable targets from tree selection for batch execute actions."""
        return view_state.get_selected_action_targets(self.tree, self.model)

    def _get_current_search_text(self) -> str:
        """Return the current search text from the header filter state."""
        if hasattr(self, 'header'):
            return self.header.get_filter_text()
        return ""

    def _select_targets_in_tree(self, target_names):
        """Select targets in the tree by their names.

        Args:
            target_names: List of target names to select
        """
        view_state.select_targets_in_tree(self.tree, self.model, target_names)

    def _build_search_context(self, selected_targets=None) -> dict:
        """Capture the current search mode, text, and selected targets."""
        targets = self.get_selected_targets() if selected_targets is None else selected_targets
        scroll_value = self.tree.verticalScrollBar().value() if hasattr(self, "tree") else 0
        return search_flow.build_search_context(
            self.is_search_mode,
            self._get_current_search_text(),
            targets,
            scroll_value=scroll_value,
        )

    def _rebuild_main_tree_now(self) -> None:
        """Rebuild the main tree immediately using the current run selection."""
        self.model.clear()
        self.populate_data()

    def _clear_search_ui_state(self) -> None:
        """Clear the visible and embedded search UI state without rebuilding."""
        if hasattr(self, 'header'):
            self._set_header_filter_text_silent("")
            self.header.hide_filter()
        self._set_quick_search_text("")
        self.is_search_mode = False

    def _get_selected_targets_keep_search(self):
        """Get selected targets while keeping search mode active.

        This method gets selected targets without exiting search mode.
        Used for operations that should maintain search state after execution.

        Returns:
            tuple: (selected_targets, search_context)
        """
        return action_controller.get_selected_targets_keep_search(self)

    def _refresh_after_action(self, search_context):
        """Refresh the view after an action, preserving search state if needed.

        Args:
            search_context: Captured search context from before the action
        """
        action_controller.refresh_after_action(self, search_context)

    def _exit_search_mode_and_get_targets(self):
        """Exit search mode if active and return selected targets.

        This method handles the transition from search mode to normal mode:
        1. Saves selected targets from search results
        2. Clears search filter and restores full tree
        3. Re-selects the saved targets in the restored tree
        4. Returns the list of selected target names

        Returns:
            list: Selected target names
        """
        return action_controller.exit_search_mode_and_get_targets(self)

    def _log_action_result(self, command: str, result: dict, include_returncode: bool = False) -> None:
        """Log the outcome of a shell action using the existing UI logging policy."""
        action_controller.log_action_result(
            self,
            command,
            result,
            include_returncode=include_returncode,
        )

    def start(self, action):
        """Execute flow action and refresh view (runs command in background thread)."""
        action_controller.start(self, action)

    def filter_tree(self, text):
        """Filter tree items based on text input.
        If text is empty, restore full hierarchy.
        If text is present, show FLAT list of matching items (no parents).
        """
        view_controller.filter_tree(self, text)

    def toggle_tree_expansion(self):
        """Toggle between Expand All and Collapse All"""
        if self.is_tree_expanded:
            self.tree.collapseAll()
        else:
            self.expand_tree_default()
        self.is_tree_expanded = not self.is_tree_expanded

    def expand_tree_default(self):
        """Expand the tree while keeping synthetic generic groups collapsed."""
        view_state.expand_all_except_groups(self.tree, self.model)

    def _filter_tree_by_status_flat(self, status):
        """Show status-filtered targets using main-view tree hierarchy."""
        return view_controller.filter_tree_by_status_flat(self, status)

    def _apply_status_filter(self, status, update_tab=True):
        """Apply in-place status filter to the target tree."""
        view_controller.apply_status_filter(self, status, update_tab=update_tab)

    def on_status_badge_double_clicked(self, status):
        """Handle status badge double-click from the bottom status bar."""
        if self.is_all_status_view:
            self.show_notification("Status Filter", "Status badge filter is available in main target view only", "info")
            return
        self._apply_status_filter(status, update_tab=True)

    def scan_runs(self):
        """Scan the run base directory for valid run directories.
        A valid run directory contains a .target_dependency.csh file.
        """
        return run_repository.scan_runs(self.run_base_dir)

    def show_all_status(self):
        """Show status summary of all run directories in the TreeView.
        Displays: Run Directory, Latest Target, Status, Time Stamp
        """
        view_controller.show_all_status(self)

    def _apply_all_status_column_widths(self):
        """Use adaptive widths for the four-column all-status overview."""
        view_controller.apply_all_status_column_widths(self)

    def _get_header_min_widths(self):
        """Calculate per-column minimum widths to fully show header text."""
        return view_controller.get_header_min_widths(self)

    def _get_main_view_default_column_widths(self):
        """Return the default width plan for the main tree view."""
        return view_controller.get_main_view_default_column_widths(self)

    def _apply_adaptive_target_column_width(self):
        """Resize only the target column to absorb overall viewport size changes."""
        view_controller.apply_adaptive_target_column_width(self)

    def _fill_trailing_blank_with_last_column(self):
        """Expand the rightmost column when manual resize leaves trailing blank space."""
        view_controller.fill_trailing_blank_with_last_column(self)

    def _on_tree_header_section_resized(self, logical_index, old_size, new_size):
        """Keep the right edge flush after manual column resizing."""
        del old_size
        if self._column_resize_guard:
            return

        self._column_resize_guard = True
        try:
            header_min_widths = self._get_header_min_widths()
            min_width = header_min_widths.get(logical_index, 0)
            if min_width > 0 and new_size < min_width:
                self.tree.setColumnWidth(logical_index, min_width)
            self._fill_trailing_blank_with_last_column()
        finally:
            self._column_resize_guard = False

    def _is_main_tree_schema_active(self) -> bool:
        """Return whether the current model is the standard main-tree schema."""
        if not hasattr(self, "model"):
            return False
        expected_headers = tree_rows.MAIN_TREE_HEADERS
        if self.model.columnCount() < len(expected_headers):
            return False
        for index, header in enumerate(expected_headers):
            if str(self.model.headerData(index, Qt.Horizontal) or "").strip().lower() != header:
                return False
        return True

    def _get_visible_main_tree_columns(self):
        """Return currently visible main-tree columns."""
        visible_columns = set()
        for column in range(min(self.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS))):
            if not self.tree.isColumnHidden(column):
                visible_columns.add(column)
        return visible_columns

    def _apply_main_tree_column_visibility(self, visible_columns, save_state=True):
        """Apply persisted main-tree column visibility to the tree widget."""
        normalized_columns = set(int(column) for column in (visible_columns or []))
        normalized_columns.update(self._locked_main_tree_columns)
        max_columns = min(self.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS))
        normalized_columns = {column for column in normalized_columns if 0 <= column < max_columns}

        if save_state:
            self._main_tree_visible_columns = set(normalized_columns)

        if not self._is_main_tree_schema_active():
            return

        for column in range(max_columns):
            self.tree.setColumnHidden(column, column not in normalized_columns)

        self._apply_adaptive_target_column_width()
        self._fill_trailing_blank_with_last_column()

    def _update_column_visibility_control_state(self):
        """Enable the column-visibility control only for main-tree mode."""
        if not hasattr(self, "column_menu"):
            return
        enabled = self._is_main_tree_schema_active() and not getattr(self, "is_all_status_view", False)
        self.column_menu.menuAction().setEnabled(enabled)
        if not enabled and self._column_visibility_picker is not None:
            self._column_visibility_picker.hide()

    def _on_apply_column_visibility(self, visible_columns):
        """Apply user-picked visibility from the picker popup."""
        if getattr(self, "is_all_status_view", False):
            return
        self._apply_main_tree_column_visibility(visible_columns, save_state=True)
        if hasattr(self, "column_menu"):
            self.column_menu.hideTearOffMenu()
            self.column_menu.hide()
        if hasattr(self, "setting_menu"):
            self.setting_menu.hideTearOffMenu()
            self.setting_menu.hide()

    def _get_or_create_column_visibility_picker(self):
        """Return the shared column-visibility editor widget."""
        if self._column_visibility_picker is None:
            self._column_visibility_picker = ColumnVisibilityPicker(self)
            self._column_visibility_picker.apply_requested.connect(self._on_apply_column_visibility)
            self._column_visibility_picker.cancel_requested.connect(self._close_column_visibility_menu)
        return self._column_visibility_picker

    def _prepare_column_visibility_menu(self):
        """Refresh the column-visibility editor before opening the menu."""
        if getattr(self, "is_all_status_view", False) or not self._is_main_tree_schema_active():
            return
        picker = self._get_or_create_column_visibility_picker()
        visible_columns = self._get_visible_main_tree_columns() or set(self._main_tree_visible_columns)
        column_rows = [
            (index, self.model.headerData(index, Qt.Horizontal) or tree_rows.MAIN_TREE_HEADERS[index])
            for index in range(min(self.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS)))
        ]
        picker.set_columns(
            column_rows,
            visible_columns,
            self._locked_main_tree_columns,
        )
        picker.show()

    def _apply_top_button_visibility(self, visible_button_ids, save_state=True):
        """Apply persisted top-button visibility to the floating button area."""
        normalized_ids = top_panel_builder.normalize_visible_top_buttons(visible_button_ids)
        if save_state:
            self._visible_top_buttons = set(normalized_ids)
        top_panel_builder.rebuild_top_action_buttons(self)

    def _on_apply_button_visibility(self, visible_button_ids):
        """Apply user-picked top-button visibility from the picker popup."""
        self._close_button_visibility_menu()
        normalized_ids = list(visible_button_ids or [])
        QTimer.singleShot(
            0,
            lambda ids=normalized_ids: self._apply_top_button_visibility(ids, save_state=True),
        )

    def _get_or_create_button_visibility_picker(self):
        """Return the shared top-button visibility editor widget."""
        if self._button_visibility_picker is None:
            self._button_visibility_picker = ButtonVisibilityPicker(self)
            self._button_visibility_picker.apply_requested.connect(self._on_apply_button_visibility)
            self._button_visibility_picker.cancel_requested.connect(self._close_button_visibility_menu)
        return self._button_visibility_picker

    def _prepare_button_visibility_menu(self):
        """Refresh the top-button visibility editor before opening the menu."""
        picker = self._get_or_create_button_visibility_picker()
        picker.set_buttons(
            top_panel_builder.get_top_button_choices(),
            self._visible_top_buttons,
        )
        picker.show()

    def _close_button_visibility_menu(self):
        """Close the button-visibility menu hierarchy."""
        if hasattr(self, "button_menu"):
            self.button_menu.hide()
        if hasattr(self, "setting_menu"):
            self.setting_menu.hide()

    def _close_column_visibility_menu(self):
        """Close the column-visibility menu hierarchy."""
        if hasattr(self, "column_menu"):
            self.column_menu.hide()
        if hasattr(self, "setting_menu"):
            self.setting_menu.hide()

    def _get_main_view_default_window_width(self):
        """Estimate the startup window width from the main-view column defaults."""
        return view_controller.get_main_view_default_window_width(self)

    def _apply_initial_window_width(self):
        """Resize the startup window to match the main-view default tree width."""
        view_controller.apply_initial_window_width(self)

    def restore_normal_view(self):
        """Restore the normal single-run TreeView from All Status view."""
        view_controller.restore_normal_view(self)

    def on_tree_double_clicked(self, index):
        """Handle double-click on tree view"""
        action_controller.on_tree_double_clicked(self, index)

    def build_dependency_graph(self, run_name):
        """
        Build dependency graph data from .target_dependency.csh file.

        Returns:
            dict with 'nodes', 'edges', and 'levels' for DependencyGraphDialog
        """
        graph_data = run_repository.build_dependency_graph(
            self.run_base_dir,
            run_name,
            getattr(self, "_status_cache", None),
        )
        logger.debug(
            f"Built graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges"
        )
        return graph_data

    def show_dependency_graph(self):
        """Show the dependency graph dialog for the current run."""
        current_run = self.combo.currentText()
        if not current_run or current_run == "No runs found":
            logger.warning("No run selected")
            return

        # Build graph data
        graph_data = self.build_dependency_graph(current_run)
        selected_targets = [] if getattr(self, "is_all_status_view", False) else self.get_selected_targets()
        initial_target = selected_targets[0] if selected_targets else None
        return_context = self._build_dependency_graph_return_context(current_run)

        # Show dialog
        dialog = DependencyGraphDialog(
            graph_data,
            self.colors,
            initial_target=initial_target,
            locate_target_callback=lambda target_name, context=return_context: self.locate_target_in_tree(
                target_name,
                context,
            ),
            parent=self,
        )
        dialog.exec_()

    def _build_dependency_graph_return_context(self, run_name: str) -> dict:
        """Capture the current tree context so graph navigation can return cleanly."""
        if not run_name or run_name == "No runs found":
            return {}

        scroll_value = self.tree.verticalScrollBar().value() if hasattr(self, "tree") else 0
        return {
            "run_name": run_name,
            "is_all_status_view": bool(getattr(self, "is_all_status_view", False)),
            "restore_plan": None if getattr(self, "is_all_status_view", False) else self._build_current_view_restore_plan(scroll_value),
        }

    def _target_matches_graph_return_context(self, target_name: str, run_name: str, return_context: dict) -> bool:
        """Return whether the target belongs to the captured tree context."""
        if not target_name or not run_name or not return_context or return_context.get("is_all_status_view"):
            return False

        restore_plan = return_context.get("restore_plan") or {"mode": "main"}
        mode = restore_plan.get("mode", "main")

        if mode == "main":
            return True
        if mode == "search":
            search_text = (restore_plan.get("search_text") or "").lower()
            return bool(search_text) and search_text in target_name.lower()
        if mode == "status":
            target_status = (self.get_target_status(run_name, target_name) or "").lower()
            return target_status == (restore_plan.get("status") or "").lower()
        if mode == "trace":
            trace_target = restore_plan.get("target_name", "")
            inout = restore_plan.get("inout")
            if not trace_target or not inout:
                return False
            run_dir = os.path.join(self.run_base_dir, run_name)
            related_targets = list(run_repository.get_retrace_targets(run_dir, trace_target, inout) or [])
            if trace_target not in related_targets:
                if inout == "in":
                    related_targets.append(trace_target)
                else:
                    related_targets.insert(0, trace_target)
            return target_name in set(related_targets)
        return False

    def _apply_dependency_graph_return_context(self, return_context: dict) -> None:
        """Restore the captured tree presentation before selecting a graph target."""
        restore_plan = (return_context or {}).get("restore_plan") or {"mode": "main"}
        mode = restore_plan.get("mode", "main")

        if mode == "trace":
            trace_target = restore_plan.get("target_name", "")
            direction = "Up" if restore_plan.get("inout") == "in" else "Down"
            self._apply_tab_state(view_tabs.get_trace_tab_state(f"Trace {direction}: {trace_target}"))
        elif mode == "status":
            status = restore_plan.get("status", "")
            self._apply_tab_state(view_tabs.get_status_tab_state(status))
        else:
            self._set_main_run_tab_state()

        if mode == "search":
            search_text = restore_plan.get("search_text", "")
            self._set_quick_search_text(search_text)
            self._set_header_filter_text_silent(search_text)
            self.is_search_mode = bool(search_text)
            if hasattr(self, "header"):
                self.header.show_filter()
        else:
            self._clear_search_ui_state()

        if mode != "main":
            self._restore_view_from_plan(restore_plan)

    def locate_target_in_tree(self, target_name: str, return_context: dict = None) -> None:
        """Restore the tree view and select the requested target from the graph."""
        current_run = (return_context or {}).get("run_name") or self.combo.currentText()
        if not current_run or current_run == "No runs found" or not target_name:
            return

        combo_index = self.combo.findText(current_run)
        run_changed = combo_index >= 0 and self.combo.currentIndex() != combo_index
        if run_changed:
            was_blocked = self.combo.blockSignals(True)
            self.combo.setCurrentIndex(combo_index)
            self.combo.blockSignals(was_blocked)

        preserve_context = self._target_matches_graph_return_context(target_name, current_run, return_context or {})
        used_main_view_fallback = False

        if run_changed or self.is_all_status_view:
            self._activate_selected_run_view(current_run, invalidate_snapshot=True)
            if preserve_context:
                self._apply_dependency_graph_return_context(return_context or {})
            else:
                used_main_view_fallback = not (return_context or {}).get("is_all_status_view", False)
        elif preserve_context:
            self._apply_dependency_graph_return_context(return_context or {})
        else:
            self._activate_selected_run_view(current_run, invalidate_snapshot=True)
            current_mode = ((return_context or {}).get("restore_plan") or {}).get("mode", "main")
            used_main_view_fallback = current_mode != "main"

        if used_main_view_fallback:
            self._clear_search_ui_state()
            self._set_main_run_tab_state()

        self._select_targets_in_tree([target_name])
        self.tree.setFocus()
        self.raise_()
        self.activateWindow()

        selected_targets = self.get_selected_targets()
        if target_name not in selected_targets:
            self.show_notification("Not Found", f"Target '{target_name}' was not found in the current tree", "warning")
        elif used_main_view_fallback:
            self.show_notification(
                "Locate In Tree",
                "Restored the main view because the selected target is outside the original graph-open filter.",
                "info",
            )

    def open_user_params(self):
        """Open user.params file for editing."""
        if not self.combo_sel or not os.path.exists(self.combo_sel):
            self.show_notification("Error", "No run selected or run directory not found", "error")
            return

        try:
            user_params_file, created = file_actions.ensure_user_params_file(self.combo_sel)
            if created:
                self.show_notification("Created", "Created new user.params file", "success")
        except Exception as e:
            self.show_notification("Error", f"Failed to create user.params: {e}", "error")
            return

        dialog = ParamsEditorDialog(user_params_file, "user", self)
        dialog.exec_()

    def open_tile_params(self):
        """Open tile.params file for viewing (read-only)."""
        if not self.combo_sel or not os.path.exists(self.combo_sel):
            self.show_notification("Error", "No run selected or run directory not found", "error")
            return

        tile_params_file = file_actions.get_tile_params_file(self.combo_sel)
        if not tile_params_file:
            self.show_notification("Not Found", f"tile.params file not found in current run", "warning")
            return

        dialog = ParamsEditorDialog(tile_params_file, "tile", self)
        dialog.exec_()

    def populate_run_combo(self):
        """Populate the combo box with available run directories."""
        runs = self.scan_runs()
        if runs:
            self.combo.addItems(runs)
            
            # Try to detect current run from working directory
            # If we are inside a run directory, the basename of cwd should match a run name
            current_cwd_name = os.path.basename(os.getcwd())
            
            logger.info(f"Current working directory basename: {current_cwd_name}")
            logger.info(f"Available runs: {runs}")
            
            if current_cwd_name in runs:
                index = self.combo.findText(current_cwd_name)
                if index >= 0:
                    self.combo.setCurrentIndex(index)
                    logger.info(f"Selected run: {current_cwd_name}")
            else:
                # Default to the first item if current cwd is not a valid run
                self.combo.setCurrentIndex(0)
                logger.info(f"Selected first run: {runs[0]}")
        else:
            # Fallback if no runs found
            self.combo.addItem("No runs found")
            self.combo.setEnabled(False)

    def parse_dependency_file(self, run_name):
        """Parse .target_dependency.csh file to extract target-level mappings.

        Returns:
            dict: Mapping of level number to list of target names
        """
        return run_repository.parse_dependency_file(self.run_base_dir, run_name)

    def parse_collapsible_target_groups(self, run_name):
        """Parse large timing/sorttiming target collections used for grouped display rows."""
        return run_repository.parse_collapsible_target_groups(self.run_base_dir, run_name)

    def _ensure_cached_collapsible_target_groups(self, run_name: str):
        """Load grouped display definitions for the active run when needed."""
        normalized_run = run_name or ""
        if (
            normalized_run
            and (
                self._cached_collapsible_target_groups_run != normalized_run
                or not self.cached_collapsible_target_groups
            )
        ):
            self.cached_collapsible_target_groups = self.parse_collapsible_target_groups(normalized_run)
            self._cached_collapsible_target_groups_run = normalized_run
        return self.cached_collapsible_target_groups

    def _build_display_level_groups(self, targets_by_level, run_name: str = None):
        """Build level/group/target display structure for the main tree."""
        current_run = run_name if run_name is not None else self.combo.currentText()
        collapsible_groups = self._ensure_cached_collapsible_target_groups(current_run)
        return tree_structure.build_level_display_groups(targets_by_level, collapsible_groups)

    def on_run_changed(self):
        """When combo box selection changes, rebuild tree with new run data."""
        view_controller.on_run_changed(self)

    def _init_top_panel_background(self):
        """Apply XMETA background overrides to container widgets when configured."""
        theme_controller.init_top_panel_background(self)



    def get_target_status(self, run_name: str, target_name: str) -> str:
        """Get status of a target by checking status files in run_dir/status/.

        Args:
            run_name: Name of the run directory.
            target_name: Name of the target to check.

        Returns:
            Status string (finish, running, failed, skip, scheduled, pending, or empty).
        """
        return run_repository.get_target_status(
            self.run_base_dir,
            run_name,
            target_name,
            getattr(self, "_status_cache", None),
        )

    def _build_status_cache(self, run_name):
        """Build a cache of all target statuses for a run (batch I/O optimization)"""
        self._status_cache = run_repository.build_status_cache(self.run_base_dir, run_name)

    def get_target_times(self, run_name: str, target_name: str) -> tuple:
        """Get start and end time from cache.

        Args:
            run_name: Name of the run directory.
            target_name: Name of the target.

        Returns:
            Tuple of (start_time, end_time) as strings, or ("", "") if not found.
        """
        return run_repository.get_target_times(
            run_name,
            target_name,
            getattr(self, "_status_cache", None),
        )

    def _reset_main_tree_model(self):
        """Reset the main target tree model with standard headers and widths."""
        tree_rows.reset_main_tree_model(self.model, self.set_column_widths)

    def _build_target_row_items(self, level_text, target_name: str, status_value: str = None, run_name: str = None) -> list:
        """Build one standard main-tree row for a target."""
        current_run = run_name if run_name is not None else self.combo.currentText()
        row_status = self.get_target_status(current_run, target_name) if status_value is None else status_value
        tune_files = self.get_tune_files(self.combo_sel, target_name)
        start_time, end_time = self.get_target_times(current_run, target_name)
        queue, cores, memory = self.get_bsub_params(self.combo_sel, target_name)
        return tree_rows.build_target_row_items(
            level_text,
            target_name,
            row_status,
            tune_files,
            start_time,
            end_time,
            queue,
            cores,
            memory,
            STATUS_COLORS,
        )

    def _build_container_row_items(
        self,
        level_text,
        label_text: str,
        row_kind: str,
        descendant_targets,
        status_value: str = "",
        status_key: str = "",
    ) -> list:
        """Build one synthetic main-tree row for a level or collapsible group container."""
        return tree_rows.build_container_row_items(
            level_text,
            label_text,
            row_kind,
            descendant_targets=descendant_targets,
            status_value=status_value,
            status_key=status_key,
            status_colors=STATUS_COLORS,
        )

    def _summarize_group_row_status(self, target_names, run_name: str = None, status_value: str = None):
        """Return display text and dominant status key for one synthetic group row."""
        current_run = run_name if run_name is not None else self.combo.currentText()
        if status_value is not None:
            normalized_status = (status_value or "").strip().lower()
            if not normalized_status:
                return "", ""
            return f"all {normalized_status}", normalized_status

        return status_summary.summarize_group_status(
            target_names,
            lambda target_name: self.get_target_status(current_run, target_name),
        )

    def _append_display_node_to_parent(self, parent_item, node: dict, run_name: str = None, status_value: str = None) -> int:
        """Append one display node and all descendants below an existing parent item."""
        node_kind = node.get("kind", tree_rows.ROW_KIND_TARGET)
        node_label = node.get("label", "")
        node_targets = list(node.get("targets", []) or [])

        if node_kind == tree_rows.ROW_KIND_TARGET:
            child_row = self._build_target_row_items(
                "",
                node.get("target_name", node_label),
                status_value=status_value,
                run_name=run_name,
            )
            parent_item.appendRow(child_row)
            return 1

        group_status_text, group_status_key = self._summarize_group_row_status(
            node_targets,
            run_name=run_name,
            status_value=status_value,
        )
        child_row = self._build_container_row_items(
            "",
            node_label,
            node_kind,
            node_targets,
            status_value=group_status_text,
            status_key=group_status_key,
        )
        parent_item.appendRow(child_row)

        appended_count = 0
        child_parent_item = child_row[0]
        for child_node in node.get("children", []):
            appended_count += self._append_display_node_to_parent(
                child_parent_item,
                child_node,
                run_name=run_name,
                status_value=status_value,
            )
        return appended_count

    def _split_level_anchor_target(self, child_nodes):
        """Return the top-level anchor target and remaining child nodes for one level."""
        ordered_nodes = list(child_nodes or [])
        if not ordered_nodes:
            return "", []

        first_node = ordered_nodes[0]
        if first_node.get("kind") == tree_rows.ROW_KIND_TARGET:
            return first_node.get("target_name", ""), ordered_nodes[1:]

        if first_node.get("kind") == tree_rows.ROW_KIND_GROUP:
            group_targets = list(first_node.get("targets", []) or [])
            if not group_targets:
                return "", ordered_nodes[1:]

            anchor_target = group_targets[0]
            remaining_targets = group_targets[1:]
            remaining_children = list(first_node.get("children", []) or [])[1:]
            remaining_nodes = []
            if remaining_targets and remaining_children:
                remaining_nodes.append(
                    {
                        "kind": tree_rows.ROW_KIND_GROUP,
                        "label": first_node.get("label", ""),
                        "target_name": "",
                        "targets": remaining_targets,
                        "children": remaining_children,
                    }
                )
            remaining_nodes.extend(ordered_nodes[1:])
            return anchor_target, remaining_nodes

        return "", ordered_nodes[1:]

    def _get_level_root_group_node(self, targets, child_nodes):
        """Return the top-level group node when one level is fully generic-grouped."""
        ordered_targets = list(targets or [])
        ordered_nodes = list(child_nodes or [])
        if len(ordered_nodes) != 1:
            return None

        first_node = ordered_nodes[0]
        if first_node.get("kind") != tree_rows.ROW_KIND_GROUP:
            return None

        group_targets = list(first_node.get("targets", []) or [])
        if not group_targets or len(group_targets) != len(ordered_targets):
            return None

        if group_targets != ordered_targets:
            return None

        return first_node

    def _append_target_groups_to_model(self, display_groups, run_name: str = None, status_value: str = None) -> int:
        """Append grouped display nodes to the model using the standard main-tree structure."""
        appended_target_count = 0
        for display_group in display_groups:
            level = display_group.get("level")
            targets = list(display_group.get("targets", []) or [])
            children = list(display_group.get("children", []) or [])

            if not targets or not children:
                continue

            level_root_group = self._get_level_root_group_node(targets, children)
            if level_root_group is not None:
                group_status_text, group_status_key = self._summarize_group_row_status(
                    level_root_group.get("targets", []),
                    run_name=run_name,
                    status_value=status_value,
                )
                parent_row = self._build_container_row_items(
                    str(level),
                    level_root_group.get("label", ""),
                    tree_rows.ROW_KIND_GROUP,
                    level_root_group.get("targets", []),
                    status_value=group_status_text,
                    status_key=group_status_key,
                )
                self.model.appendRow(parent_row)

                level_parent_item = parent_row[0]
                for child_node in level_root_group.get("children", []):
                    appended_target_count += self._append_display_node_to_parent(
                        level_parent_item,
                        child_node,
                        run_name=run_name,
                        status_value=status_value,
                    )
                continue

            anchor_target, remaining_children = self._split_level_anchor_target(children)
            if not anchor_target:
                anchor_target = targets[0]
                remaining_children = children

            parent_row = self._build_target_row_items(
                str(level),
                anchor_target,
                status_value=status_value,
                run_name=run_name,
            )
            self.model.appendRow(parent_row)
            appended_target_count += 1

            level_parent_item = parent_row[0]
            for child_node in remaining_children:
                appended_target_count += self._append_display_node_to_parent(
                    level_parent_item,
                    child_node,
                    run_name=run_name,
                    status_value=status_value,
                )

        return appended_target_count

    def _build_current_view_restore_plan(self, scroll_value: int) -> dict:
        """Describe the active filtered/tree mode so it can be replayed after rebuild."""
        return view_controller.build_current_view_restore_plan(self, scroll_value)

    def _restore_view_from_plan(self, restore_plan: dict) -> str:
        """Replay a previously captured filtered/tree mode."""
        return view_controller.restore_view_from_plan(self, restore_plan)

    def _apply_tab_state(self, tab_state: dict) -> None:
        """Apply a tab label/button presentation state."""
        view_controller.apply_tab_state(self, tab_state)

    def _set_main_run_tab_state(self) -> None:
        """Apply the default tab presentation for the normal single-run view."""
        view_controller.set_main_run_tab_state(self)

    def _set_filtered_main_view_tab_state(self) -> None:
        """Reset the in-place filtered tab back to the Main View appearance."""
        view_controller.set_filtered_main_view_tab_state(self)

    def _set_all_status_tab_state(self) -> None:
        """Apply the tab presentation for the all-status overview."""
        view_controller.set_all_status_tab_state(self)

    def _populate_all_status_overview(self, overview_rows) -> None:
        """Populate the tree model with the four-column all-status overview."""
        view_controller.populate_all_status_overview(self, overview_rows)

    def _activate_selected_run_view(self, current_run: str, invalidate_snapshot: bool = True) -> None:
        """Switch from overview/other run states back to the selected single-run view."""
        view_controller.activate_selected_run_view(
            self,
            current_run,
            invalidate_snapshot=invalidate_snapshot,
        )

    def populate_data(self, force_rebuild=False):
        """Populate or refresh the current run tree."""
        view_controller.populate_data(self, force_rebuild=force_rebuild)

    def setup_status_watcher(self):
        """Setup file system watcher for the current run's status directory."""
        if not self.combo_sel:
            return
        
        status_dir = os.path.join(self.combo_sel, "status")
        
        # Remove old watched directories
        if self.watched_status_dirs:
            old_dirs = list(self.watched_status_dirs)
            self.status_watcher.removePaths(old_dirs)
            self.watched_status_dirs.clear()
        
        # Add new status directory if it exists
        if os.path.exists(status_dir):
            self.status_watcher.addPath(status_dir)
            self.watched_status_dirs.add(status_dir)
            logger.debug(f"Now watching status directory: {status_dir}")
    
    def on_status_directory_changed(self, path):
        """Called when the status directory contents change (file added/removed)."""
        logger.debug(f"Status directory changed: {path}")

        # Use debounce timer to batch rapid changes
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(DEBOUNCE_DELAY_MS)

    def on_status_file_changed(self, path):
        """Called when a watched file is modified."""
        logger.debug(f"Status file changed: {path}")

        # Use debounce timer to batch rapid changes
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(DEBOUNCE_DELAY_MS)

    def change_run(self):
        """Refresh status timer callback - updates status/time for all visible targets"""
        view_controller.change_run(self)

    def get_start_end_time(self, tgt_track_file: str) -> tuple:
        """Get start and end time from target tracker file.

        Args:
            tgt_track_file: Base path for tracker files (without .start/.finished suffix).

        Returns:
            Tuple of (start_time, end_time) as formatted strings.
        """
        return run_repository.get_start_end_time(tgt_track_file)

    # ========== File Viewers ==========

    def _open_file_with_editor(self, filepath: str, editor: str = 'gvim', use_popen: bool = False) -> None:
        """Open file with editor in background thread.

        Args:
            filepath: Path to the file to open.
            editor: Editor command to use (default: gvim).
            use_popen: If True, use Popen for background execution; otherwise use run with timeout.
        """
        action_controller.open_file_with_editor(self, filepath, editor=editor, use_popen=use_popen)

    def handle_csh(self):
        """Open shell file for selected target (runs in background thread)"""
        action_controller.handle_csh(self)

    def handle_log(self):
        """Open log file for selected target (runs in background thread)"""
        action_controller.handle_log(self)

    def handle_cmd(self):
        """Open command file for selected target (runs in background thread)"""
        action_controller.handle_cmd(self)

    # ========== Tune File Management ==========

    def get_tune_files(self, run_dir: str, target_name: str) -> list:
        """Get all tune files for a target.

        Tune file naming: {run_dir}/tune/{target}/{target}.{suffix}.tcl

        Args:
            run_dir: Path to the run directory.
            target_name: Name of the target.

        Returns:
            List of (suffix, full_path) tuples, sorted by suffix.
        """
        return run_repository.get_tune_files(
            run_dir,
            target_name,
            self._tune_files_cache,
        )

    def get_tune_display(self, run_dir, target_name):
        """Get tune display string for tree view.
        Returns comma-separated suffixes or empty string
        """
        tune_files = self.get_tune_files(run_dir, target_name)
        if not tune_files:
            return ""
        return ", ".join([suffix for suffix, _ in tune_files])

    def get_tune_candidates_from_cmd(self, run_dir: str, target_name: str) -> list:
        """Parse tunesource entries from cmds/<target>.cmd.

        Args:
            run_dir: Path to run directory.
            target_name: Name of selected target.

        Returns:
            List of (display_name, full_path) tuples for tune files that can be created.
        """
        return run_repository.get_tune_candidates_from_cmd(run_dir, target_name)

    def _refresh_tune_cells_for_target(self, target_name: str) -> None:
        """Refresh tune column text and UserRole data for one target in tree model."""
        if not self.combo_sel or not hasattr(self, "model") or self.model is None:
            return

        tune_files = self.get_tune_files(self.combo_sel, target_name)
        tune_display = ", ".join([suffix for suffix, _ in tune_files]) if tune_files else ""

        def update_cells(target_item, tune_item):
            if not target_item or not tune_item:
                return
            if tree_rows.get_row_target_name(target_item) != target_name:
                return
            tune_item.setText(tune_display)
            tune_item.setData(tune_files, Qt.UserRole)

        def walk_rows(parent_item=None):
            row_count = parent_item.rowCount() if parent_item is not None else self.model.rowCount()
            for row_idx in range(row_count):
                row_items = tree_rows.get_row_items(self.model, row_idx, parent_item)
                update_cells(row_items[1] if len(row_items) > 1 else None, row_items[3] if len(row_items) > 3 else None)
                level_item = row_items[0] if row_items else None
                if level_item and level_item.hasChildren():
                    walk_rows(level_item)

        walk_rows()

    def create_tune(self):
        """Create a tune file from tunesource entries in cmds/<target>.cmd and open it."""
        action_controller.create_tune(self)

    # ========== BSUB Parameter Methods ==========

    def get_bsub_params(self, run_dir: str, target_name: str) -> tuple:
        """Parse bsub parameters from {run_dir}/make_targets/{target}.csh.

        Args:
            run_dir: Path to the run directory.
            target_name: Name of the target.

        Returns:
            Tuple of (queue, cores, memory), each can be 'N/A' if not found.
        """
        return run_repository.get_bsub_params(
            run_dir,
            target_name,
            self._bsub_params_cache,
        )

    def save_bsub_param(self, run_dir, target_name, param_type, new_value):
        """Save a single bsub parameter to the csh file.
        Args:
            run_dir: Run directory path
            target_name: Target name
            param_type: 'queue', 'cores', or 'memory'
            new_value: New value to set
        Returns: True if successful, False otherwise
        """
        if run_repository.save_bsub_param(run_dir, target_name, param_type, new_value):
            self._invalidate_bsub_cache(run_dir, target_name)
            logger.info(f"Updated {param_type} to {new_value} for {target_name}")
            return True
        return False

    def handle_tune(self):
        """Open tune file for selected target with gvim"""
        action_controller.handle_tune(self)

    def _open_tune_file(self, tune_file):
        """Open a tune file with gvim (runs in background thread)"""
        action_controller.open_tune_file(self, tune_file)

    def copy_tune_to_runs(self):
        """Copy tune file to selected runs"""
        action_controller.copy_tune_to_runs(self)

    def open_terminal(self):
        """Open terminal in current run directory (runs in background thread)"""
        action_controller.open_terminal(self)

    # ========== Context Menu Helpers ==========

    def _build_execute_menu(self, menu: QMenu) -> None:
        """Build the Execute submenu."""
        context_menu_controller.build_execute_menu(self, menu)

    def _build_file_menu(self, menu: QMenu) -> None:
        """Build the Files submenu."""
        context_menu_controller.build_file_menu(self, menu)

    def _build_tune_menu(self, menu: QMenu, selected_targets: list) -> None:
        """Build the Tune submenu."""
        context_menu_controller.build_tune_menu(self, menu, selected_targets)

    def _build_params_menu(self, menu: QMenu) -> None:
        """Build the Params submenu."""
        context_menu_controller.build_params_menu(self, menu)

    def _build_trace_menu(self, menu: QMenu) -> None:
        """Build the Trace submenu."""
        context_menu_controller.build_trace_menu(self, menu)

    def _build_copy_menu(self, menu: QMenu, single_target: bool, selected_targets: list) -> None:
        """Build the Copy submenu."""
        context_menu_controller.build_copy_menu(self, menu, single_target, selected_targets)

    # ========== Right-click Menu ==========

    def show_context_menu(self, position):
        """Show context menu on right-click with icons and grouping."""
        context_menu_controller.show_context_menu(self, position)

    def _copy_run_path(self):
        """Copy the current run path to clipboard"""
        context_menu_controller.copy_run_path(self)

    # ========== Trace Functionality ==========
    
    def get_retrace_target(self, target, inout):
        """Parse .target_dependency.csh to find related targets (upstream/downstream)"""
        return run_repository.get_retrace_targets(self.combo_sel, target, inout)

    def filter_tree_by_targets(self, targets_to_show):
        """Filter tree to show only specific targets"""
        logger.debug(f"Filtering tree for {len(targets_to_show)} targets")
        view_state.filter_tree_by_targets(self.tree, self.model, targets_to_show)

    def retrace_tab(self, inout):
        """Execute trace and filter view (In-Place)"""
        action_controller.retrace_tab(self, inout)




    def set_column_widths(self):
        """Set column widths to user preferences"""
        header = self.tree.header()
        default_widths = self._get_main_view_default_column_widths()
        header_min_widths = self._get_header_min_widths()
        if header is not None:
            header.setStretchLastSection(False)
            for col in range(self.model.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Interactive)

        for column, width in default_widths.items():
            min_width = header_min_widths.get(column, 0)
            self.tree.setColumnWidth(column, max(width, min_width))

        self._apply_adaptive_target_column_width()
        self._fill_trailing_blank_with_last_column()
        self._apply_main_tree_column_visibility(self._main_tree_visible_columns, save_state=False)
        self._update_column_visibility_control_state()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
