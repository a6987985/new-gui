"""Main-tree display-group orchestration helpers for MainWindow."""

from new_gui.config.settings import STATUS_COLORS
from new_gui.services import status_summary
from new_gui.services import tree_rows
from new_gui.services import tree_structure


def ensure_cached_collapsible_target_groups(window, run_name: str):
    """Load grouped display definitions for the active run when needed."""
    normalized_run = run_name or ""
    if normalized_run and (
        window._cached_collapsible_target_groups_run != normalized_run
        or not window.cached_collapsible_target_groups
    ):
        window.cached_collapsible_target_groups = window.parse_collapsible_target_groups(normalized_run)
        window._cached_collapsible_target_groups_run = normalized_run
    return window.cached_collapsible_target_groups


def build_display_level_groups(window, targets_by_level, run_name: str = None):
    """Build level/group/target display structure for the main tree."""
    current_run = run_name if run_name is not None else window.combo.currentText()
    collapsible_groups = ensure_cached_collapsible_target_groups(window, current_run)
    return tree_structure.build_level_display_groups(targets_by_level, collapsible_groups)


def build_target_row_items(
    window,
    level_text,
    target_name: str,
    status_value: str = None,
    run_name: str = None,
) -> list:
    """Build one standard main-tree row for a target."""
    current_run = run_name if run_name is not None else window.combo.currentText()
    run_dir = getattr(window, "combo_sel", None)
    row_status = (
        window.get_target_status(current_run, target_name)
        if status_value is None
        else status_value
    )
    tune_files = window.get_tune_files(run_dir, target_name) if run_dir else []
    start_time, end_time = window.get_target_times(current_run, target_name)
    queue, cores, memory = (
        window.get_bsub_params(run_dir, target_name)
        if run_dir
        else ("", "", "")
    )
    return tree_rows.build_target_row_items(
        level_text,
        target_name,
        row_status,
        tune_files,
        start_time,
        end_time,
        queue,
        cores,
        memory,
        STATUS_COLORS,
    )


def build_container_row_items(
    level_text,
    label_text: str,
    row_kind: str,
    descendant_targets,
    status_value: str = "",
    status_key: str = "",
) -> list:
    """Build one synthetic main-tree row for a level or collapsible group container."""
    return tree_rows.build_container_row_items(
        level_text,
        label_text,
        row_kind,
        descendant_targets=descendant_targets,
        status_value=status_value,
        status_key=status_key,
        status_colors=STATUS_COLORS,
    )


def summarize_group_row_status(window, target_names, run_name: str = None, status_value: str = None):
    """Return display text and dominant status key for one synthetic group row."""
    current_run = run_name if run_name is not None else window.combo.currentText()
    if status_value is not None:
        normalized_status = (status_value or "").strip().lower()
        if not normalized_status:
            return "", ""
        return f"all {normalized_status}", normalized_status

    return status_summary.summarize_group_status(
        target_names,
        lambda target_name: window.get_target_status(current_run, target_name),
    )


def append_display_node_to_parent(window, parent_item, node: dict, run_name: str = None, status_value: str = None) -> int:
    """Append one display node and all descendants below an existing parent item."""
    node_kind = node.get("kind", tree_rows.ROW_KIND_TARGET)
    node_label = node.get("label", "")
    node_targets = list(node.get("targets", []) or [])

    if node_kind == tree_rows.ROW_KIND_TARGET:
        child_row = build_target_row_items(
            window,
            "",
            node.get("target_name", node_label),
            status_value=status_value,
            run_name=run_name,
        )
        parent_item.appendRow(child_row)
        return 1

    group_status_text, group_status_key = summarize_group_row_status(
        window,
        node_targets,
        run_name=run_name,
        status_value=status_value,
    )
    child_row = build_container_row_items(
        "",
        node_label,
        node_kind,
        node_targets,
        status_value=group_status_text,
        status_key=group_status_key,
    )
    parent_item.appendRow(child_row)

    appended_count = 0
    child_parent_item = child_row[0]
    for child_node in node.get("children", []):
        appended_count += append_display_node_to_parent(
            window,
            child_parent_item,
            child_node,
            run_name=run_name,
            status_value=status_value,
        )
    return appended_count


def split_level_anchor_target(child_nodes):
    """Return the top-level anchor target and remaining child nodes for one level."""
    ordered_nodes = list(child_nodes or [])
    if not ordered_nodes:
        return "", []

    first_node = ordered_nodes[0]
    if first_node.get("kind") == tree_rows.ROW_KIND_TARGET:
        return first_node.get("target_name", ""), ordered_nodes[1:]

    if first_node.get("kind") == tree_rows.ROW_KIND_GROUP:
        group_targets = list(first_node.get("targets", []) or [])
        if not group_targets:
            return "", ordered_nodes[1:]

        anchor_target = group_targets[0]
        remaining_targets = group_targets[1:]
        remaining_children = list(first_node.get("children", []) or [])[1:]
        remaining_nodes = []
        if remaining_targets and remaining_children:
            remaining_nodes.append(
                {
                    "kind": tree_rows.ROW_KIND_GROUP,
                    "label": first_node.get("label", ""),
                    "target_name": "",
                    "targets": remaining_targets,
                    "children": remaining_children,
                }
            )
        remaining_nodes.extend(ordered_nodes[1:])
        return anchor_target, remaining_nodes

    return "", ordered_nodes[1:]


def get_level_root_group_node(targets, child_nodes):
    """Return the top-level group node when one level is fully generic-grouped."""
    ordered_targets = list(targets or [])
    ordered_nodes = list(child_nodes or [])
    if len(ordered_nodes) != 1:
        return None

    first_node = ordered_nodes[0]
    if first_node.get("kind") != tree_rows.ROW_KIND_GROUP:
        return None

    group_targets = list(first_node.get("targets", []) or [])
    if not group_targets or len(group_targets) != len(ordered_targets):
        return None

    if group_targets != ordered_targets:
        return None

    return first_node


def append_target_groups_to_model(window, display_groups, run_name: str = None, status_value: str = None) -> int:
    """Append grouped display nodes to the model using the standard main-tree structure."""
    appended_target_count = 0
    for display_group in display_groups:
        level = display_group.get("level")
        targets = list(display_group.get("targets", []) or [])
        children = list(display_group.get("children", []) or [])

        if not targets or not children:
            continue

        level_root_group = get_level_root_group_node(targets, children)
        if level_root_group is not None:
            group_status_text, group_status_key = summarize_group_row_status(
                window,
                level_root_group.get("targets", []),
                run_name=run_name,
                status_value=status_value,
            )
            parent_row = build_container_row_items(
                str(level),
                level_root_group.get("label", ""),
                tree_rows.ROW_KIND_GROUP,
                level_root_group.get("targets", []),
                status_value=group_status_text,
                status_key=group_status_key,
            )
            window.model.appendRow(parent_row)

            level_parent_item = parent_row[0]
            for child_node in level_root_group.get("children", []):
                appended_target_count += append_display_node_to_parent(
                    window,
                    level_parent_item,
                    child_node,
                    run_name=run_name,
                    status_value=status_value,
                )
            continue

        anchor_target, remaining_children = split_level_anchor_target(children)
        if not anchor_target:
            anchor_target = targets[0]
            remaining_children = children

        parent_row = build_target_row_items(
            window,
            str(level),
            anchor_target,
            status_value=status_value,
            run_name=run_name,
        )
        window.model.appendRow(parent_row)
        appended_target_count += 1

        level_parent_item = parent_row[0]
        for child_node in remaining_children:
            appended_target_count += append_display_node_to_parent(
                window,
                level_parent_item,
                child_node,
                run_name=run_name,
                status_value=status_value,
            )

    return appended_target_count
