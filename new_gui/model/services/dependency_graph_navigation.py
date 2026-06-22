"""Dependency-graph return context helpers for the main window."""

import os

from new_gui.infrastructure.repositories import run_repository
from new_gui.model.services import view_mode_state
from new_gui.model.services import view_state


def build_dependency_graph_return_context(window, run_name: str) -> dict:
    """Capture tree context so graph navigation can restore the prior view."""
    if not run_name or run_name == "No runs found":
        return {}

    scroll_value = window.tree.verticalScrollBar().value() if hasattr(window, "tree") else 0
    is_all_status_view = view_mode_state.get_tree_mode(window) == view_mode_state.TREE_MODE_ALL_STATUS
    return {
        "run_name": run_name,
        "is_all_status_view": is_all_status_view,
        "restore_plan": None
        if is_all_status_view
        else window._build_current_view_restore_plan(scroll_value),
    }


def target_matches_graph_return_context(
    window,
    target_name: str,
    run_name: str,
    return_context: dict,
) -> bool:
    """Return whether the target belongs to the captured tree context."""
    if not target_name or not run_name or not return_context or return_context.get("is_all_status_view"):
        return False

    restore_plan = return_context.get("restore_plan") or {"mode": "main"}
    mode = restore_plan.get("mode", "main")

    if mode == "main":
        return True
    if mode == "search":
        search_text = (restore_plan.get("search_text") or "").lower()
        if not search_text:
            return False
        matcher = view_state.build_search_value_matcher(
            str(restore_plan.get("search_text") or ""),
            dict(restore_plan.get("search_options") or {}),
        )
        return matcher(target_name)
    if mode == "status":
        target_status = (window.get_target_status(run_name, target_name) or "").lower()
        return target_status == (restore_plan.get("status") or "").lower()
    if mode == "category":
        allowed_targets = {
            str(name).strip()
            for name in list(restore_plan.get("targets") or [])
            if str(name).strip()
        }
        return target_name in allowed_targets
    if mode == "trace":
        trace_target = restore_plan.get("target_name", "")
        inout = restore_plan.get("inout")
        if not trace_target or not inout:
            return False
        run_dir = os.path.join(window.run_base_dir, run_name)
        related_targets = list(run_repository.get_retrace_targets(run_dir, trace_target, inout) or [])
        if trace_target not in related_targets:
            if inout == "in":
                related_targets.append(trace_target)
            else:
                related_targets.insert(0, trace_target)
        return target_name in set(related_targets)
    return False


def apply_dependency_graph_return_context(window, return_context: dict) -> None:
    """Restore captured tree presentation before selecting a graph target."""
    restore_plan = (return_context or {}).get("restore_plan") or {"mode": "main"}
    mode = restore_plan.get("mode", "main")

    if mode == "main":
        view_mode_state.set_tree_mode_main(window)
        window._set_main_run_tab_state()
    else:
        window._restore_view_from_plan(restore_plan)


def locate_target_in_tree(window, target_name: str, return_context: dict = None) -> None:
    """Restore the tree view and select the requested target from graph dialog."""
    if hasattr(window, "show_main_view_tab"):
        window.show_main_view_tab()

    current_run = (return_context or {}).get("run_name") or window.combo.currentText()
    if not current_run or current_run == "No runs found" or not target_name:
        return

    combo_index = window.combo.findText(current_run)
    run_changed = combo_index >= 0 and window.combo.currentIndex() != combo_index
    if run_changed:
        was_blocked = window.combo.blockSignals(True)
        window.combo.setCurrentIndex(combo_index)
        window.combo.blockSignals(was_blocked)

    preserve_context = window._target_matches_graph_return_context(
        target_name,
        current_run,
        return_context or {},
    )
    used_main_view_fallback = False

    if run_changed or window.is_all_status_view:
        window._activate_selected_run_view(current_run, invalidate_snapshot=True)
        if preserve_context:
            window._apply_dependency_graph_return_context(return_context or {})
        else:
            used_main_view_fallback = not (return_context or {}).get("is_all_status_view", False)
    elif preserve_context:
        window._apply_dependency_graph_return_context(return_context or {})
    else:
        window._activate_selected_run_view(current_run, invalidate_snapshot=True)
        current_mode = ((return_context or {}).get("restore_plan") or {}).get("mode", "main")
        used_main_view_fallback = current_mode != "main"

    if used_main_view_fallback:
        window._clear_search_ui_state()
        window._set_main_run_tab_state()

    window._select_targets_in_tree([target_name])
    window.tree.setFocus()
    window.raise_()
    window.activateWindow()

    selected_targets = window.get_selected_targets()
    if target_name not in selected_targets:
        window.show_notification("Not Found", f"Target '{target_name}' was not found in the current tree", "warning")
    elif used_main_view_fallback:
        window.show_notification(
            "Locate In Tree",
            "Restored the main view because the selected target is outside the original graph-open filter.",
            "info",
        )
