"""Reader for the JSONL audit log produced by :class:`AgentAuditLog`.

The reader is intentionally permissive: it skips malformed lines instead of
raising, so a corrupted tail never breaks the dock or governance tooling.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class AuditRecord:
    """Single audit entry loaded back from disk."""

    timestamp: float
    prompt: str
    plan: Tuple[str, ...]
    results: Tuple[dict, ...]
    errors: Tuple[str, ...]
    observation: Optional[dict] = None


def _coerce_record(raw: Mapping[str, object]) -> Optional[AuditRecord]:
    if not isinstance(raw, Mapping):
        return None
    try:
        timestamp = float(raw.get("timestamp") or 0.0)
    except (TypeError, ValueError):
        return None
    prompt = str(raw.get("prompt") or "")
    plan = tuple(str(value) for value in (raw.get("plan") or []))
    results = tuple(
        dict(item) for item in (raw.get("results") or []) if isinstance(item, Mapping)
    )
    errors = tuple(str(value) for value in (raw.get("errors") or []))
    observation = raw.get("observation")
    if observation is not None and not isinstance(observation, Mapping):
        observation = None
    return AuditRecord(
        timestamp=timestamp,
        prompt=prompt,
        plan=plan,
        results=results,
        errors=errors,
        observation=dict(observation) if observation else None,
    )


def parse_audit_lines(lines: Iterable[str]) -> List[AuditRecord]:
    """Parse JSONL lines, ignoring malformed entries."""
    records: List[AuditRecord] = []
    for line in lines:
        text = (line or "").strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        coerced = _coerce_record(payload)
        if coerced is not None:
            records.append(coerced)
    return records


def load_audit_file(path: str) -> List[AuditRecord]:
    """Load every audit record from ``path``; return ``[]`` if missing."""
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return parse_audit_lines(handle.readlines())


def summarize_records(records: Iterable[AuditRecord]) -> dict:
    """Aggregate a sequence of audit records into governance-friendly counts."""
    records = list(records)
    total_prompts = len(records)
    total_actions = 0
    executed = 0
    rejected = 0
    failed_planner = 0
    actions_by_id: dict = {}
    for record in records:
        if not record.plan:
            failed_planner += 1
        for entry in record.results:
            total_actions += 1
            action_id = str(entry.get("action_id") or "")
            status = str(entry.get("status") or "")
            actions_by_id[action_id] = actions_by_id.get(action_id, 0) + 1
            if status == "executed":
                executed += 1
            elif status == "rejected":
                rejected += 1
    return {
        "total_prompts": total_prompts,
        "total_actions": total_actions,
        "executed": executed,
        "rejected": rejected,
        "planner_misses": failed_planner,
        "actions_by_id": actions_by_id,
    }
