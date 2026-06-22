"""Tune/BSUB runtime helpers delegated from MainWindow."""

from PyQt5.QtCore import Qt

from new_gui.shared.config.settings import logger
from new_gui.infrastructure.repositories import run_repository
from new_gui.model.services import tree_rows


def get_tune_files(window, run_dir: str, target_name: str) -> list:
    """Return tune files for one target, with cache support."""
    return run_repository.get_tune_files(
        run_dir,
        target_name,
        window._tune_files_cache,
    )


def get_tune_display(window, run_dir: str, target_name: str) -> str:
    """Return comma-separated tune suffixes for tree cell display."""
    tune_files = window.get_tune_files(run_dir, target_name)
    if not tune_files:
        return ""
    return ", ".join([suffix for suffix, _ in tune_files])


def get_tune_candidates_from_cmd(run_dir: str, target_name: str) -> list:
    """Parse tunesource entries from cmds/<target>.cmd."""
    return run_repository.get_tune_candidates_from_cmd(run_dir, target_name)


def refresh_tune_cells_for_target(window, target_name: str) -> None:
    """Refresh tune text and payload for one target row in the current model."""
    if not window.combo_sel or not hasattr(window, "model") or window.model is None:
        return

    tune_files = window.get_tune_files(window.combo_sel, target_name)
    tune_display = ", ".join([suffix for suffix, _ in tune_files]) if tune_files else ""

    def update_cells(target_item, tune_item):
        if not target_item or not tune_item:
            return
        if tree_rows.get_row_target_name(target_item) != target_name:
            return
        tune_item.setText(tune_display)
        tune_item.setData(tune_files, Qt.UserRole)

    def walk_rows(parent_item=None):
        row_count = parent_item.rowCount() if parent_item is not None else window.model.rowCount()
        for row_idx in range(row_count):
            row_items = tree_rows.get_row_items(window.model, row_idx, parent_item)
            update_cells(row_items[1] if len(row_items) > 1 else None, row_items[3] if len(row_items) > 3 else None)
            level_item = row_items[0] if row_items else None
            if level_item and level_item.hasChildren():
                walk_rows(level_item)

    walk_rows()


def get_bsub_params(window, run_dir: str, target_name: str) -> tuple:
    """Return BSUB queue/core/memory values from target csh."""
    return run_repository.get_bsub_params(
        run_dir,
        target_name,
        window._bsub_params_cache,
    )


def save_bsub_param(window, run_dir, target_name, param_type, new_value) -> bool:
    """Persist one BSUB parameter update and invalidate cache on success."""
    if run_repository.save_bsub_param(run_dir, target_name, param_type, new_value):
        window._invalidate_bsub_cache(run_dir, target_name)
        logger.info(f"Updated {param_type} to {new_value} for {target_name}")
        return True
    return False
