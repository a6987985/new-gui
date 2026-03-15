"""Helpers for editable tree interactions."""

from typing import Dict, Optional

from PyQt5.QtCore import Qt

from new_gui.services import tree_rows


EDITABLE_BSUB_COLUMNS = {
    6: "queue",
    7: "cores",
    8: "memory",
}

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
    if param_type == "cores" and not new_value.isdigit():
        return "Cores must be a number."
    if param_type == "memory" and not new_value.isdigit():
        return "Memory must be a number (MB)."
    return None
