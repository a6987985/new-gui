"""Helpers for editable tree interactions."""

from typing import Dict, Optional

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
