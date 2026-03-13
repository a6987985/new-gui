"""Helpers for computing run-level status summaries."""


RUN_STATUS_KEYS = ["finish", "running", "failed", "skip", "scheduled", "pending"]


def build_empty_stats() -> dict:
    """Return an empty run status summary structure."""
    stats = {"total": 0}
    for key in RUN_STATUS_KEYS:
        stats[key] = 0
    return stats


def compute_run_stats(targets_by_level, status_lookup) -> dict:
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
