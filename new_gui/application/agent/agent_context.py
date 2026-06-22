"""Read-only session context exposed to the Executable Agent.

The Agent never reads ``MainWindow`` attributes directly. A presenter calls
:func:`snapshot_session_context` to capture the relevant runtime state and
hands the resulting frozen dataclass to the Agent layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class AgentSessionContext:
    """Snapshot of the data the Agent is allowed to reason about."""

    run_base_dir: str
    current_run: Optional[str]
    selected_targets: Tuple[str, ...] = field(default_factory=tuple)
    visible_targets: Tuple[str, ...] = field(default_factory=tuple)
    view_mode: str = "main"
    status_filter: Optional[str] = None

    @property
    def has_selection(self) -> bool:
        return bool(self.selected_targets)

    @property
    def has_run(self) -> bool:
        return bool(self.current_run)


def _coerce_targets(values: Optional[Iterable[object]]) -> Tuple[str, ...]:
    if not values:
        return ()
    result = []
    seen = set()
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def snapshot_session_context(
    *,
    run_base_dir: str,
    current_run: Optional[str],
    selected_targets: Optional[Iterable[object]] = None,
    visible_targets: Optional[Iterable[object]] = None,
    view_mode: str = "main",
    status_filter: Optional[str] = None,
) -> AgentSessionContext:
    """Build an :class:`AgentSessionContext` from raw runtime inputs."""
    return AgentSessionContext(
        run_base_dir=str(run_base_dir or ""),
        current_run=current_run or None,
        selected_targets=_coerce_targets(selected_targets),
        visible_targets=_coerce_targets(visible_targets),
        view_mode=str(view_mode or "main"),
        status_filter=status_filter or None,
    )
