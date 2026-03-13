"""Cache helpers for run-target keyed data."""

import os
from typing import Dict, Optional, Tuple


CacheKey = Tuple[str, str]
RunTargetCache = Dict[CacheKey, object]


def build_run_target_cache_key(run_dir: str, target_name: str) -> CacheKey:
    """Build a stable cache key for per-target run data."""
    return (os.path.abspath(run_dir), target_name)


def invalidate_run_target_cache(
    cache: RunTargetCache,
    run_dir: Optional[str] = None,
    target_name: Optional[str] = None,
) -> None:
    """Invalidate cached run-target data in place."""
    if run_dir is None and target_name is None:
        cache.clear()
        return

    run_key = os.path.abspath(run_dir) if run_dir else None
    keys_to_remove: list[CacheKey] = []
    for key_run, key_target in cache.keys():
        if run_key and key_run != run_key:
            continue
        if target_name and key_target != target_name:
            continue
        keys_to_remove.append((key_run, key_target))

    for key in keys_to_remove:
        cache.pop(key, None)
