"""Centralized cache helpers for run-derived data."""

from __future__ import annotations

from typing import Optional

from new_gui.infrastructure.repositories.run_cache import build_run_target_cache_key


class RunCacheManager:
    """Manage window-owned caches with explicit invalidation helpers."""

    def __init__(self, cache_state) -> None:
        self._cache_state = cache_state

    @property
    def status_cache(self):
        return self._cache_state.status_cache

    @status_cache.setter
    def status_cache(self, value) -> None:
        self._cache_state.status_cache = value

    def reset_status_cache(self) -> None:
        self._cache_state.status_cache = {"run": "", "statuses": {}, "times": {}}

    def set_targets_cache(self, run_name: str, targets_by_level, collapsible_groups) -> None:
        self._cache_state.targets_by_level = targets_by_level
        self._cache_state.cached_targets_run = run_name
        self._cache_state.collapsible_target_groups = collapsible_groups
        self._cache_state.cached_collapsible_groups_run = run_name

    def clear_targets_cache(self) -> None:
        self._cache_state.targets_by_level = {}
        self._cache_state.cached_targets_run = ""
        self._cache_state.collapsible_target_groups = {}
        self._cache_state.cached_collapsible_groups_run = ""

    def invalidate_tune_cache(self, run_dir: Optional[str] = None, target_name: Optional[str] = None) -> None:
        self._invalidate_cache_map(self._cache_state.tune_files_cache, run_dir, target_name)

    def invalidate_bsub_cache(self, run_dir: Optional[str] = None, target_name: Optional[str] = None) -> None:
        self._invalidate_cache_map(self._cache_state.bsub_params_cache, run_dir, target_name)

    @staticmethod
    def _invalidate_cache_map(cache_map, run_dir: Optional[str], target_name: Optional[str]) -> None:
        if not run_dir:
            cache_map.clear()
            return

        if not target_name:
            keys_to_remove = [key for key in cache_map if key[0] == run_dir]
            for key in keys_to_remove:
                cache_map.pop(key, None)
            return

        cache_key = build_run_target_cache_key(run_dir, target_name)
        cache_map.pop(cache_key, None)
