"""Adapter that derives an :class:`AgentSessionContext` from a live MainWindow.

This module is the only place that knows how to read runtime data from the
``MainWindow``. The Agent layer itself never reaches into widget state; it
consumes the frozen snapshot returned here. Keeping the read paths centralized
makes it safe to evolve ``MainWindow`` without leaking new dependencies into
``application/agent``.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from new_gui.application.agent.agent_context import (
    AgentSessionContext,
    snapshot_session_context,
)


def _safe_current_run(window: object) -> Optional[str]:
    combo = getattr(window, "combo", None)
    if combo is None:
        return None
    try:
        value = combo.currentText()
    except Exception:
        return None
    text = str(value or "").strip()
    if not text or text == "No runs found":
        return None
    return text


def _safe_selected_targets(window: object) -> List[str]:
    method = getattr(window, "get_selected_targets", None)
    if not callable(method):
        return []
    try:
        result = method() or []
    except Exception:
        return []
    return [str(item) for item in result]


def _safe_visible_targets(window: object, run_name: Optional[str]) -> List[str]:
    if not run_name:
        return []
    cached_run = getattr(window, "_cached_targets_run", "") or ""
    if cached_run and cached_run != run_name:
        # Stale cache from a previously selected run -- treat visibility as unknown
        # so the Agent never targets phantom items.
        return []
    cache = getattr(window, "cached_targets_by_level", None) or {}
    flattened: List[str] = []
    seen = set()
    try:
        for level in sorted(cache.keys()):
            for target in cache.get(level, []) or []:
                text = str(target or "").strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                flattened.append(text)
    except Exception:
        return []
    return flattened


def _safe_view_mode(window: object) -> str:
    mode = getattr(window, "_active_content_mode", "main") or "main"
    return str(mode)


def _safe_status_filter(window: object) -> Optional[str]:
    candidate = (
        getattr(window, "_active_status_filter", None)
        or getattr(window, "active_status_filter", None)
    )
    if candidate is None:
        return None
    text = str(candidate).strip()
    return text or None


def snapshot_from_window(window: object) -> AgentSessionContext:
    """Build an :class:`AgentSessionContext` from a live ``MainWindow``."""
    current_run = _safe_current_run(window)
    return snapshot_session_context(
        run_base_dir=str(getattr(window, "run_base_dir", "") or ""),
        current_run=current_run,
        selected_targets=_safe_selected_targets(window),
        visible_targets=_safe_visible_targets(window, current_run),
        view_mode=_safe_view_mode(window),
        status_filter=_safe_status_filter(window),
    )
