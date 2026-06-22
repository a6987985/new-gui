"""Helpers for computing run-level status summaries."""

from typing import Callable, Dict, List, Sequence, Tuple


RUN_STATUS_KEYS = ["finish", "running", "failed", "skip", "scheduled", "pending"]
GROUP_STATUS_PRIORITY = ["failed", "pending", "running", "scheduled", "skip", "finish", ""]
RunStats = Dict[str, int]
TargetsByLevel = Dict[int, List[str]]
GroupStatusSummary = Tuple[str, str]


def build_empty_stats() -> RunStats:
    """Return an empty run status summary structure."""
    stats: RunStats = {"total": 0}
    for key in RUN_STATUS_KEYS:
        stats[key] = 0
    return stats


def compute_run_stats(
    targets_by_level: TargetsByLevel,
    status_lookup: Callable[[str], str],
) -> RunStats:
    """Compute run-level status totals from grouped targets."""
    stats = build_empty_stats()
    if not targets_by_level:
        return stats

    for _, targets in sorted(targets_by_level.items()):
        for target_name in targets:
            status = (status_lookup(target_name) or "").lower()
            stats["total"] += 1
            if status in stats:
                stats[status] += 1
    return stats


def summarize_group_status(
    target_names: Sequence[str],
    status_lookup: Callable[[str], str],
) -> GroupStatusSummary:
    """Return display text and dominant status for a grouped target row."""
    normalized_targets = [target for target in list(target_names or []) if target]
    total_count = len(normalized_targets)
    if total_count == 0:
        return "", ""

    counts: Dict[str, int] = {}
    ordered_statuses: List[str] = []
    for target_name in normalized_targets:
        status = (status_lookup(target_name) or "").strip().lower()
        counts[status] = counts.get(status, 0) + 1
        ordered_statuses.append(status)

    unique_statuses = [status for status, count in counts.items() if count > 0]
    if len(unique_statuses) == 1:
        only_status = unique_statuses[0]
        if not only_status:
            return "", ""
        return f"all {only_status}", only_status

    for status in GROUP_STATUS_PRIORITY:
        count = counts.get(status, 0)
        if count > 0:
            label = status or "unknown"
            return f"{label} {count}/{total_count}", status

    fallback_status = ordered_statuses[0] if ordered_statuses else ""
    if not fallback_status:
        return "", ""
    return f"{fallback_status} {counts.get(fallback_status, 0)}/{total_count}", fallback_status
