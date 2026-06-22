"""Sidebar category filtering helpers for the main window."""

from new_gui.shared.config.settings import logger
from new_gui.infrastructure.repositories import target_categories
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_tabs
from new_gui.model.services import view_state


def get_active_category_restore_state(window):
    """Return the active sidebar category state needed to restore filtered views."""
    if not hasattr(window, "left_sidebar"):
        return None
    scope = window.left_sidebar.active_scope()
    category_id = window.left_sidebar.selected_category_id(scope)
    if not category_id:
        return None
    return {
        "scope": scope,
        "category_id": category_id,
        "category_label": _resolve_selected_category_label(window, scope, category_id),
        "targets": window.left_sidebar.selected_category_targets(scope),
    }


def restore_category_view(window, scope: str, category_id: str) -> bool:
    """Restore one sidebar category selection and the corresponding filtered view."""
    if not hasattr(window, "left_sidebar"):
        return False

    normalized_scope = (scope or "stage").strip().lower()
    normalized_id = (category_id or "").strip()
    if not normalized_id:
        return False

    left_sidebar = window.left_sidebar
    if normalized_scope not in {"stage", "type"}:
        normalized_scope = "stage"

    if hasattr(left_sidebar, "set_active_scope"):
        left_sidebar.set_active_scope(normalized_scope)
    if hasattr(left_sidebar, "select_category"):
        left_sidebar.select_category(normalized_scope, normalized_id)

    if normalized_scope == "type":
        window._selected_type_category_id = normalized_id
    else:
        window._selected_stage_category_id = normalized_id
    window._category_scope = normalized_scope

    if not window.combo_sel or window.is_all_status_view:
        _apply_sidebar_category_tab_state(window, normalized_scope, normalized_id)
        return True

    if not window._apply_sidebar_category_filter_in_place():
        window.populate_data(force_rebuild=True)
    _apply_sidebar_category_tab_state(window, normalized_scope, normalized_id)
    return True


def _refresh_dependency_graph_for_sidebar_change(window) -> None:
    """Refresh graph mode after sidebar scope/category changes."""
    if hasattr(window, "_mark_dependency_graph_dirty"):
        window._mark_dependency_graph_dirty()
    if view_mode_state.get_visible_content_mode(window) != "graph":
        return
    if not window.combo_sel or window.is_all_status_view:
        return
    if hasattr(window, "show_dependency_graph"):
        window.show_dependency_graph()


def _resolve_selected_category_label(window, scope: str, category_id: str) -> str:
    """Return the display label for one sidebar category selection."""
    normalized_scope = (scope or "stage").strip().lower()
    normalized_id = (category_id or "").strip()
    if not normalized_id:
        return ""

    source = window._type_categories if normalized_scope == "type" else window._stage_categories
    for category in source:
        if str(category.get("id") or "").strip() == normalized_id:
            label = str(category.get("label") or "").strip()
            return label or normalized_id
    return normalized_id


def _capture_tab_state(window) -> dict:
    """Capture the visible top-tab state for sidebar category rollback."""
    text = ""
    style = ""
    show_close_button = False
    if hasattr(window, "tab_label"):
        text = window.tab_label.text()
        style = window.tab_label.styleSheet()
    if hasattr(window, "tab_close_btn"):
        show_close_button = window.tab_close_btn.isVisible()
    return {
        "text": text,
        "style": style,
        "show_close_button": show_close_button,
    }


def _apply_sidebar_category_tab_state(window, scope: str, category_id: str) -> None:
    """Apply one closable tab state for the active sidebar category selection."""
    if not hasattr(window, "_apply_tab_state"):
        return

    label = _resolve_selected_category_label(window, scope, category_id)
    if not label:
        return
    if not view_mode_state.is_category_overlay_active(window):
        scroll_value = window.tree.verticalScrollBar().value() if hasattr(window, "tree") else 0
        return_restore_plan = view_mode_state.build_restore_plan(window, scroll_value)
        view_mode_state.activate_category_overlay(
            window,
            scope,
            category_id,
            label,
            targets=window.get_active_category_target_set(),
            return_content_mode=view_mode_state.get_visible_content_mode(window),
            return_restore_plan=return_restore_plan,
            return_tab_state=_capture_tab_state(window),
        )
    else:
        view_mode_state.update_active_category_overlay(
            window,
            scope,
            category_id,
            label,
            targets=window.get_active_category_target_set(),
        )
    window._apply_tab_state(view_tabs.get_category_tab_state(scope, label))


def clear_left_sidebar_selection(window) -> None:
    """Clear active sidebar selections on both scopes."""
    window._selected_stage_category_id = ""
    window._selected_type_category_id = ""
    view_mode_state.clear_category_overlay(window)
    if hasattr(window, "left_sidebar"):
        window.left_sidebar.clear_category_selection()


def show_full_target_view(window, force_rebuild: bool = False) -> bool:
    """Restore the unfiltered main-view tree for the active run."""
    current_run = window.combo.currentText() if hasattr(window, "combo") else ""
    if not current_run or current_run == "No runs found":
        return False
    if window.is_all_status_view:
        window._activate_selected_run_view(current_run, invalidate_snapshot=True)
        return True

    window._clear_search_ui_state()
    view_mode_state.set_tree_mode_main(window)
    window._invalidate_main_view_snapshot()
    window._set_main_run_tab_state()
    if force_rebuild:
        window._sidebar_filter_snapshot = None
    elif window._restore_sidebar_filter_snapshot(current_run):
        window._update_column_visibility_control_state()
        return True

    cached_targets_by_level = dict(getattr(window, "cached_targets_by_level", {}) or {})
    if (
        getattr(window, "_cached_targets_run", "") != current_run
        or not cached_targets_by_level
        or not window._is_main_tree_schema_active()
    ):
        window.populate_data(force_rebuild=True)
        window._apply_main_tree_column_visibility(window._main_tree_visible_columns, save_state=False)
        window._update_column_visibility_control_state()
        return True

    header = window.tree.header() if hasattr(window, "tree") else None
    window._suspend_header_layout_updates = True
    previous_tree_updates = window.tree.updatesEnabled()
    window.tree.setUpdatesEnabled(False)
    previous_header_updates = header.updatesEnabled() if header is not None else True
    if header is not None:
        header.setUpdatesEnabled(False)
    try:
        window.model.removeRows(0, window.model.rowCount())
        display_groups = window._build_display_level_groups(cached_targets_by_level, run_name=current_run)
        window._append_target_groups_to_model(display_groups, run_name=current_run)
        window.expand_tree_default()
        window._update_column_visibility_control_state()
    finally:
        if header is not None:
            header.setUpdatesEnabled(previous_header_updates)
        window.tree.setUpdatesEnabled(previous_tree_updates)
        window._suspend_header_layout_updates = False
        if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0:
            window.tree.viewport().update()
            if header is not None:
                header.viewport().update()
    return True


def can_apply_sidebar_filter_in_place(window) -> bool:
    """Return whether sidebar filtering can run without rebuilding the model."""
    if not window.combo_sel or window.is_all_status_view or window.is_search_mode:
        return False
    if not window._is_main_tree_schema_active():
        return False
    return view_mode_state.get_tree_mode(window) == view_mode_state.TREE_MODE_MAIN


def restore_sidebar_filter_snapshot(
    window,
    current_run: str = None,
    clear_snapshot: bool = True,
) -> bool:
    """Restore the pre-sidebar-filter presentation snapshot when available."""
    run_name = current_run or (window.combo.currentText() if hasattr(window, "combo") else "")
    if not run_name or run_name == "No runs found":
        return False
    restored = view_state.restore_tree_presentation_snapshot(
        window.model,
        window.tree,
        window._sidebar_filter_snapshot,
        run_name,
    )
    if restored:
        if clear_snapshot:
            window._sidebar_filter_snapshot = None
        if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0:
            window.tree.viewport().update()
            header = window.tree.header() if hasattr(window, "tree") else None
            if header is not None:
                header.viewport().update()
    return restored


def apply_sidebar_category_filter_in_place(window) -> bool:
    """Apply the active sidebar filter by hiding/restoring rows in place."""
    if not can_apply_sidebar_filter_in_place(window):
        return False

    current_run = window.combo.currentText() if hasattr(window, "combo") else ""
    if not current_run or current_run == "No runs found":
        return False

    active_targets = window.get_active_category_target_set()
    if window._sidebar_filter_snapshot is None:
        window._sidebar_filter_snapshot = view_state.capture_tree_presentation_snapshot(
            window.model,
            window.tree,
            current_run,
        )

    if not window._restore_sidebar_filter_snapshot(current_run, clear_snapshot=False):
        window._sidebar_filter_snapshot = view_state.capture_tree_presentation_snapshot(
            window.model,
            window.tree,
            current_run,
        )
        if not window._restore_sidebar_filter_snapshot(current_run, clear_snapshot=False):
            return False

    if active_targets is None:
        return window._restore_sidebar_filter_snapshot(current_run)

    view_state.filter_tree_by_targets(window.tree, window.model, set(active_targets))
    if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0:
        window.tree.viewport().update()
        header = window.tree.header() if hasattr(window, "tree") else None
        if header is not None:
            header.viewport().update()
    return True


def refresh_left_sidebar_categories(window, run_dir: str = None) -> None:
    """Reload stage/type category rows from the shared target-stage file."""
    if not hasattr(window, "left_sidebar"):
        return
    window._sidebar_filter_snapshot = None
    del run_dir
    categories, file_path = target_categories.load_target_stage_categories()
    window._stage_categories = list(categories or [])
    window._type_categories = []
    window.left_sidebar.set_stage_categories(window._stage_categories)
    window.left_sidebar.set_type_categories(window._type_categories)
    window._category_scope = window.left_sidebar.active_scope()
    window._selected_stage_category_id = window.left_sidebar.selected_category_id("stage")
    window._selected_type_category_id = window.left_sidebar.selected_category_id("type")
    if categories:
        logger.info(f"Loaded {len(categories)} sidebar categories from {file_path}")
    else:
        logger.info(f"No sidebar category data loaded from {file_path}")


def on_left_sidebar_scope_changed(window, scope: str) -> None:
    """Handle STAGE/TYPE tab switch and refresh visible tree rows."""
    window._category_scope = (scope or "stage").strip().lower()
    if not window.combo_sel or window.is_all_status_view:
        return
    if not window._apply_sidebar_category_filter_in_place():
        window.populate_data(force_rebuild=True)
    _refresh_dependency_graph_for_sidebar_change(window)
    if hasattr(window, "left_sidebar"):
        selected_category_id = window.left_sidebar.selected_category_id(window._category_scope)
        if selected_category_id:
            _apply_sidebar_category_tab_state(window, window._category_scope, selected_category_id)
            return
    view_mode_state.clear_category_overlay(window)


def on_left_sidebar_category_changed(window, scope: str, category_id: str) -> None:
    """Handle single-select category changes from the left sidebar."""
    normalized_scope = (scope or "stage").strip().lower()
    normalized_id = (category_id or "").strip()
    if normalized_scope == "type":
        window._selected_type_category_id = normalized_id
    else:
        window._selected_stage_category_id = normalized_id

    if not window.combo_sel or window.is_all_status_view:
        return
    if not window._apply_sidebar_category_filter_in_place():
        window.populate_data(force_rebuild=True)
    _refresh_dependency_graph_for_sidebar_change(window)
    _apply_sidebar_category_tab_state(window, normalized_scope, normalized_id)


def get_active_category_target_set(window):
    """Return selected category targets for current scope, or None when unscoped."""
    if not hasattr(window, "left_sidebar"):
        return None
    scope = window.left_sidebar.active_scope()
    if scope == "type":
        return None
    selected_category_id = window.left_sidebar.selected_category_id("stage")
    if not selected_category_id:
        return None
    targets = window.left_sidebar.selected_category_targets("stage")
    return set(str(target).strip() for target in targets if str(target).strip())
