"""State containers for MainWindow runtime and UI concerns."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from new_gui.infrastructure.repositories.run_cache import CacheKey
from new_gui.model.services import tree_rows
from new_gui.presentation.views.builders import top_panel_builder
from new_gui.shared.config.settings import STATUS_CONFIG


@dataclass
class RunCacheState:
    """Hold run-derived caches owned by the main window."""

    status_cache: Dict[str, object] = field(
        default_factory=lambda: {"run": "", "statuses": {}, "times": {}}
    )
    tune_files_cache: Dict[CacheKey, List[str]] = field(default_factory=dict)
    bsub_params_cache: Dict[CacheKey, object] = field(default_factory=dict)
    targets_by_level: Dict[int, List[str]] = field(default_factory=dict)
    cached_targets_run: str = ""
    collapsible_target_groups: Dict[str, object] = field(default_factory=dict)
    cached_collapsible_groups_run: str = ""


@dataclass
class ViewState:
    """Hold tree and view presentation state."""

    level_expanded: Dict[str, bool] = field(default_factory=dict)
    combo_sel: Optional[str] = None
    is_tree_expanded: bool = True
    is_search_mode: bool = False
    main_view_snapshot: Optional[dict] = None
    search_view_snapshot: Optional[dict] = None
    column_resize_guard: bool = False
    suspend_header_layout_updates: bool = False
    locked_main_tree_columns: Set[int] = field(default_factory=lambda: {0, 1})
    main_tree_visible_columns: Set[int] = field(
        default_factory=lambda: set(range(len(tree_rows.MAIN_TREE_HEADERS)))
    )
    column_visibility_picker: object = None
    visible_top_buttons: Set[str] = field(
        default_factory=lambda: set(top_panel_builder.DEFAULT_TOP_BUTTON_IDS)
    )
    button_visibility_picker: object = None
    bottom_output_last_height: int = 260
    search_filter_request_id: int = 0
    active_content_mode: str = "main"
    dependency_graph_panel: object = None
    dependency_graph_dirty: bool = True


@dataclass
class RuntimeState:
    """Hold async runtime and background refresh state."""

    executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(max_workers=4)
    )
    pending_tune_refresh: bool = False
    pending_dependency_refresh: bool = False
    missing_selected_run_name: str = ""
    terminal_follow_run: bool = False
    launch_xmeta_background: Optional[str] = field(
        default_factory=lambda: os.environ.get("XMETA_BACKGROUND", "").strip() or None
    )
    xmeta_background_color: Optional[str] = None
    ui_log_dispatcher: object = None
    action_refresh_dispatcher: object = None
    gui_log_handler: object = None
    gui_log_previous_logger_level: object = None
    gui_log_root_handler_levels: Dict[str, object] = field(default_factory=dict)
    runtime_observer_pause_depth: int = 0
    runtime_refresh_pending: bool = False
    runtime_resume_refresh_scheduled: bool = False
    runtime_backup_timer_was_active: bool = False
    runtime_status_snapshot_timer_was_active: bool = False


@dataclass
class SidebarState:
    """Hold sidebar category state."""

    category_scope: str = "stage"
    stage_categories: List[object] = field(default_factory=list)
    type_categories: List[object] = field(default_factory=list)
    selected_stage_category_id: str = ""
    selected_type_category_id: str = ""
    sidebar_filter_snapshot: object = None


class WindowStateStore:
    """Aggregate state containers and expose defaults for MainWindow."""

    def __init__(self) -> None:
        self.colors = {key: value["color"] for key, value in STATUS_CONFIG.items()}
        self.run_cache = RunCacheState()
        self.view = ViewState()
        self.runtime = RuntimeState()
        self.sidebar = SidebarState()
        self.selection_sync_in_progress = False
