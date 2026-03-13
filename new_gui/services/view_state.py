"""Tree/view state helpers for MainWindow."""

from typing import Callable, Dict, List, Sequence, Set, Tuple

from PyQt5.QtCore import QItemSelectionModel, QModelIndex, Qt

from new_gui.services import tree_rows


SerializedRow = Dict[str, object]
SnapshotData = Dict[str, object]
TargetNames = Sequence[str]
RowKey = Tuple[int, int]


def serialize_tree_row(model, tree, row_index: int, parent_item=None) -> SerializedRow:
    """Serialize one tree row into plain Python data."""
    if parent_item is None:
        get_item = lambda col: model.item(row_index, col)
        parent_index = model.index(row_index, 0)
    else:
        get_item = lambda col: parent_item.child(row_index, col)
        parent_index = parent_item.child(row_index, 0).index()

    values: List[str] = []
    tune_files = []
    for col in range(model.columnCount()):
        item = get_item(col)
        values.append(item.text() if item else "")
        if col == 3 and item is not None:
            tune_files = item.data(Qt.UserRole) or []

    children: List[SerializedRow] = []
    level_item = get_item(0)
    if level_item and level_item.hasChildren():
        for child_row in range(level_item.rowCount()):
            children.append(serialize_tree_row(model, tree, child_row, level_item))

    return {
        "values": values,
        "tune_files": list(tune_files),
        "children": children,
        "expanded": tree.isExpanded(parent_index),
    }


def capture_main_view_snapshot(model, tree, current_run: str) -> SnapshotData:
    """Capture the current main-view tree for fast restore."""
    rows: List[SerializedRow] = []
    for row in range(model.rowCount()):
        rows.append(serialize_tree_row(model, tree, row))

    return {
        "run": current_run,
        "rows": rows,
        "scroll": tree.verticalScrollBar().value(),
    }


def restore_main_view_snapshot(
    model,
    tree,
    snapshot: SnapshotData,
    current_run: str,
    status_colors: Dict[str, str],
    set_column_widths: Callable[[], None],
) -> bool:
    """Restore the cached main-view snapshot if available."""
    if not snapshot or snapshot.get("run") != current_run:
        return False

    def build_row_items(row_data: SerializedRow):
        values = row_data.get("values", [])
        tune_files = row_data.get("tune_files", [])
        padded_values = list(values[:len(tree_rows.MAIN_TREE_HEADERS)])
        if len(padded_values) < len(tree_rows.MAIN_TREE_HEADERS):
            padded_values.extend([""] * (len(tree_rows.MAIN_TREE_HEADERS) - len(padded_values)))

        row_items = tree_rows.build_target_row_items(
            padded_values[0],
            padded_values[1],
            padded_values[2],
            tune_files,
            padded_values[4],
            padded_values[5],
            padded_values[6],
            padded_values[7],
            padded_values[8],
            status_colors,
            tune_display=padded_values[3],
        )

        level_item = row_items[0] if row_items else None
        if level_item is not None:
            for child_data in row_data.get("children", []):
                level_item.appendRow(build_row_items(child_data))
        return row_items

    tree.setUpdatesEnabled(False)
    tree_rows.reset_main_tree_model(model, set_column_widths)

    for row_data in snapshot.get("rows", []):
        model.appendRow(build_row_items(row_data))

    for row, row_data in enumerate(snapshot.get("rows", [])):
        tree.setExpanded(model.index(row, 0), row_data.get("expanded", True))

    tree.verticalScrollBar().setValue(snapshot.get("scroll", 0))
    tree.setUpdatesEnabled(True)
    return True


def get_selected_targets(tree, model) -> List[str]:
    """Return currently selected targets from tree view."""
    selected_indexes = tree.selectionModel().selectedIndexes()
    if not selected_indexes:
        return []

    targets: List[str] = []
    seen_rows: Set[RowKey] = set()

    for index in selected_indexes:
        if index.column() != 1:
            continue

        row_key = (index.row(), index.parent().row() if index.parent().isValid() else -1)
        if row_key in seen_rows:
            continue
        seen_rows.add(row_key)

        if index.parent().isValid():
            target_index = model.index(index.row(), 1, index.parent())
        else:
            target_index = model.index(index.row(), 1)

        target = model.data(target_index)
        if target:
            targets.append(target)

    return targets


def select_targets_in_tree(tree, model, target_names: TargetNames) -> None:
    """Select targets in the tree by their names."""
    if not target_names:
        return

    target_set = set(target_names)
    selection_model = tree.selectionModel()
    selection_model.clearSelection()

    for row in range(model.rowCount()):
        target_index = model.index(row, 1)
        target_name = model.data(target_index)

        if target_name in target_set:
            selection_model.select(target_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            tree.scrollTo(target_index)

        level_item = model.item(row, 0)
        if level_item and level_item.hasChildren():
            for child_row in range(level_item.rowCount()):
                child_target_index = model.index(child_row, 1, level_item.index())
                child_target_name = model.data(child_target_index)
                if child_target_name in target_set:
                    selection_model.select(child_target_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)


def show_all_children(tree, item) -> None:
    """Recursively unhide all descendants of an item."""
    if item.hasChildren():
        for i in range(item.rowCount()):
            child = item.child(i)
            parent_index = item.index()
            tree.setRowHidden(i, parent_index, False)
            show_all_children(tree, child)


def filter_tree_by_targets(tree, model, targets_to_show: Set[str]) -> None:
    """Filter tree to show only specific targets."""
    def check_visibility(item):
        if item.parent():
            target_col_idx = model.index(item.row(), 1, item.parent().index())
            target_name = model.data(target_col_idx)
            should_show = target_name in targets_to_show
            tree.setRowHidden(item.row(), item.parent().index(), not should_show)
            return should_show

        target_col_idx = model.index(item.row(), 1)
        target_name = model.data(target_col_idx)
        parent_match = target_name in targets_to_show

        child_match = False
        if item.hasChildren():
            for i in range(item.rowCount()):
                c_target_idx = model.index(i, 1, item.index())
                c_target_name = model.data(c_target_idx)
                c_match = c_target_name in targets_to_show
                tree.setRowHidden(i, item.index(), not c_match)
                if c_match:
                    child_match = True

        should_show = parent_match or child_match
        tree.setRowHidden(item.row(), QModelIndex(), not should_show)

        if should_show:
            tree.expand(item.index())

        return should_show

    tree.setUpdatesEnabled(False)
    for row in range(model.rowCount()):
        item = model.item(row)
        check_visibility(item)
    tree.setUpdatesEnabled(True)


def clear_trace_filter(tree, model) -> None:
    """Restore visibility for all rows after an in-place trace filter."""
    tree.setUpdatesEnabled(False)
    for row in range(model.rowCount()):
        tree.setRowHidden(row, QModelIndex(), False)
        item = model.item(row)
        if item:
            show_all_children(tree, item)
    tree.setUpdatesEnabled(True)
