"""Explicit window view-state helpers decoupled from rendered tab text."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List


CONTENT_MODE_MAIN = "main"
CONTENT_MODE_GRAPH = "graph"

TREE_MODE_MAIN = "main"
TREE_MODE_ALL_STATUS = "all_status"
TREE_MODE_SEARCH = "search"
TREE_MODE_STATUS = "status"
TREE_MODE_TRACE = "trace"


@dataclass
class TreeModeState:
    """Structured state for the tree presentation mode."""

    mode: str = TREE_MODE_MAIN
    search_text: str = ""
    search_options: Dict[str, bool] = field(default_factory=dict)
    status_filter: str = ""
    trace_target: str = ""
    trace_direction: str = ""


@dataclass
class CategoryOverlayState:
    """State for the temporary category overlay shown on top of the tree or graph."""

    active: bool = False
    scope: str = "stage"
    category_id: str = ""
    category_label: str = ""
    targets: List[str] = field(default_factory=list)
    return_content_mode: str = CONTENT_MODE_MAIN
    return_restore_plan: Dict[str, object] = field(default_factory=dict)
    return_tab_state: Dict[str, object] = field(default_factory=dict)


@dataclass
class WindowViewState:
    """Single source of truth for main-window content and tree state."""

    content_mode: str = CONTENT_MODE_MAIN
    tree: TreeModeState = field(default_factory=TreeModeState)
    category_overlay: CategoryOverlayState = field(default_factory=CategoryOverlayState)


def ensure_window_view_state(window) -> WindowViewState:
    """Create the explicit view-state container on demand and sync legacy flags."""
    state = window.__dict__.get("_window_view_state")
    if isinstance(state, WindowViewState):
        _sync_legacy_flags(window, state)
        return state

    state = WindowViewState()
    window.__dict__["_window_view_state"] = state
    _sync_legacy_flags(window, state)
    return state


def _sync_legacy_flags(window, state: WindowViewState) -> None:
    """Keep legacy ad-hoc flags synchronized during the transition."""
    window._active_content_mode = state.content_mode
    tree_mode = state.tree.mode
    window.is_all_status_view = tree_mode == TREE_MODE_ALL_STATUS
    window.is_search_mode = tree_mode == TREE_MODE_SEARCH and bool(state.tree.search_text)
    overlay = state.category_overlay
    window._sidebar_category_tab_active = bool(overlay.active)
    if overlay.active:
        window._sidebar_category_return_state = {
            "content_mode": overlay.return_content_mode,
            "restore_plan": deepcopy(overlay.return_restore_plan),
            "tab_state": deepcopy(overlay.return_tab_state),
        }
    else:
        window._sidebar_category_return_state = None


def get_content_mode(window) -> str:
    """Return the active content mode."""
    return ensure_window_view_state(window).content_mode


def get_visible_content_mode(window) -> str:
    """Return the visible content page mode and repair stale stored state when needed."""
    tabs = getattr(window, "_content_mode_tabs", None)
    graph_page = getattr(window, "_graph_view_page", None)
    if tabs is None or graph_page is None:
        return get_content_mode(window)

    visible_mode = CONTENT_MODE_GRAPH if tabs.currentWidget() is graph_page else CONTENT_MODE_MAIN
    if ensure_window_view_state(window).content_mode != visible_mode:
        set_content_mode(window, visible_mode)
    return visible_mode


def set_content_mode(window, mode: str) -> None:
    """Store the active content mode."""
    state = ensure_window_view_state(window)
    normalized_mode = str(mode or CONTENT_MODE_MAIN).strip().lower()
    state.content_mode = CONTENT_MODE_GRAPH if normalized_mode == CONTENT_MODE_GRAPH else CONTENT_MODE_MAIN
    _sync_legacy_flags(window, state)


def get_tree_mode(window) -> str:
    """Return the base tree presentation mode."""
    return ensure_window_view_state(window).tree.mode


def get_active_view_mode(window) -> str:
    """Return the effective visible mode, including category overlays."""
    state = ensure_window_view_state(window)
    if state.category_overlay.active:
        return "category"
    return state.tree.mode


def set_tree_mode_main(window) -> None:
    """Switch the tree state back to the normal single-run mode."""
    state = ensure_window_view_state(window)
    state.tree = TreeModeState(mode=TREE_MODE_MAIN)
    _sync_legacy_flags(window, state)


def set_tree_mode_all_status(window) -> None:
    """Switch the tree state to the all-status overview."""
    state = ensure_window_view_state(window)
    state.tree = TreeModeState(mode=TREE_MODE_ALL_STATUS)
    _sync_legacy_flags(window, state)


def _normalize_search_options(search_options: Dict[str, object] | None) -> Dict[str, bool]:
    """Return one normalized copy of the header-search option flags."""
    return {
        "case_sensitive": bool((search_options or {}).get("case_sensitive", False)),
        "whole_word": bool((search_options or {}).get("whole_word", False)),
        "regex": bool((search_options or {}).get("regex", False)),
    }


def set_tree_mode_search(window, search_text: str, search_options: Dict[str, object] | None = None) -> None:
    """Switch the tree state to search mode with one explicit query."""
    normalized_text = str(search_text or "")
    state = ensure_window_view_state(window)
    state.tree = TreeModeState(
        mode=TREE_MODE_SEARCH if normalized_text else TREE_MODE_MAIN,
        search_text=normalized_text,
        search_options=_normalize_search_options(search_options) if normalized_text else {},
    )
    _sync_legacy_flags(window, state)


def clear_search_state(window) -> None:
    """Clear the tracked search text without disturbing non-search modes."""
    state = ensure_window_view_state(window)
    state.tree.search_text = ""
    state.tree.search_options = {}
    if state.tree.mode == TREE_MODE_SEARCH:
        state.tree.mode = TREE_MODE_MAIN
    _sync_legacy_flags(window, state)


def set_tree_mode_status(window, status: str) -> None:
    """Switch the tree state to one explicit status filter."""
    normalized_status = str(status or "").strip().lower()
    state = ensure_window_view_state(window)
    state.tree = TreeModeState(
        mode=TREE_MODE_STATUS if normalized_status else TREE_MODE_MAIN,
        status_filter=normalized_status,
    )
    _sync_legacy_flags(window, state)


def set_tree_mode_trace(window, target_name: str, direction: str) -> None:
    """Switch the tree state to one explicit trace filter."""
    normalized_target = str(target_name or "").strip()
    normalized_direction = "in" if str(direction or "").strip().lower() == "in" else "out"
    state = ensure_window_view_state(window)
    state.tree = TreeModeState(
        mode=TREE_MODE_TRACE if normalized_target else TREE_MODE_MAIN,
        trace_target=normalized_target,
        trace_direction=normalized_direction if normalized_target else "",
    )
    _sync_legacy_flags(window, state)


def build_restore_plan(window, scroll_value: int) -> Dict[str, object]:
    """Build a restore plan from the explicit view state instead of tab text."""
    state = ensure_window_view_state(window)
    if state.category_overlay.active:
        overlay = state.category_overlay
        return {
            "mode": "category",
            "scope": overlay.scope,
            "category_id": overlay.category_id,
            "category_label": overlay.category_label,
            "targets": list(overlay.targets or []),
            "scroll": scroll_value,
        }

    tree_state = state.tree
    if tree_state.mode == TREE_MODE_TRACE and tree_state.trace_target:
        return {
            "mode": "trace",
            "target_name": tree_state.trace_target,
            "inout": tree_state.trace_direction or "out",
            "scroll": scroll_value,
        }
    if tree_state.mode == TREE_MODE_STATUS and tree_state.status_filter:
        return {
            "mode": "status",
            "status": tree_state.status_filter,
            "scroll": scroll_value,
        }
    if tree_state.mode == TREE_MODE_SEARCH and tree_state.search_text:
        return {
            "mode": "search",
            "search_text": tree_state.search_text,
            "search_options": _normalize_search_options(tree_state.search_options),
            "scroll": scroll_value,
        }
    if tree_state.mode == TREE_MODE_ALL_STATUS:
        return {
            "mode": TREE_MODE_ALL_STATUS,
            "scroll": scroll_value,
        }
    return {"mode": TREE_MODE_MAIN, "scroll": scroll_value}


def set_tree_mode_from_restore_plan(window, restore_plan: Dict[str, object]) -> None:
    """Synchronize the explicit tree mode from one restore-plan payload."""
    plan = dict(restore_plan or {})
    mode = str(plan.get("mode") or TREE_MODE_MAIN).strip().lower()
    if mode == TREE_MODE_SEARCH:
        set_tree_mode_search(
            window,
            str(plan.get("search_text") or ""),
            dict(plan.get("search_options") or {}),
        )
        return
    if mode == TREE_MODE_STATUS:
        set_tree_mode_status(window, str(plan.get("status") or ""))
        return
    if mode == TREE_MODE_TRACE:
        set_tree_mode_trace(
            window,
            str(plan.get("target_name") or ""),
            str(plan.get("inout") or "out"),
        )
        return
    if mode == TREE_MODE_ALL_STATUS:
        set_tree_mode_all_status(window)
        return
    set_tree_mode_main(window)


def is_category_overlay_active(window) -> bool:
    """Return whether the category overlay is currently active."""
    return bool(ensure_window_view_state(window).category_overlay.active)


def activate_category_overlay(
    window,
    scope: str,
    category_id: str,
    category_label: str,
    targets=None,
    return_content_mode: str = CONTENT_MODE_MAIN,
    return_restore_plan: Dict[str, object] | None = None,
    return_tab_state: Dict[str, object] | None = None,
) -> None:
    """Activate the category overlay and store the state needed for rollback."""
    state = ensure_window_view_state(window)
    state.category_overlay = CategoryOverlayState(
        active=True,
        scope=str(scope or "stage").strip().lower() or "stage",
        category_id=str(category_id or "").strip(),
        category_label=str(category_label or "").strip(),
        targets=list(targets or []),
        return_content_mode=str(return_content_mode or CONTENT_MODE_MAIN).strip().lower() or CONTENT_MODE_MAIN,
        return_restore_plan=deepcopy(return_restore_plan or {}),
        return_tab_state=deepcopy(return_tab_state or {}),
    )
    _sync_legacy_flags(window, state)


def update_active_category_overlay(window, scope: str, category_id: str, category_label: str, targets=None) -> None:
    """Update the visible category overlay without overwriting its rollback state."""
    state = ensure_window_view_state(window)
    if not state.category_overlay.active:
        activate_category_overlay(
            window,
            scope,
            category_id,
            category_label,
            targets=targets,
        )
        return

    state.category_overlay.scope = str(scope or "stage").strip().lower() or "stage"
    state.category_overlay.category_id = str(category_id or "").strip()
    state.category_overlay.category_label = str(category_label or "").strip()
    state.category_overlay.targets = list(targets or [])
    _sync_legacy_flags(window, state)


def clear_category_overlay(window) -> None:
    """Clear the active category overlay state."""
    state = ensure_window_view_state(window)
    state.category_overlay = CategoryOverlayState()
    _sync_legacy_flags(window, state)


def get_category_return_content_mode(window) -> str:
    """Return the stored content mode for category-overlay rollback."""
    return ensure_window_view_state(window).category_overlay.return_content_mode


def get_category_return_restore_plan(window) -> Dict[str, object]:
    """Return the stored tree restore plan for category-overlay rollback."""
    return deepcopy(ensure_window_view_state(window).category_overlay.return_restore_plan)
