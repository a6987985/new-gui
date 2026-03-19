"""Column and top-button visibility picker orchestration helpers."""

from PyQt5.QtCore import QTimer, Qt

from new_gui.services import tree_rows
from new_gui.ui.builders import top_panel_builder
from new_gui.ui.widgets.button_visibility_picker import ButtonVisibilityPicker
from new_gui.ui.widgets.column_visibility_picker import ColumnVisibilityPicker


def is_main_tree_schema_active(window) -> bool:
    """Return whether the current model is the standard main-tree schema."""
    if not hasattr(window, "model"):
        return False
    expected_headers = tree_rows.MAIN_TREE_HEADERS
    if window.model.columnCount() < len(expected_headers):
        return False
    for index, header in enumerate(expected_headers):
        if str(window.model.headerData(index, Qt.Horizontal) or "").strip().lower() != header:
            return False
    return True


def get_visible_main_tree_columns(window):
    """Return currently visible main-tree columns."""
    visible_columns = set()
    for column in range(min(window.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS))):
        if not window.tree.isColumnHidden(column):
            visible_columns.add(column)
    return visible_columns


def apply_main_tree_column_visibility(window, visible_columns, save_state=True) -> None:
    """Apply persisted main-tree column visibility to the tree widget."""
    normalized_columns = set(int(column) for column in (visible_columns or []))
    normalized_columns.update(window._locked_main_tree_columns)
    max_columns = min(window.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS))
    normalized_columns = {column for column in normalized_columns if 0 <= column < max_columns}

    if save_state:
        window._main_tree_visible_columns = set(normalized_columns)

    if not is_main_tree_schema_active(window):
        return

    for column in range(max_columns):
        window.tree.setColumnHidden(column, column not in normalized_columns)

    window._apply_adaptive_target_column_width()
    window._fill_trailing_blank_with_last_column()


def update_column_visibility_control_state(window) -> None:
    """Enable the column-visibility control only for main-tree mode."""
    if not hasattr(window, "column_menu"):
        return
    enabled = is_main_tree_schema_active(window) and not getattr(window, "is_all_status_view", False)
    window.column_menu.menuAction().setEnabled(enabled)
    if not enabled and window._column_visibility_picker is not None:
        window._column_visibility_picker.hide()


def on_apply_column_visibility(window, visible_columns) -> None:
    """Apply user-picked visibility from the picker popup."""
    if getattr(window, "is_all_status_view", False):
        return
    apply_main_tree_column_visibility(window, visible_columns, save_state=True)
    if hasattr(window, "column_menu"):
        window.column_menu.hideTearOffMenu()
        window.column_menu.hide()
    if hasattr(window, "setting_menu"):
        window.setting_menu.hideTearOffMenu()
        window.setting_menu.hide()


def get_or_create_column_visibility_picker(window):
    """Return the shared column-visibility editor widget."""
    if window._column_visibility_picker is None:
        window._column_visibility_picker = ColumnVisibilityPicker(window)
        window._column_visibility_picker.apply_requested.connect(
            window._on_apply_column_visibility
        )
        window._column_visibility_picker.cancel_requested.connect(
            window._close_column_visibility_menu
        )
    return window._column_visibility_picker


def prepare_column_visibility_menu(window) -> None:
    """Refresh the column-visibility editor before opening the menu."""
    if getattr(window, "is_all_status_view", False) or not is_main_tree_schema_active(window):
        return
    picker = get_or_create_column_visibility_picker(window)
    visible_columns = get_visible_main_tree_columns(window) or set(window._main_tree_visible_columns)
    column_rows = [
        (
            index,
            window.model.headerData(index, Qt.Horizontal) or tree_rows.MAIN_TREE_HEADERS[index],
        )
        for index in range(min(window.model.columnCount(), len(tree_rows.MAIN_TREE_HEADERS)))
    ]
    picker.set_columns(
        column_rows,
        visible_columns,
        window._locked_main_tree_columns,
    )
    picker.show()


def apply_top_button_visibility(window, visible_button_ids, save_state=True) -> None:
    """Apply persisted top-button visibility to the floating button area."""
    normalized_ids = top_panel_builder.normalize_visible_top_buttons(visible_button_ids)
    if save_state:
        window._visible_top_buttons = set(normalized_ids)
    top_panel_builder.rebuild_top_action_buttons(window)


def on_apply_button_visibility(window, visible_button_ids) -> None:
    """Apply user-picked top-button visibility from the picker popup."""
    close_button_visibility_menu(window)
    normalized_ids = list(visible_button_ids or [])
    QTimer.singleShot(
        0,
        lambda ids=normalized_ids: apply_top_button_visibility(window, ids, save_state=True),
    )


def get_or_create_button_visibility_picker(window):
    """Return the shared top-button visibility editor widget."""
    if window._button_visibility_picker is None:
        window._button_visibility_picker = ButtonVisibilityPicker(window)
        window._button_visibility_picker.apply_requested.connect(
            window._on_apply_button_visibility
        )
        window._button_visibility_picker.cancel_requested.connect(
            window._close_button_visibility_menu
        )
    return window._button_visibility_picker


def prepare_button_visibility_menu(window) -> None:
    """Refresh the top-button visibility editor before opening the menu."""
    picker = get_or_create_button_visibility_picker(window)
    picker.set_buttons(
        top_panel_builder.get_top_button_choices(),
        window._visible_top_buttons,
    )
    picker.show()


def close_button_visibility_menu(window) -> None:
    """Close the button-visibility menu hierarchy."""
    if hasattr(window, "button_menu"):
        window.button_menu.hide()
    if hasattr(window, "setting_menu"):
        window.setting_menu.hide()


def close_column_visibility_menu(window) -> None:
    """Close the column-visibility menu hierarchy."""
    if hasattr(window, "column_menu"):
        window.column_menu.hide()
    if hasattr(window, "setting_menu"):
        window.setting_menu.hide()
