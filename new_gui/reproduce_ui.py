import sys
import os
import re
import time
import warnings
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor

# Last Updated: 2026-03-05 19:00
warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from new_gui.config.settings import (
    ANIMATION_DURATION_MS,
    BACKUP_TIMER_INTERVAL_MS,
    DEBOUNCE_DELAY_MS,
    FADE_IN_DURATION_MS,
    MAX_NOTIFICATIONS,
    NOTIFICATION_MARGIN_BOTTOM,
    NOTIFICATION_MARGIN_RIGHT,
    NOTIFICATION_SPACING,
    NOTIFICATION_TYPES,
    RE_ACTIVE_TARGETS,
    RE_ALL_RELATED,
    RE_DEPENDENCY_OUT,
    RE_LEVEL_LINE,
    RE_QUOTED_STRING,
    RE_TARGET_LEVEL,
    SHORTCUTS,
    STATUS_COLORS,
    STATUS_CONFIG,
    THEMES,
    logger,
)
from new_gui.ui.dialogs.dependency_graph import DependencyGraphDialog
from new_gui.ui.dialogs.params_editor import ParamsEditorDialog
from new_gui.services import run_repository
from new_gui.services import file_actions
from new_gui.services import search_flow
from new_gui.services import status_summary
from new_gui.services import tree_rows
from new_gui.services import view_state
from new_gui.ui.widgets.bounded_combo import BoundedComboBox
from new_gui.ui.theme_runtime import ThemeManager
from new_gui.ui.builders import menu_builder, shortcut_builder, top_panel_builder, window_builder
from new_gui.ui.controllers import (
    action_controller,
    context_menu_controller,
    theme_controller,
    view_controller,
)
from new_gui.ui.widgets.delegates import BorderItemDelegate, TuneComboBoxDelegate
from new_gui.ui.widgets.filter_header import FilterHeaderView
from new_gui.ui.widgets.labels import ClickableLabel
from new_gui.ui.widgets.notifications import NotificationManager
from new_gui.ui.widgets.scrollbars import RoundedScrollBar
from new_gui.ui.widgets.status_bar import StatusBar
from new_gui.ui.widgets.tree_view import ColorTreeView, TreeViewEventFilter


from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, Qt, QTimer, QObject,
                          QEvent, QModelIndex, QRect, pyqtSignal,
                          QPointF, QLineF, QFileSystemWatcher, QSize, QPoint,
                          QAbstractTableModel, QSortFilterProxyModel)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton, QCompleter,
                             QTreeView, QLineEdit, QHeaderView,
                             QGraphicsDropShadowEffect,
                             QSizePolicy, QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem,
                             QAbstractItemView, QStyleOptionComboBox,
                             QMenuBar, QAction, QGraphicsScene, QGraphicsView,
                             QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
                             QGraphicsPolygonItem, QFileDialog, QCheckBox, QScrollArea,
                             QGroupBox, QFrame, QShortcut, QShortcut,
                             QGraphicsRectItem, QGraphicsItem, QTableWidget, QTableWidgetItem,
                             QTableView, QItemDelegate, QScrollBar,
                             QStyleOptionSlider)
from PyQt5.QtGui import (QStandardItemModel, QStandardItem, QColor, QBrush, QFont,
                         QPen, QPainter, QPolygonF,
                         QKeySequence, QIcon, QPixmap, QPainterPath)
import math


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
        self.tree.expandAll()

    def _init_core_variables(self):
        """Initialize core instance variables."""
        self.level_expanded = {}
        self.combo_sel = None
        self.cached_targets_by_level = {}
        self.is_tree_expanded = True
        self.is_search_mode = False
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.colors = {k: v["color"] for k, v in STATUS_CONFIG.items()}
        self._tune_files_cache = {}
        self._bsub_params_cache = {}
        self._main_view_snapshot = None

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
        return search_flow.build_search_context(
            self.is_search_mode,
            self._get_current_search_text(),
            targets,
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
            self.tree.expandAll()
        self.is_tree_expanded = not self.is_tree_expanded

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

        # Show dialog
        dialog = DependencyGraphDialog(graph_data, self.colors, self)
        dialog.exec_()

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

    def _append_target_groups_to_model(self, level_groups, run_name: str = None, status_value: str = None) -> int:
        """Append grouped targets to the model using the standard main-tree structure."""
        appended_count = 0
        for level, targets in level_groups:
            if not targets:
                continue

            parent_row = self._build_target_row_items(str(level), targets[0], status_value=status_value, run_name=run_name)
            self.model.appendRow(parent_row)
            appended_count += 1

            parent_level_item = parent_row[0]
            for child_target in targets[1:]:
                child_row = self._build_target_row_items("", child_target, status_value=status_value, run_name=run_name)
                parent_level_item.appendRow(child_row)
                appended_count += 1
        return appended_count

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
            if target_item.text() != target_name:
                return
            tune_item.setText(tune_display)
            tune_item.setData(tune_files, Qt.UserRole)

        for row_idx in range(self.model.rowCount()):
            update_cells(self.model.item(row_idx, 1), self.model.item(row_idx, 3))
            level_item = self.model.item(row_idx, 0)
            if not level_item or not level_item.hasChildren():
                continue
            for child_row in range(level_item.rowCount()):
                update_cells(level_item.child(child_row, 1), level_item.child(child_row, 3))

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
            if self.model.columnCount() > 1:
                header.setSectionResizeMode(1, QHeaderView.Stretch)

        for column, width in default_widths.items():
            min_width = header_min_widths.get(column, 0)
            self.tree.setColumnWidth(column, max(width, min_width))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
