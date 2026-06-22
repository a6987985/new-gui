"""Post-action observations for the Executable Agent.

The Agent must be able to reason about what changed after an action runs.
Rather than poking around ``MainWindow`` directly, the controller asks an
``ObservationCollector`` to capture a tiny, JSON-serializable snapshot of run
state before and after every plan execution. The diff between the two
snapshots becomes the observation, which is persisted to the audit log and
shown in the dock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class RunStateObservation:
    """A coarse, JSON-friendly snapshot of run state."""

    current_run: Optional[str] = None
    status_counts: Mapping[str, int] = field(default_factory=dict)
    selected_targets: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "current_run": self.current_run,
            "status_counts": dict(self.status_counts),
            "selected_targets": list(self.selected_targets),
        }


@dataclass(frozen=True)
class ObservationDiff:
    """Difference between two :class:`RunStateObservation` instances."""

    run_changed: bool
    status_delta: Mapping[str, int]
    selection_added: Tuple[str, ...]
    selection_removed: Tuple[str, ...]

    def is_empty(self) -> bool:
        return (
            not self.run_changed
            and not self.status_delta
            and not self.selection_added
            and not self.selection_removed
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "run_changed": bool(self.run_changed),
            "status_delta": dict(self.status_delta),
            "selection_added": list(self.selection_added),
            "selection_removed": list(self.selection_removed),
        }


def diff_observations(
    before: RunStateObservation, after: RunStateObservation
) -> ObservationDiff:
    """Return the diff between two observations, stable for serialization.

    When the active run changes between snapshots we deliberately suppress the
    status delta: the two ``status_counts`` maps belong to different runs and
    subtracting them would produce a fake "change" signal that confuses the
    Agent loop and the audit summary.
    """
    run_changed = before.current_run != after.current_run

    delta: Dict[str, int] = {}
    cache_just_filled = (
        not before.status_counts and bool(after.status_counts)
    )
    if not run_changed and not cache_just_filled:
        keys = set(before.status_counts) | set(after.status_counts)
        for key in sorted(keys):
            change = int(after.status_counts.get(key, 0)) - int(
                before.status_counts.get(key, 0)
            )
            if change:
                delta[key] = change

    before_sel = set(before.selected_targets)
    after_sel = set(after.selected_targets)
    return ObservationDiff(
        run_changed=run_changed,
        status_delta=delta,
        selection_added=tuple(sorted(after_sel - before_sel)),
        selection_removed=tuple(sorted(before_sel - after_sel)),
    )


def _safe_status_counts(window: object) -> Dict[str, int]:
    """Read window status cache without raising on partial state."""
    cache = getattr(window, "_status_cache", None) or {}
    counts: Dict[str, int] = {}
    try:
        for target_name, status in cache.items():
            text = str(status or "").strip() or "unknown"
            counts[text] = counts.get(text, 0) + 1
    except Exception:
        return {}
    return counts


def _safe_selection(window: object) -> Tuple[str, ...]:
    method = getattr(window, "get_selected_targets", None)
    if not callable(method):
        return ()
    try:
        values = method() or []
    except Exception:
        return ()
    cleaned: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _safe_current_run(window: object) -> Optional[str]:
    combo = getattr(window, "combo", None)
    if combo is None:
        return None
    try:
        text = combo.currentText()
    except Exception:
        return None
    text = str(text or "").strip()
    if not text or text == "No runs found":
        return None
    return text


ObservationCollector = Callable[[object], RunStateObservation]


def default_collector(window: object) -> RunStateObservation:
    """Collect a coarse observation from the live ``MainWindow``."""
    return RunStateObservation(
        current_run=_safe_current_run(window),
        status_counts=_safe_status_counts(window),
        selected_targets=_safe_selection(window),
    )
