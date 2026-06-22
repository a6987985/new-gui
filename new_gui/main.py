import os
import sys
import warnings

# Last Updated: 2026-03-05 19:00
warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from new_gui.shared.config.settings import (
    STATUS_COLORS,
    STATUS_CONFIG,
    logger,
)
from new_gui.presentation.views.dialogs.params_editor import ParamsEditorDialog
from new_gui.infrastructure.repositories import file_actions
from new_gui.infrastructure.repositories import run_repository
from new_gui.model.services import search_flow
from new_gui.model.services import status_summary
from new_gui.infrastructure.repositories import target_categories
from new_gui.model.services import tree_rows
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_state
from new_gui.model.services import dependency_graph_navigation
from new_gui.model.services import runtime_watchers
from new_gui.model.services import sidebar_view
from new_gui.model.services import tune_runtime
from new_gui.presentation.theme.theme_runtime import ThemeManager
from new_gui.presentation.views.builders import menu_builder, shortcut_builder, top_panel_builder, window_builder
from new_gui.presentation.presenters import (
    action_controller,
    context_menu_controller,
    output_controller,
    runtime_controller,
    search_ui_controller,
    theme_controller,
    tree_display_controller,
    content_tab_controller,
    visibility_controller,
    view_controller,
)
from new_gui.presentation.presenters import external_scrollbar_controller
from new_gui.presentation.state.window_state import WindowStateStore
from new_gui.infrastructure.repositories.run_cache_manager import RunCacheManager
from PyQt5.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QDockWidget, QHeaderView, QMainWindow, QMenu

from new_gui.application.agent import (
    AgentAuditLog,
    LLMPlanner,
    LLMPlannerSettings,
    RulePlanner,
    default_audit_log_path,
)
from new_gui.presentation.presenters.agent_controller import AgentController
from new_gui.presentation.views.widgets.agent_panel import AgentPanel


# ========== Status Bar ==========
class MainWindow(QMainWindow):
    def __init__(self):
        # Initialize core variables FIRST
        self._init_core_variables()

        # Initialize theme manager
        self.theme_manager = ThemeManager()

        # Detect run base directory
        self._detect_run_base_dir()
        self._ensure_shared_target_stage_file()

        # Call parent constructor
        super().__init__()
        self._init_ui_log_dispatcher()
        self._init_action_refresh_dispatcher()

        # Initialize window
        self._init_window()

        # Initialize UI components
        self._init_menu_bar()
        self._init_central_widget()
        self._init_top_panel()
        self._install_gui_log_handler()
        self._install_agent_dock()

        # Expand tree initially
        self.expand_tree_default()

    def _install_agent_dock(self):
        """Mount the Executable Agent panel in a right-side dock."""
        settings = LLMPlannerSettings.from_env()
        rule_planner = RulePlanner()
        planner = (
            LLMPlanner(settings=settings, fallback=rule_planner)
            if settings.is_enabled
            else rule_planner
        )
        audit_path = default_audit_log_path()
        try:
            audit_log = AgentAuditLog(path=audit_path)
        except Exception:
            audit_log = None
            audit_path = None
        self.agent_controller = AgentController(
            self,
            planner=planner,
            audit_log=audit_log,
        )
        self._agent_panel = AgentPanel(
            self.agent_controller,
            parent=self,
            audit_path=audit_path,
        )
        self._agent_dock = QDockWidget("✨  Agent", self)
        self._agent_dock.setObjectName("agent_dock")
        self._agent_dock.setWidget(self._agent_panel)
        self._agent_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._agent_dock.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        self._agent_dock.setMinimumWidth(360)
        self.addDockWidget(Qt.RightDockWidgetArea, self._agent_dock)
        self._agent_dock.hide()
        self._agent_dock.visibilityChanged.connect(self._on_agent_dock_visibility_changed)
        try:
            self._agent_panel.apply_theme(self.theme_manager.get_theme())
        except Exception:
            pass

    def _on_agent_dock_visibility_changed(self, visible):
        """Mirror the dock visibility on the menu toggle when present."""
        action = getattr(self, "toggle_agent_action", None)
        if action is not None and action.isChecked() != bool(visible):
            action.blockSignals(True)
            action.setChecked(bool(visible))
            action.blockSignals(False)
        if visible and hasattr(self, "_agent_panel"):
            try:
                self._agent_panel.on_dock_shown()
            except Exception:
                pass

    def toggle_agent_dock(self):
        """Show or hide the Executable Agent dock."""
        if not hasattr(self, "_agent_dock"):
            return
        if self._agent_dock.isVisible():
            self._agent_dock.hide()
        else:
            self._agent_dock.show()
            self._agent_dock.raise_()
            if hasattr(self, "_agent_panel"):
                self._agent_panel.on_dock_shown()
                self._agent_panel.focus_prompt()

    def focus_agent_prompt(self):
        """Reveal the Agent dock if hidden and focus the prompt input."""
        if not hasattr(self, "_agent_dock"):
            return
        if not self._agent_dock.isVisible():
            self._agent_dock.show()
            self._agent_dock.raise_()
        if hasattr(self, "_agent_panel"):
            try:
                self._agent_panel.on_dock_shown()
                self._agent_panel.focus_prompt()
            except Exception:
                pass

    def clear_agent_transcript(self):
        """Clear the Agent transcript pane from a menu action."""
        panel = getattr(self, "_agent_panel", None)
        if panel is not None and hasattr(panel, "clear_transcript"):
            try:
                panel.clear_transcript()
            except Exception:
                pass

    def _init_core_variables(self):
        """Initialize core instance variables."""
        self._state = WindowStateStore()
        self._cache_manager = RunCacheManager(self._state.run_cache)
        self.level_expanded = self._state.view.level_expanded
        self.combo_sel = self._state.view.combo_sel
        self.cached_targets_by_level = self._state.run_cache.targets_by_level
        self._cached_targets_run = self._state.run_cache.cached_targets_run
        self.cached_collapsible_target_groups = self._state.run_cache.collapsible_target_groups
        self._cached_collapsible_target_groups_run = self._state.run_cache.cached_collapsible_groups_run
        self.is_tree_expanded = self._state.view.is_tree_expanded
        self.is_search_mode = self._state.view.is_search_mode
        self._executor = self._state.runtime.executor
        self.colors = self._state.colors
        self._tune_files_cache = self._state.run_cache.tune_files_cache
        self._bsub_params_cache = self._state.run_cache.bsub_params_cache
        self._status_cache = self._state.run_cache.status_cache
        self._main_view_snapshot = self._state.view.main_view_snapshot
        self._search_view_snapshot = self._state.view.search_view_snapshot
        self._column_resize_guard = self._state.view.column_resize_guard
        self._suspend_header_layout_updates = self._state.view.suspend_header_layout_updates
        self._locked_main_tree_columns = self._state.view.locked_main_tree_columns
        self._main_tree_visible_columns = self._state.view.main_tree_visible_columns
        self._column_visibility_picker = self._state.view.column_visibility_picker
        self._visible_top_buttons = self._state.view.visible_top_buttons
        self._button_visibility_picker = self._state.view.button_visibility_picker
        self._bottom_output_last_height = self._state.view.bottom_output_last_height
        self._terminal_output_content_filled = False
        self._terminal_output_restore_height = self._bottom_output_last_height
        self._pending_tune_refresh = self._state.runtime.pending_tune_refresh
        self._pending_dependency_refresh = self._state.runtime.pending_dependency_refresh
        self._missing_selected_run_name = self._state.runtime.missing_selected_run_name
        self._terminal_follow_run = self._state.runtime.terminal_follow_run
        self._launch_xmeta_background = self._state.runtime.launch_xmeta_background
        self._xmeta_background_color = self._state.runtime.launch_xmeta_background
        self._ui_log_dispatcher = self._state.runtime.ui_log_dispatcher
        self._action_refresh_dispatcher = self._state.runtime.action_refresh_dispatcher
        self._gui_log_handler = self._state.runtime.gui_log_handler
        self._gui_log_previous_logger_level = self._state.runtime.gui_log_previous_logger_level
        self._gui_log_root_handler_levels = self._state.runtime.gui_log_root_handler_levels
        self._runtime_observer_pause_depth = self._state.runtime.runtime_observer_pause_depth
        self._runtime_refresh_pending = self._state.runtime.runtime_refresh_pending
        self._runtime_resume_refresh_scheduled = self._state.runtime.runtime_resume_refresh_scheduled
        self._runtime_backup_timer_was_active = self._state.runtime.runtime_backup_timer_was_active
        self._runtime_status_snapshot_timer_was_active = (
            self._state.runtime.runtime_status_snapshot_timer_was_active
        )
        self._search_filter_request_id = self._state.view.search_filter_request_id
        self._category_scope = self._state.sidebar.category_scope
        self._stage_categories = self._state.sidebar.stage_categories
        self._type_categories = self._state.sidebar.type_categories
        self._selected_stage_category_id = self._state.sidebar.selected_stage_category_id
        self._selected_type_category_id = self._state.sidebar.selected_type_category_id
        self._sidebar_filter_snapshot = self._state.sidebar.sidebar_filter_snapshot
        self._active_content_mode = self._state.view.active_content_mode
        self._dependency_graph_panel = self._state.view.dependency_graph_panel
        self._dependency_graph_dirty = self._state.view.dependency_graph_dirty
        self._dependency_graph_initialized = False
        self._dependency_graph_return_context = {}
        self._main_view_tab_state = None
        self._sidebar_category_tab_active = False
        self._sidebar_category_return_state = None
        self._trace_return_scroll_value = None
        self._selection_sync_in_progress = self._state.selection_sync_in_progress
        view_mode_state.ensure_window_view_state(self)

    def _init_ui_log_dispatcher(self) -> None:
        """Create the thread-safe log bridge used by the GUI session log."""
        output_controller.init_ui_log_dispatcher(self)

    def _init_action_refresh_dispatcher(self) -> None:
        """Create the thread-safe bridge used by async action refresh callbacks."""
        output_controller.init_action_refresh_dispatcher(self)

    def _install_gui_log_handler(self) -> None:
        """Attach a GUI-only log handler while keeping console logging unchanged."""
        output_controller.install_gui_log_handler(self)

    def _remove_gui_log_handler(self) -> None:
        """Detach the GUI log handler and restore previous logger settings."""
        output_controller.remove_gui_log_handler(self)

    def _queue_ui_log_entry(self, entry) -> None:
        """Queue one log entry back onto the GUI thread."""
        output_controller.queue_ui_log_entry(self, entry)

    @staticmethod
    def _normalize_ui_log_level(level: str) -> str:
        """Normalize GUI log levels to the supported INFO/WARNING/ERROR set."""
        return output_controller.normalize_ui_log_level(level)

    def append_ui_log(
        self,
        level: str,
        source: str,
        message: str,
        command: str = "",
        details: str = "",
    ) -> None:
        """Append one session log entry through the thread-safe GUI sink."""
        output_controller.append_ui_log(
            self,
            level,
            source,
            message,
            command=command,
            details=details,
        )

    def _append_ui_log_entry(self, entry) -> None:
        """Render one queued log entry and apply panel attention rules."""
        output_controller.append_ui_log_entry(self, entry)

    def request_action_refresh(self, search_context: dict, command: str = "") -> None:
        """Queue one async action-complete refresh request onto the GUI thread."""
        payload = {
            "search_context": dict(search_context or {}),
            "command": str(command or ""),
        }
        output_controller.queue_action_refresh_request(self, payload)

    def _handle_action_refresh_request(self, payload) -> None:
        """Handle one action-complete refresh request on the GUI thread."""
        payload_dict = dict(payload or {})
        search_context = dict(payload_dict.get("search_context") or {})
        command = str(payload_dict.get("command") or "")
        logger.info(
            f"Action refresh requested from async command: {command or 'unknown'}",
            extra={"ui_source": "runtime"},
        )
        action_controller.refresh_after_action(self, search_context)

    def _invalidate_tune_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate tune-file cache entries."""
        self._cache_manager.invalidate_tune_cache(run_dir, target_name)

    def _invalidate_bsub_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate bsub-parameter cache entries."""
        self._cache_manager.invalidate_bsub_cache(run_dir, target_name)

    def _invalidate_main_view_snapshot(self) -> None:
        """Drop the in-memory main-view snapshot."""
        self._main_view_snapshot = None

    def _invalidate_search_view_snapshot(self) -> None:
        """Drop the in-memory search visibility snapshot."""
        self._search_view_snapshot = None

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

    def _capture_search_view_snapshot(self) -> None:
        """Capture the current row visibility state before entering search mode."""
        current_run = self.combo.currentText()
        if not current_run or current_run == "No runs found":
            return
        self._search_view_snapshot = view_state.capture_tree_presentation_snapshot(
            self.model,
            self.tree,
            current_run,
        )

    def _restore_search_view_snapshot(self) -> bool:
        """Restore the saved pre-search row visibility state."""
        return view_state.restore_tree_presentation_snapshot(
            self.model,
            self.tree,
            self._search_view_snapshot,
            self.combo.currentText(),
        )

    def _get_xmeta_background_color(self):
        """Return the configured XMETA background color, if any."""
        return theme_controller.get_xmeta_background_color(self)

    def refresh_xmeta_background(self, run_dir: str = None, announce: bool = False):
        """Reload the run-backed XMETA background and refresh the current theme."""
        return theme_controller.refresh_xmeta_background(self, run_dir=run_dir, announce=announce)

    def _detect_run_base_dir(self):
        """Detect the run base directory based on environment."""
        if os.path.exists("mock_runs"):
            self.run_base_dir = "mock_runs"
        elif os.path.exists(".target_dependency.csh"):
            self.run_base_dir = ".."
            logger.info(f"Detected run in current directory. Setting base to parent: {os.path.abspath(self.run_base_dir)}")
        else:
            self.run_base_dir = "."

    def _ensure_shared_target_stage_file(self) -> None:
        """Prepare the shared target-stage file under ../../XMeta/util/GUI."""
        target_file, created_gui_dir, copied_target_file, error_message = (
            target_categories.ensure_shared_target_stage_file(
                create_gui_dir=True,
                copy_target_file=True,
            )
        )
        if error_message:
            logger.warning(f"Failed to prepare shared target-stage file: {error_message} ({target_file})")
            return
        if created_gui_dir:
            logger.info(f"Created shared GUI directory for target stages: {os.path.dirname(target_file)}")
        if copied_target_file:
            logger.info(f"Copied shared target-stage file to: {target_file}")
        elif os.path.isfile(target_file):
            logger.info(f"Using shared target-stage file: {target_file}")
        else:
            logger.debug(f"Shared target-stage file not found: {target_file}")

    def _init_window(self):
        """Initialize window properties and animation."""
        window_builder.init_window(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_top_action_buttons()
        self._apply_adaptive_target_column_width()
        external_scrollbar_controller.sync_external_scrollbar(self)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_adaptive_target_column_width)
        QTimer.singleShot(0, lambda: external_scrollbar_controller.sync_external_scrollbar(self))
        QTimer.singleShot(0, self._update_backup_timer_state)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._update_backup_timer_state()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            QTimer.singleShot(0, self._update_backup_timer_state)

    def closeEvent(self, event):
        """Release background resources when the window closes."""
        self._remove_gui_log_handler()
        if hasattr(self, "_embedded_terminal"):
            self._embedded_terminal.shutdown()
        runtime_controller.shutdown_runtime_observers(self)
        super().closeEvent(event)
        QCoreApplication.quit()

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

    def set_left_sidebar_visible(self, visible: bool) -> None:
        """Show or hide the codex-style workspace sidebar."""
        top_panel_builder.set_left_sidebar_visible(self, visible)

    def set_left_sidebar_content_mode_visible(self, visible: bool) -> None:
        """Show or hide the sidebar for content-page switches."""
        top_panel_builder.set_left_sidebar_content_mode_visible(self, visible)

    def toggle_left_sidebar(self) -> bool:
        """Toggle workspace sidebar visibility from top-left icon button."""
        return top_panel_builder.toggle_left_sidebar(self)

    def clear_left_sidebar_selection(self) -> None:
        """Clear the active left-sidebar category selection state."""
        sidebar_view.clear_left_sidebar_selection(self)

    def show_full_target_view(self, force_rebuild: bool = False) -> bool:
        """Restore the unfiltered Main View target tree for the active run."""
        return sidebar_view.show_full_target_view(self, force_rebuild=force_rebuild)

    def _can_apply_sidebar_filter_in_place(self) -> bool:
        """Return whether sidebar category filtering can run without rebuilding the model."""
        return sidebar_view.can_apply_sidebar_filter_in_place(self)

    def _restore_sidebar_filter_snapshot(self, current_run: str = None, clear_snapshot: bool = True) -> bool:
        """Restore the pre-sidebar-filter tree presentation snapshot if available."""
        return sidebar_view.restore_sidebar_filter_snapshot(
            self,
            current_run=current_run,
            clear_snapshot=clear_snapshot,
        )

    def _apply_sidebar_category_filter_in_place(self) -> bool:
        """Apply the active sidebar category filter by hiding or restoring existing rows."""
        return sidebar_view.apply_sidebar_category_filter_in_place(self)

    def refresh_left_sidebar_categories(self, run_dir: str = None) -> None:
        """Reload stage/type category rows from the shared target-stage file."""
        sidebar_view.refresh_left_sidebar_categories(self, run_dir=run_dir)

    def on_left_sidebar_scope_changed(self, scope: str) -> None:
        """Handle STAGE/TYPE tab switch and refresh visible tree rows."""
        sidebar_view.on_left_sidebar_scope_changed(self, scope)

    def on_left_sidebar_category_changed(self, scope: str, category_id: str) -> None:
        """Handle single-select category changes from the left sidebar."""
        sidebar_view.on_left_sidebar_category_changed(self, scope, category_id)

    def get_active_category_target_set(self):
        """Return selected category targets for current scope, or None when unscoped."""
        return sidebar_view.get_active_category_target_set(self)

    def _set_bottom_output_panel_visible(self, visible: bool) -> None:
        """Show or collapse the bottom output panel inside the content splitter."""
        output_controller.set_bottom_output_panel_visible(self, visible)

    def _set_embedded_terminal_panel_visible(self, visible: bool) -> None:
        """Backward-compatible wrapper for the old terminal-only panel API."""
        output_controller.set_embedded_terminal_panel_visible(self, visible)

    def show_embedded_terminal_panel(self, run_dir: str) -> bool:
        """Open the embedded terminal panel for the requested run directory."""
        return output_controller.show_embedded_terminal_panel(self, run_dir)

    def hide_embedded_terminal_panel(self) -> None:
        """Close the embedded terminal session and collapse the bottom panel."""
        output_controller.hide_embedded_terminal_panel(self)

    def hide_bottom_output_panel(self) -> None:
        """Collapse the bottom output panel without stopping the terminal session."""
        output_controller.hide_bottom_output_panel(self)

    def toggle_terminal_output_panel(self) -> bool:
        """Toggle the embedded terminal panel from the top icon button."""
        return output_controller.toggle_terminal_output_panel(self)

    def show_log_output_panel(self) -> None:
        """Open the bottom output area and switch to the session log tab."""
        output_controller.show_log_output_panel(self)

    def set_terminal_output_content_filled(self, filled: bool) -> None:
        """Expand or restore the embedded terminal inside the content area."""
        output_controller.set_terminal_output_content_filled(self, filled)

    def get_embedded_terminal_status_message(self) -> str:
        """Return the current embedded-terminal status text, if any."""
        return output_controller.get_embedded_terminal_status_message(self)

    def is_terminal_follow_run_enabled(self) -> bool:
        """Return whether terminal rundir should follow run selection changes."""
        return output_controller.is_terminal_follow_run_enabled(self)

    def set_terminal_follow_run_enabled(self, enabled: bool) -> None:
        """Update whether terminal rundir should follow run selection changes."""
        output_controller.set_terminal_follow_run_enabled(self, enabled)

    def sync_embedded_terminal_run_dir(self, run_dir: str) -> bool:
        """Sync the embedded terminal session to a new run directory when enabled."""
        return output_controller.sync_embedded_terminal_run_dir(self, run_dir)

    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts"""
        shortcut_builder.setup_keyboard_shortcuts(self)

    def _focus_search(self):
        """Focus the search input - shows the embedded filter in header"""
        search_ui_controller.focus_search(self)

    def _set_quick_search_text(self, text):
        """Update the persistent search field without triggering another filter pass."""
        search_ui_controller.set_quick_search_text(self, text)

    def _set_header_filter_text_silent(self, text):
        """Update the header search state without emitting filter_changed again."""
        search_ui_controller.set_header_filter_text_silent(self, text)

    def _on_top_search_changed(self, text):
        """Keep the header search state in sync with the visible search field."""
        search_ui_controller.on_top_search_changed(self, text)

    def _on_header_filter_changed(self, text):
        """Mirror header search edits back to the visible search field."""
        search_ui_controller.on_header_filter_changed(self, text)

    def _refresh_view(self):
        """Refresh the current view"""
        current_run = self.combo.currentText()
        if current_run and current_run != "No runs found":
            self._build_status_cache(current_run)
            self.populate_data()
            if getattr(self, "_active_content_mode", "main") == "graph":
                self._mark_dependency_graph_dirty()
                self.show_dependency_graph(preserve_viewport=True)
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

    def open_xmeta_background_dialog(self) -> None:
        """Open the XMETA background editor for every run in the current directory."""
        theme_controller.open_xmeta_background_dialog(self)

    def show_notification(self, title, message, notification_type="info"):
        """Show a notification message"""
        if hasattr(self, '_notification_manager'):
            self._notification_manager.show_notification(title, message, notification_type)
        level = {
            "error": "ERROR",
            "warning": "WARNING",
            "success": "INFO",
            "info": "INFO",
        }.get(notification_type, "INFO")
        summary = f"{title}: {message}" if title else message
        self.append_ui_log(level, "notification", summary)

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
        if getattr(self, "_active_content_mode", "main") == "graph":
            panel = getattr(self, "_dependency_graph_panel", None)
            if panel is not None and getattr(panel, "selected_node", None):
                if hasattr(panel, "selected_display_target"):
                    selected_target = str(panel.selected_display_target() or "").strip()
                    return [selected_target] if selected_target else []
        return view_state.get_selected_targets(self.tree, self.model)

    def get_selected_action_targets(self):
        """Get actionable targets from tree selection for batch execute actions."""
        if getattr(self, "_active_content_mode", "main") == "graph":
            panel = getattr(self, "_dependency_graph_panel", None)
            if panel is not None and getattr(panel, "selected_node", None):
                if hasattr(panel, "selected_action_targets"):
                    return list(panel.selected_action_targets() or [])
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
        self._invalidate_search_view_snapshot()
        self.model.clear()
        self.populate_data()

    def _refresh_tree_rows_stable(self) -> bool:
        """Refresh row status/tune cells in place without rebuilding tree structure."""
        if self.is_all_status_view or not self.combo_sel:
            return False
        if self.model is None or self.model.rowCount() <= 0:
            return False
        self.populate_data(force_rebuild=False)
        if getattr(self, "_active_content_mode", "main") == "graph":
            self._mark_dependency_graph_dirty()
            self.show_dependency_graph(preserve_viewport=True)
        return True

    def _clear_search_ui_state(self) -> None:
        """Clear the visible and embedded search UI state without rebuilding."""
        if hasattr(self, 'header'):
            self._set_header_filter_text_silent("")
            self.header.hide_filter()
        self._set_quick_search_text("")
        view_mode_state.clear_search_state(self)
        self._invalidate_search_view_snapshot()

    def start(self, action):
        """Execute flow action and refresh view (runs command in background thread)."""
        action_controller.start(self, action)

    def filter_tree(self, text, search_options=None):
        """Filter tree items based on text input and active search options."""
        view_controller.filter_tree(self, text, search_options=search_options)

    def toggle_tree_expansion(self):
        """Toggle between full Expand All and Collapse All."""
        if self.is_tree_expanded:
            self.collapse_tree_all()
        else:
            self.expand_tree_all()

    def expand_tree_all(self):
        """Expand the entire tree, including synthetic generic target groups."""
        view_state.expand_all_rows(self.tree)
        self.is_tree_expanded = True

    def collapse_tree_all(self):
        """Collapse the entire tree."""
        view_state.collapse_all_rows(self.tree)
        self.is_tree_expanded = False

    def expand_tree_default(self):
        """Expand the tree while keeping synthetic generic groups collapsed."""
        view_state.expand_all_except_groups(self.tree, self.model)
        self.is_tree_expanded = True

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
        if getattr(self, "_active_content_mode", "main") == "graph":
            self.show_main_view_tab()
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
        if getattr(self, "_suspend_header_layout_updates", False):
            return
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
        return visibility_controller.is_main_tree_schema_active(self)

    def _get_visible_main_tree_columns(self):
        """Return currently visible main-tree columns."""
        return visibility_controller.get_visible_main_tree_columns(self)

    def _apply_main_tree_column_visibility(self, visible_columns, save_state=True):
        """Apply persisted main-tree column visibility to the tree widget."""
        visibility_controller.apply_main_tree_column_visibility(
            self,
            visible_columns,
            save_state=save_state,
        )

    def _update_column_visibility_control_state(self):
        """Enable the column-visibility control only for main-tree mode."""
        visibility_controller.update_column_visibility_control_state(self)

    def _on_apply_column_visibility(self, visible_columns):
        """Apply user-picked visibility from the picker popup."""
        visibility_controller.on_apply_column_visibility(self, visible_columns)

    def _get_or_create_column_visibility_picker(self):
        """Return the shared column-visibility editor widget."""
        return visibility_controller.get_or_create_column_visibility_picker(self)

    def _prepare_column_visibility_menu(self):
        """Refresh the column-visibility editor before opening the menu."""
        visibility_controller.prepare_column_visibility_menu(self)

    def _apply_top_button_visibility(self, visible_button_ids, save_state=True):
        """Apply persisted top-button visibility to the floating button area."""
        visibility_controller.apply_top_button_visibility(
            self,
            visible_button_ids,
            save_state=save_state,
        )

    def _on_apply_button_visibility(self, visible_button_ids):
        """Apply user-picked top-button visibility from the picker popup."""
        visibility_controller.on_apply_button_visibility(self, visible_button_ids)

    def _get_or_create_button_visibility_picker(self):
        """Return the shared top-button visibility editor widget."""
        return visibility_controller.get_or_create_button_visibility_picker(self)

    def _prepare_button_visibility_menu(self):
        """Refresh the top-button visibility editor before opening the menu."""
        visibility_controller.prepare_button_visibility_menu(self)

    def _close_button_visibility_menu(self):
        """Close the button-visibility menu hierarchy."""
        visibility_controller.close_button_visibility_menu(self)

    def _close_column_visibility_menu(self):
        """Close the column-visibility menu hierarchy."""
        visibility_controller.close_column_visibility_menu(self)

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

    def show_dependency_graph(self, preserve_viewport: bool = False):
        """Open the dependency graph as the persistent content tab."""
        content_tab_controller.activate_dependency_graph_tab(
            self,
            preserve_viewport=preserve_viewport,
        )

    def show_main_view_tab(self):
        """Switch back to the main target-tree content tab."""
        content_tab_controller.activate_main_view_tab(self)

    def _on_content_mode_tab_changed(self, index: int) -> None:
        """Handle content tab switches between main view and dependency graph."""
        content_tab_controller.on_content_tab_changed(self, index)

    def _on_top_tab_label_clicked(self) -> None:
        """Route top-tab click behavior to the currently active content mode."""
        content_tab_controller.on_top_tab_label_clicked(self)

    def _on_top_tab_label_double_clicked(self) -> None:
        """Route top-tab double-click behavior to the currently active content mode."""
        content_tab_controller.on_top_tab_label_double_clicked(self)

    def _resolve_dependency_graph_initial_target(self):
        """Return the selected target used for initial graph focus when available."""
        selected_targets = [] if getattr(self, "is_all_status_view", False) else self.get_selected_targets()
        return selected_targets[0] if selected_targets else None

    def _mark_dependency_graph_dirty(self) -> None:
        """Mark the embedded dependency graph as stale until next graph-tab activation."""
        self._dependency_graph_dirty = True

    def _build_dependency_graph_return_context(self, run_name: str) -> dict:
        """Capture the current tree context so graph navigation can return cleanly."""
        return dependency_graph_navigation.build_dependency_graph_return_context(self, run_name)

    def _target_matches_graph_return_context(self, target_name: str, run_name: str, return_context: dict) -> bool:
        """Return whether the target belongs to the captured tree context."""
        return dependency_graph_navigation.target_matches_graph_return_context(
            self,
            target_name,
            run_name,
            return_context,
        )

    def _apply_dependency_graph_return_context(self, return_context: dict) -> None:
        """Restore the captured tree presentation before selecting a graph target."""
        dependency_graph_navigation.apply_dependency_graph_return_context(self, return_context)

    def locate_target_in_tree(self, target_name: str, return_context: dict = None) -> None:
        """Restore the tree view and select the requested target from the graph."""
        dependency_graph_navigation.locate_target_in_tree(
            self,
            target_name,
            return_context=return_context,
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
        view_controller.refresh_run_list(self, prefer_cwd=True)

    def refresh_available_runs(self):
        """Re-scan available runs and update the combo-box entries."""
        return view_controller.refresh_run_list(self, activate_if_selection_changed=True)

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
        return tree_display_controller.ensure_cached_collapsible_target_groups(self, run_name)

    def _build_display_level_groups(self, targets_by_level, run_name: str = None):
        """Build level/group/target display structure for the main tree."""
        return tree_display_controller.build_display_level_groups(
            self,
            targets_by_level,
            run_name=run_name,
        )

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
        self._cache_manager.status_cache = self._status_cache

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
        return tree_display_controller.build_target_row_items(
            self,
            level_text,
            target_name,
            status_value=status_value,
            run_name=run_name,
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
        return tree_display_controller.build_container_row_items(
            level_text,
            label_text,
            row_kind,
            descendant_targets,
            status_value=status_value,
            status_key=status_key,
        )

    def _summarize_group_row_status(self, target_names, run_name: str = None, status_value: str = None):
        """Return display text and dominant status key for one synthetic group row."""
        return tree_display_controller.summarize_group_row_status(
            self,
            target_names,
            run_name=run_name,
            status_value=status_value,
        )

    def _append_display_node_to_parent(self, parent_item, node: dict, run_name: str = None, status_value: str = None) -> int:
        """Append one display node and all descendants below an existing parent item."""
        return tree_display_controller.append_display_node_to_parent(
            self,
            parent_item,
            node,
            run_name=run_name,
            status_value=status_value,
        )

    def _split_level_anchor_target(self, child_nodes):
        """Return the top-level anchor target and remaining child nodes for one level."""
        return tree_display_controller.split_level_anchor_target(child_nodes)

    def _get_level_root_group_node(self, targets, child_nodes):
        """Return the top-level group node when one level is fully generic-grouped."""
        return tree_display_controller.get_level_root_group_node(targets, child_nodes)

    def _append_target_groups_to_model(self, display_groups, run_name: str = None, status_value: str = None) -> int:
        """Append grouped display nodes to the model using the standard main-tree structure."""
        return tree_display_controller.append_target_groups_to_model(
            self,
            display_groups,
            run_name=run_name,
            status_value=status_value,
        )

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

    def _activate_selected_run_view(
        self,
        current_run: str,
        invalidate_snapshot: bool = True,
        presentation_snapshot: dict = None,
    ) -> None:
        """Switch from overview/other run states back to the selected single-run view."""
        view_controller.activate_selected_run_view(
            self,
            current_run,
            invalidate_snapshot=invalidate_snapshot,
            presentation_snapshot=presentation_snapshot,
        )

    def populate_data(self, force_rebuild=False):
        """Populate or refresh the current run tree."""
        view_controller.populate_data(self, force_rebuild=force_rebuild)

    def setup_status_watcher(self):
        """Setup file system watcher for the current run's status directory."""
        runtime_watchers.setup_status_watcher(self)

    def setup_tune_watcher(self):
        """Setup file system watcher for the current run's tune directories."""
        runtime_watchers.setup_tune_watcher(self)

    def setup_dependency_watcher(self):
        """Setup file system watcher for the current run's dependency file."""
        runtime_watchers.setup_dependency_watcher(self)
    
    def on_status_directory_changed(self, path):
        """Called when the status directory contents change (file added/removed)."""
        runtime_watchers.on_status_directory_changed(self, path)

    def on_status_file_changed(self, path):
        """Called when a watched file is modified."""
        runtime_watchers.on_status_file_changed(self, path)

    def poll_status_directory_snapshot(self):
        """Detect status file changes missed by the platform watcher."""
        runtime_watchers.poll_status_directory_snapshot(self)

    def on_tune_directory_changed(self, path):
        """Called when the tune directory tree changes for the current run."""
        runtime_watchers.on_tune_directory_changed(self, path)

    def on_tune_file_changed(self, path):
        """Called when a watched tune file is modified."""
        runtime_watchers.on_tune_file_changed(self, path)

    def on_dependency_file_changed(self, path):
        """Called when the watched target dependency file is modified."""
        runtime_watchers.on_dependency_file_changed(self, path)

    def on_dependency_directory_changed(self, path):
        """Called when the selected run directory may contain dependency changes."""
        runtime_watchers.on_dependency_directory_changed(self, path)

    def change_run(self):
        """Refresh status timer callback - updates status/time for all visible targets"""
        view_controller.change_run(self)

    def _update_backup_timer_state(self):
        """Sync backup polling state with the current window/view/run conditions."""
        runtime_controller.update_backup_timer_state(self)

    def _update_status_snapshot_timer_state(self):
        """Sync missed-status-event polling with the current run."""
        runtime_controller.update_status_snapshot_timer_state(self)

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
        return tune_runtime.get_tune_files(self, run_dir, target_name)

    def get_tune_display(self, run_dir, target_name):
        """Get tune display string for tree view.
        Returns comma-separated suffixes or empty string
        """
        return tune_runtime.get_tune_display(self, run_dir, target_name)

    def get_tune_candidates_from_cmd(self, run_dir: str, target_name: str) -> list:
        """Parse tunesource entries from cmds/<target>.cmd.

        Args:
            run_dir: Path to run directory.
            target_name: Name of selected target.

        Returns:
            List of (display_name, full_path) tuples for tune files that can be created.
        """
        return tune_runtime.get_tune_candidates_from_cmd(run_dir, target_name)

    def _refresh_tune_cells_for_target(self, target_name: str) -> None:
        """Refresh tune column text and UserRole data for one target in tree model."""
        tune_runtime.refresh_tune_cells_for_target(self, target_name)

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
        return tune_runtime.get_bsub_params(self, run_dir, target_name)

    def save_bsub_param(self, run_dir, target_name, param_type, new_value):
        """Save a single bsub parameter to the csh file.
        Args:
            run_dir: Run directory path
            target_name: Target name
            param_type: 'queue', 'cores', or 'memory'
            new_value: New value to set
        Returns: True if successful, False otherwise
        """
        return tune_runtime.save_bsub_param(self, run_dir, target_name, param_type, new_value)

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
        """Open the embedded terminal panel for the current run, or fall back externally."""
        action_controller.open_terminal(self)

    def open_external_terminal(self):
        """Open the external terminal in the current run directory."""
        action_controller.open_external_terminal(self)

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
        view_controller.filter_tree_by_targets_flat(self, targets_to_show)

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
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
