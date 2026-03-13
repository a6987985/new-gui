"""Pure data helpers for main-tree grouping and filtering."""

from typing import Callable, Dict, List, Tuple


TargetsByLevel = Dict[int, List[str]]
LevelGroup = Tuple[int, List[str]]


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


def count_targets_in_groups(groups: List[LevelGroup]) -> int:
    """Count total targets across grouped rows."""
    return sum(len(targets) for _, targets in groups)
