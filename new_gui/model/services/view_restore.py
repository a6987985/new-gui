"""Helpers for restoring filtered main-tree views after a rebuild."""

from typing import Callable, Dict, Optional


RestorePlan = Dict[str, object]


def build_restore_plan(
    mode: str,
    scroll_value: int,
    *,
    search_text: str = "",
    status: str = "",
    trace_target: str = "",
    trace_direction: str = "",
    category_scope: str = "",
    category_id: str = "",
    category_label: str = "",
    category_targets=None,
) -> RestorePlan:
    """Build a restore plan from explicit state instead of rendered tab text."""
    normalized_mode = str(mode or "main").strip().lower() or "main"

    if normalized_mode == "trace" and trace_target:
        return {
            "mode": "trace",
            "target_name": str(trace_target),
            "inout": "in" if str(trace_direction or "").strip().lower() == "in" else "out",
            "scroll": scroll_value,
        }
    if normalized_mode == "status" and status:
        return {
            "mode": "status",
            "status": str(status).strip().lower(),
            "scroll": scroll_value,
        }
    if normalized_mode == "search" and search_text:
        return {
            "mode": "search",
            "search_text": str(search_text),
            "scroll": scroll_value,
        }
    if normalized_mode == "category" and category_id:
        return {
            "mode": "category",
            "scope": str(category_scope or "stage"),
            "category_id": str(category_id),
            "category_label": str(category_label or ""),
            "targets": list(category_targets or []),
            "scroll": scroll_value,
        }
    if normalized_mode == "all_status":
        return {"mode": "all_status", "scroll": scroll_value}
    return {"mode": "main", "scroll": scroll_value}


def apply_restore_plan(
    plan: RestorePlan,
    get_retrace_target: Callable[[str, str], list],
    filter_tree_by_targets: Callable[[set], None],
    apply_status_filter: Callable[[str], None],
    filter_tree: Callable[[str], None],
    restore_category_view: Optional[Callable[[str, str], bool]],
    set_scroll_value: Callable[[int], None],
    show_status_close_button: Optional[Callable[[], None]] = None,
) -> str:
    """Replay the filtered view described by a restore plan."""
    mode = (plan or {}).get("mode", "main")

    if mode == "trace":
        target_name = plan.get("target_name", "")
        inout = plan.get("inout")
        if target_name and inout:
            related_targets = list(get_retrace_target(target_name, inout) or [])
            if target_name not in related_targets:
                if inout == "in":
                    related_targets.append(target_name)
                else:
                    related_targets.insert(0, target_name)
            filter_tree_by_targets(set(related_targets))
    elif mode == "status":
        status = plan.get("status", "")
        if status:
            apply_status_filter(status, update_tab=False)
            if show_status_close_button is not None:
                show_status_close_button()
    elif mode == "search":
        search_text = plan.get("search_text", "")
        if search_text:
            filter_tree(search_text)
    elif mode == "category":
        scope = str(plan.get("scope") or "stage")
        category_id = str(plan.get("category_id") or "")
        if restore_category_view is not None and category_id:
            restore_category_view(scope, category_id)

    set_scroll_value(plan.get("scroll", 0))
    return mode
