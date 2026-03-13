"""Pure data helpers for main-tree grouping and filtering."""


def get_level_target_groups(targets_by_level) -> list:
    """Return sorted non-empty target groups preserving level hierarchy."""
    if not targets_by_level:
        return []

    groups = []
    for level in sorted(targets_by_level.keys()):
        targets = list(targets_by_level.get(level) or [])
        if not targets:
            continue
        groups.append((level, targets))
    return groups


def filter_level_groups_by_text(targets_by_level, text: str) -> list:
    """Return sorted level groups containing only targets matching the text."""
    text_key = (text or "").lower()
    if not text_key:
        return []

    groups = []
    for level, targets in get_level_target_groups(targets_by_level):
        matching_targets = [target for target in targets if text_key in target.lower()]
        if matching_targets:
            groups.append((level, matching_targets))
    return groups


def filter_level_groups_by_status(targets_by_level, status_lookup, status: str) -> list:
    """Return sorted level groups containing only targets matching the status."""
    status_key = (status or "").strip().lower()
    if not status_key:
        return []

    groups = []
    for level, targets in get_level_target_groups(targets_by_level):
        matching_targets = []
        for target_name in targets:
            target_status = (status_lookup(target_name) or "").lower()
            if target_status == status_key:
                matching_targets.append(target_name)
        if matching_targets:
            groups.append((level, matching_targets))
    return groups


def count_targets_in_groups(groups) -> int:
    """Count total targets across grouped rows."""
    return sum(len(targets) for _, targets in groups)
