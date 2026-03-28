"""Helpers for editable tree interactions."""

from typing import Callable, Dict, List, Optional, Sequence

from PyQt5.QtCore import Qt

from new_gui.services import tree_rows


EDITABLE_BSUB_COLUMNS = {
    6: "queue",
    7: "cores",
    8: "memory",
}

CORE_VALUE_OPTIONS = (
    {
        "value": "1",
        "label": "1",
        "tone": "warning",
    },
    {
        "value": "2",
        "label": "2",
        "tone": "warning",
    },
    {
        "value": "4",
        "label": "4",
        "tone": "recommended",
    },
    {
        "value": "8",
        "label": "8",
        "tone": "recommended",
    },
    {
        "value": "16",
        "label": "16",
        "tone": "recommended",
    },
    {
        "value": "32",
        "label": "32",
        "tone": "danger",
    },
)

MEMORY_VALUE_OPTIONS = (
    {"value": "30000", "label": "30000"},
    {"value": "60000", "label": "60000"},
    {"value": "128000", "label": "128000"},
    {"value": "256000", "label": "256000"},
    {"value": "300000", "label": "300000"},
)

BsubEditContext = Dict[str, object]


def get_all_status_run_name(model, index) -> str:
    """Return the run name for an all-status row, if available."""
    if index is None or not index.isValid():
        return ""
    run_name_index = model.index(index.row(), 0)
    return model.data(run_name_index) or ""


def build_bsub_edit_context(model, index) -> Optional[BsubEditContext]:
    """Extract editable bsub cell context from a tree index."""
    if index is None or not index.isValid():
        return None

    column = index.column()
    param_type = EDITABLE_BSUB_COLUMNS.get(column)
    if not param_type:
        return None

    target_item = model.itemFromIndex(model.index(index.row(), 1, index.parent()))
    target_name = tree_rows.get_row_target_name(target_item)
    if not target_name:
        return None

    current_value = model.data(index)
    if current_value == "N/A":
        current_value = ""

    return {
        "column": column,
        "param_type": param_type,
        "target_name": target_name,
        "header_text": model.headerData(column, Qt.Horizontal),
        "current_value": current_value or "",
    }


def validate_bsub_value(param_type: str, new_value: str) -> Optional[str]:
    """Validate a user-entered bsub value and return an error message or None."""
    if param_type == "cores":
        if new_value not in {option["value"] for option in CORE_VALUE_OPTIONS}:
            return "Cores must be one of: 1, 2, 4, 8, 16, 32."
    if param_type == "memory":
        if new_value not in {option["value"] for option in MEMORY_VALUE_OPTIONS}:
            return "Memory must be one of: 30000, 60000, 128000, 256000, 300000."
    return None


def resolve_bsub_edit_targets(selected_targets: Sequence[str], clicked_target: str) -> List[str]:
    """Return one ordered target list for single or batch BSUB editing."""
    normalized_selected = [str(target).strip() for target in (selected_targets or []) if str(target or "").strip()]
    if len(normalized_selected) >= 2 and clicked_target in normalized_selected:
        return normalized_selected
    return [clicked_target]


def normalize_bsub_value(value: str) -> str:
    """Normalize one parsed BSUB value for editing comparisons."""
    normalized = str(value or "").strip()
    if normalized == "N/A":
        return ""
    return normalized


def resolve_popup_current_value(
    param_type: str,
    target_names: Sequence[str],
    fallback_value: str,
    run_dir: str,
    get_bsub_params: Callable[[str, str], Sequence[str]],
) -> str:
    """Resolve one popup current value for single-target and mixed batch edits."""
    normalized_targets = [str(target).strip() for target in (target_names or []) if str(target or "").strip()]
    if len(normalized_targets) <= 1:
        return str(fallback_value or "").strip()

    value_index_map = {"queue": 0, "cores": 1, "memory": 2}
    value_index = value_index_map.get(param_type)
    if value_index is None:
        return ""

    value_set = set()
    for target_name in normalized_targets:
        queue, cores, memory = get_bsub_params(run_dir, target_name)
        values = (queue, cores, memory)
        value_set.add(normalize_bsub_value(values[value_index]))
        if len(value_set) > 1:
            return ""
    return next(iter(value_set), "")


def collect_non_editable_queue_targets(
    target_names: Sequence[str],
    run_dir: str,
    get_bsub_params: Callable[[str, str], Sequence[str]],
    is_editable_queue_name: Callable[[str], bool],
) -> List[str]:
    """Return selected targets whose current queue does not start with 'pd_'."""
    blocked = []
    for target_name in target_names:
        queue_name, _, _ = get_bsub_params(run_dir, target_name)
        normalized_queue = normalize_bsub_value(queue_name)
        if normalized_queue and not is_editable_queue_name(normalized_queue):
            blocked.append(f"{target_name} ({normalized_queue})")
    return blocked


def format_target_summary(target_names: Sequence[str], limit: int = 6) -> str:
    """Return one compact target summary for notification and warning text."""
    names = [str(name).strip() for name in (target_names or []) if str(name or "").strip()]
    if not names:
        return ""
    if len(names) <= limit:
        return ", ".join(names)
    shown = ", ".join(names[:limit])
    hidden_count = len(names) - limit
    return f"{shown}, and {hidden_count} more"


def update_bsub_cells_for_targets(model, target_names: Sequence[str], column: int, new_value: str) -> int:
    """Update visible tree cells for one BSUB column across selected targets."""
    target_set = {str(target).strip() for target in (target_names or []) if str(target or "").strip()}
    if not target_set:
        return 0

    updated_rows = 0

    def walk_rows(parent_item=None):
        nonlocal updated_rows
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        for row_index in range(row_count):
            row_items = tree_rows.get_row_items(model, row_index, parent_item)
            target_item = row_items[1] if len(row_items) > 1 else None
            target_name = tree_rows.get_row_target_name(target_item)
            if target_name in target_set:
                cell_item = row_items[column] if len(row_items) > column else None
                if cell_item is not None and cell_item.text() != new_value:
                    cell_item.setText(new_value)
                updated_rows += 1

            level_item = row_items[0] if row_items else None
            if level_item and level_item.hasChildren():
                walk_rows(level_item)

    walk_rows()
    return updated_rows


def apply_bsub_value_for_targets(
    target_names: Sequence[str],
    run_dir: str,
    param_type: str,
    new_value: str,
    save_bsub_param: Callable[[str, str, str, str], bool],
    model=None,
    column: int = -1,
) -> Dict[str, List[str]]:
    """Persist one BSUB value for all selected targets and return success/failure."""
    successes: List[str] = []
    failures: List[str] = []
    for target_name in target_names:
        if save_bsub_param(run_dir, target_name, param_type, new_value):
            successes.append(target_name)
        else:
            failures.append(target_name)

    if model is not None and column >= 0 and successes:
        update_bsub_cells_for_targets(model, successes, column, new_value)

    return {"successes": successes, "failures": failures}


def build_bsub_edit_plan(
    edit_context: BsubEditContext,
    selected_targets: Sequence[str],
    run_dir: str,
    get_bsub_params: Callable[[str, str], Sequence[str]],
) -> Dict[str, object]:
    """Build one normalized BSUB edit plan for single-target or batch mode."""
    target_name = str(edit_context.get("target_name") or "").strip()
    param_type = str(edit_context.get("param_type") or "").strip()
    current_value = str(edit_context.get("current_value") or "").strip()
    edit_targets = resolve_bsub_edit_targets(selected_targets, target_name)
    popup_current_value = resolve_popup_current_value(
        param_type,
        edit_targets,
        current_value,
        run_dir,
        get_bsub_params,
    )
    return {
        "target_name": target_name,
        "param_type": param_type,
        "edit_targets": edit_targets,
        "is_batch_edit": len(edit_targets) >= 2,
        "popup_current_value": popup_current_value,
    }


def build_queue_selection_context(
    run_dir: str,
    run_base_dir: str,
    current_value: str,
    target_names: Sequence[str],
    get_bsub_params: Callable[[str, str], Sequence[str]],
    is_editable_queue_name: Callable[[str], bool],
    discover_available_queues: Callable[[str, str, str], Dict[str, object]],
) -> Dict[str, object]:
    """Return queue options or one blocking message for queue editing."""
    blocked_targets = collect_non_editable_queue_targets(
        target_names,
        run_dir,
        get_bsub_params,
        is_editable_queue_name,
    )
    if blocked_targets:
        blocked_summary = format_target_summary(blocked_targets)
        if len(target_names) <= 1:
            message = "Only queues starting with 'pd_' can be changed in the GUI."
        else:
            message = (
                "Queue batch edit is blocked because some selected targets currently use "
                f"non-editable queues (must start with 'pd_').\n\n{blocked_summary}"
            )
        return {"blocked_message": message, "options": []}

    discovery_result = discover_available_queues(run_dir, run_base_dir, current_value)
    queue_options = [
        {"value": queue_name, "label": queue_name}
        for queue_name in discovery_result.get("queues", [])
    ]
    if not queue_options:
        return {
            "blocked_message": "No editable queues starting with 'pd_' are available.",
            "options": [],
        }
    return {"blocked_message": "", "options": queue_options}


def build_core_32_warning_text(target_count: int) -> str:
    """Return the warning text for selecting 32 cores."""
    if target_count > 1:
        return f"32 cores is strongly discouraged. Apply this value to {target_count} selected targets?"
    return "32 cores is strongly discouraged. Do you want to continue?"


def build_bsub_apply_feedback(
    param_type: str,
    new_value: str,
    primary_target: str,
    edit_targets: Sequence[str],
    apply_result: Dict[str, List[str]],
) -> Dict[str, str]:
    """Build one user-facing feedback payload after applying a BSUB edit."""
    successes = list(apply_result.get("successes") or [])
    failures = list(apply_result.get("failures") or [])
    success_count = len(successes)
    total_count = len(edit_targets or [])
    is_batch_edit = total_count >= 2

    if not successes:
        failed_summary = format_target_summary(failures)
        return {
            "kind": "error",
            "title": "Error",
            "message": (
                f"Failed to update {param_type} for selected target(s). "
                f"Check whether each .csh file exists and is writable.\n\n{failed_summary}"
            ),
        }

    if not failures:
        if is_batch_edit:
            message = f"Updated {param_type} to {new_value} for {success_count} targets"
        else:
            message = f"Updated {param_type} to {new_value} for {primary_target}"
        return {"kind": "success", "title": "Saved", "message": message}

    failed_summary = format_target_summary(failures)
    return {
        "kind": "warning",
        "title": "Saved",
        "message": f"Updated {param_type} for {success_count}/{total_count} targets; failed: {failed_summary}",
    }
