"""Pure data helpers for main-tree grouping and filtering."""

from typing import Callable, Dict, List, Tuple

MIN_DISPLAY_GROUP_SIZE = 3


TargetsByLevel = Dict[int, List[str]]
LevelGroup = Tuple[int, List[str]]
CollapsibleTargetGroups = Dict[str, List[str]]
TreeDisplayNode = Dict[str, object]
LevelDisplayGroup = Dict[str, object]


def _build_target_node(target_name: str) -> TreeDisplayNode:
    """Return one display node for a real leaf target."""
    return {
        "kind": "target",
        "label": target_name,
        "target_name": target_name,
        "targets": [target_name],
        "children": [],
    }


def _build_group_node(group_label: str, target_names: List[str]) -> TreeDisplayNode:
    """Return one display node for a synthetic collapsible group."""
    ordered_targets = list(target_names or [])
    return {
        "kind": "group",
        "label": group_label,
        "target_name": "",
        "targets": ordered_targets,
        "children": [_build_target_node(target_name) for target_name in ordered_targets],
    }


def _collect_level_group_nodes(
    level_targets: List[str],
    collapsible_groups: CollapsibleTargetGroups,
) -> List[TreeDisplayNode]:
    """Build child nodes for one level while preserving target order."""
    if not level_targets:
        return []

    level_target_set = set(level_targets)
    target_positions = {target_name: index for index, target_name in enumerate(level_targets)}
    candidate_groups = []
    for group_label, group_targets in (collapsible_groups or {}).items():
        scoped_targets = [target_name for target_name in level_targets if target_name in set(group_targets)]
        if len(scoped_targets) < MIN_DISPLAY_GROUP_SIZE:
            continue
        candidate_groups.append(
            (
                target_positions[scoped_targets[0]],
                -len(scoped_targets),
                group_label,
                scoped_targets,
            )
        )

    candidate_groups.sort()
    groups_by_first_target = {
        scoped_targets[0]: {
            "label": group_label,
            "targets": scoped_targets,
        }
        for _, _, group_label, scoped_targets in candidate_groups
        if scoped_targets and all(target_name in level_target_set for target_name in scoped_targets)
    }

    display_nodes: List[TreeDisplayNode] = []
    assigned_targets = set()
    for target_name in level_targets:
        if target_name in assigned_targets:
            continue

        group_definition = groups_by_first_target.get(target_name)
        if group_definition:
            available_targets = [
                grouped_target
                for grouped_target in group_definition["targets"]
                if grouped_target not in assigned_targets
            ]
            if len(available_targets) >= MIN_DISPLAY_GROUP_SIZE:
                display_nodes.append(_build_group_node(group_definition["label"], available_targets))
                assigned_targets.update(available_targets)
                continue

        display_nodes.append(_build_target_node(target_name))
        assigned_targets.add(target_name)

    return display_nodes


def build_level_display_groups(
    targets_by_level: TargetsByLevel,
    collapsible_groups: CollapsibleTargetGroups,
) -> List[LevelDisplayGroup]:
    """Return display groups for the main tree, including synthetic timing sub-groups."""
    display_groups: List[LevelDisplayGroup] = []
    for level, targets in get_level_target_groups(targets_by_level):
        children = _collect_level_group_nodes(targets, collapsible_groups)
        display_groups.append(
            {
                "level": level,
                "targets": list(targets),
                "children": children,
                "grouped": any(child.get("kind") == "group" for child in children),
            }
        )
    return display_groups


def count_display_targets(display_groups: List[LevelDisplayGroup]) -> int:
    """Count leaf targets represented across display groups."""
    return sum(len(group.get("targets", [])) for group in display_groups)


def get_level_target_groups(targets_by_level: TargetsByLevel) -> List[LevelGroup]:
    """Return sorted non-empty target groups preserving level hierarchy."""
    if not targets_by_level:
        return []

    groups: List[LevelGroup] = []
    for level in sorted(targets_by_level.keys()):
        targets = list(targets_by_level.get(level) or [])
        if not targets:
            continue
        groups.append((level, targets))
    return groups


def filter_level_groups_by_text(targets_by_level: TargetsByLevel, text: str) -> List[LevelGroup]:
    """Return sorted level groups containing only targets matching the text."""
    text_key = (text or "").lower()
    if not text_key:
        return []

    groups: List[LevelGroup] = []
    for level, targets in get_level_target_groups(targets_by_level):
        matching_targets = [target for target in targets if text_key in target.lower()]
        if matching_targets:
            groups.append((level, matching_targets))
    return groups


def filter_level_groups_by_status(
    targets_by_level: TargetsByLevel,
    status_lookup: Callable[[str], str],
    status: str,
) -> List[LevelGroup]:
    """Return sorted level groups containing only targets matching the status."""
    status_key = (status or "").strip().lower()
    if not status_key:
        return []

    groups: List[LevelGroup] = []
    for level, targets in get_level_target_groups(targets_by_level):
        matching_targets = []
        for target_name in targets:
            target_status = (status_lookup(target_name) or "").lower()
            if target_status == status_key:
                matching_targets.append(target_name)
        if matching_targets:
            groups.append((level, matching_targets))
    return groups


def filter_level_groups_by_targets(
    targets_by_level: TargetsByLevel,
    targets_to_show,
) -> List[LevelGroup]:
    """Return sorted level groups containing only explicitly requested targets."""
    requested_targets = set(targets_to_show or [])
    if not requested_targets:
        return []

    groups: List[LevelGroup] = []
    for level, targets in get_level_target_groups(targets_by_level):
        matching_targets = [target for target in targets if target in requested_targets]
        if matching_targets:
            groups.append((level, matching_targets))
    return groups
