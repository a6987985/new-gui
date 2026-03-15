"""Tree/view state helpers for MainWindow."""

from typing import Callable, Dict, List, Sequence, Set

from PyQt5.QtCore import QItemSelectionModel, QModelIndex, Qt

from new_gui.services import tree_rows


SerializedRow = Dict[str, object]
SnapshotData = Dict[str, object]
TargetNames = Sequence[str]


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
    target_item = get_item(1)
    if level_item and level_item.hasChildren():
        for child_row in range(level_item.rowCount()):
            children.append(serialize_tree_row(model, tree, child_row, level_item))

    return {
        "values": values,
        "tune_files": list(tune_files),
        "row_kind": tree_rows.get_row_kind(target_item),
        "target_name": tree_rows.get_row_target_name(target_item),
        "descendant_targets": tree_rows.get_row_targets(target_item),
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
        row_kind = row_data.get("row_kind", tree_rows.ROW_KIND_TARGET)
        descendant_targets = row_data.get("descendant_targets", [])
        padded_values = list(values[:len(tree_rows.MAIN_TREE_HEADERS)])
        if len(padded_values) < len(tree_rows.MAIN_TREE_HEADERS):
            padded_values.extend([""] * (len(tree_rows.MAIN_TREE_HEADERS) - len(padded_values)))

        if row_kind not in (tree_rows.ROW_KIND_GROUP, tree_rows.ROW_KIND_LEVEL):
            row_items = tree_rows.build_target_row_items(
                padded_values[0],
                row_data.get("target_name") or padded_values[1],
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
        else:
            row_items = tree_rows.build_container_row_items(
                padded_values[0],
                padded_values[1],
                row_kind or tree_rows.ROW_KIND_GROUP,
                descendant_targets=descendant_targets,
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
    selection_model = tree.selectionModel()
    if selection_model is None:
        return []

    selected_indexes = selection_model.selectedRows(1)
    if not selected_indexes:
        return []

    targets: List[str] = []
    seen_targets: Set[str] = set()
    for index in selected_indexes:
        item = model.itemFromIndex(index)
        target_name = tree_rows.get_row_target_name(item)
        if not target_name or target_name in seen_targets:
            continue
        seen_targets.add(target_name)
        targets.append(target_name)

    return targets


def get_selected_action_targets(tree, model) -> List[str]:
    """Return actionable target names for the current tree selection.

    Leaf target rows contribute their own target name.
    Synthetic group rows contribute all descendant leaf targets so batch
    execute actions can operate on the full group.
    """
    selection_model = tree.selectionModel()
    if selection_model is None:
        return []

    selected_indexes = selection_model.selectedRows(1)
    if not selected_indexes:
        return []

    action_targets: List[str] = []
    seen_targets: Set[str] = set()
    for index in selected_indexes:
        item = model.itemFromIndex(index)
        row_kind = tree_rows.get_row_kind(item)
        if row_kind == tree_rows.ROW_KIND_GROUP:
            candidate_targets = tree_rows.get_row_targets(item)
        else:
            target_name = tree_rows.get_row_target_name(item)
            candidate_targets = [target_name] if target_name else []

        for target_name in candidate_targets:
            if not target_name or target_name in seen_targets:
                continue
            seen_targets.add(target_name)
            action_targets.append(target_name)

    return action_targets


def select_targets_in_tree(tree, model, target_names: TargetNames) -> None:
    """Select targets in the tree by their names."""
    if not target_names:
        return

    target_set = set(target_names)
    selection_model = tree.selectionModel()
    selection_model.clearSelection()

    first_match = None

    def walk_rows(parent_item=None):
        nonlocal first_match
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        for row in range(row_count):
            row_items = tree_rows.get_row_items(model, row, parent_item)
            target_item = row_items[1] if len(row_items) > 1 else None
            target_name = tree_rows.get_row_target_name(target_item)
            if target_name in target_set and target_item is not None:
                target_index = target_item.index()
                selection_model.select(target_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                parent_index = target_index.parent()
                while parent_index.isValid():
                    tree.expand(parent_index)
                    parent_index = parent_index.parent()
                if first_match is None:
                    first_match = target_index

            level_item = row_items[0] if row_items else None
            if level_item and level_item.hasChildren():
                walk_rows(level_item)

    walk_rows()
    if first_match is not None:
        tree.scrollTo(first_match)


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
    def check_visibility(row_index: int, parent_item=None) -> bool:
        row_items = tree_rows.get_row_items(model, row_index, parent_item)
        level_item = row_items[0] if row_items else None
        target_item = row_items[1] if len(row_items) > 1 else None
        represented_targets = set(tree_rows.get_row_targets(target_item))

        child_match = False
        if level_item and level_item.hasChildren():
            for child_row in range(level_item.rowCount()):
                if check_visibility(child_row, level_item):
                    child_match = True

        should_show = bool(represented_targets & targets_to_show) or child_match
        parent_index = parent_item.index() if parent_item is not None else QModelIndex()
        tree.setRowHidden(row_index, parent_index, not should_show)

        if should_show and level_item and level_item.hasChildren():
            tree.expand(level_item.index())

        return should_show

    tree.setUpdatesEnabled(False)
    for row in range(model.rowCount()):
        check_visibility(row)
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


def expand_all_except_groups(tree, model) -> None:
    """Expand the visible tree while keeping synthetic group rows collapsed."""
    if tree is None or model is None:
        return

    tree.setUpdatesEnabled(False)
    tree.expandAll()

    def collapse_group_rows(parent_item=None) -> None:
        row_count = parent_item.rowCount() if parent_item is not None else model.rowCount()
        for row in range(row_count):
            row_items = tree_rows.get_row_items(model, row, parent_item)
            level_item = row_items[0] if row_items else None
            target_item = row_items[1] if len(row_items) > 1 else None
            if level_item is None:
                continue

            if tree_rows.get_row_kind(target_item) == tree_rows.ROW_KIND_GROUP:
                tree.collapse(level_item.index())

            if level_item.hasChildren():
                collapse_group_rows(level_item)

    collapse_group_rows()
    tree.setUpdatesEnabled(True)
