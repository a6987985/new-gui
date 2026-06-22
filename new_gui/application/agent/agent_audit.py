"""Append-only audit log for Executable Agent invocations.

Every prompt -> plan -> execute cycle is written as one JSON line, so a
reviewer can later replay the Agent's behavior offline. The default
implementation writes to ``<base_dir>/agent_audit.log`` but accepts any
file-like sink for tests and embedding scenarios.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, TextIO


@dataclass(frozen=True)
class AgentAuditEntry:
    """One audited Agent interaction."""

    timestamp: float
    prompt: str
    plan: List[str]
    rationales: List[str]
    results: List[dict]
    errors: List[str]
    observation: Optional[dict] = None

    def to_json(self) -> str:
        payload = {
            "timestamp": self.timestamp,
            "prompt": self.prompt,
            "plan": list(self.plan),
            "rationales": list(self.rationales),
            "results": list(self.results),
            "errors": list(self.errors),
            "observation": self.observation,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class AgentAuditLog:
    """Threadsafe append-only audit sink."""

    def __init__(
        self,
        *,
        sink: Optional[TextIO] = None,
        path: Optional[str] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if sink is None and path is None:
            raise ValueError("AgentAuditLog needs either a sink or a path")
        self._sink = sink
        self._path = path
        self._clock = clock
        self._lock = threading.Lock()
        self._buffer: List[AgentAuditEntry] = []

    @property
    def entries(self) -> tuple:
        """Return entries recorded in-memory (best-effort, primarily for tests)."""
        with self._lock:
            return tuple(self._buffer)

    def record(
        self,
        *,
        prompt: str,
        plan: Iterable[str],
        rationales: Iterable[str],
        results: Iterable[dict],
        errors: Iterable[str],
        observation: Optional[dict] = None,
    ) -> AgentAuditEntry:
        entry = AgentAuditEntry(
            timestamp=self._clock(),
            prompt=prompt,
            plan=list(plan),
            rationales=list(rationales),
            results=[dict(item) for item in results],
            errors=list(errors),
            observation=dict(observation) if observation else None,
        )
        line = entry.to_json() + "\n"
        with self._lock:
            self._buffer.append(entry)
            if self._sink is not None:
                self._sink.write(line)
                self._sink.flush()
            elif self._path:
                os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as handle:
                    handle.write(line)
        return entry


def default_audit_log_path() -> str:
    """Return the conventional audit log location relative to CWD."""
    return os.path.join(".agent", "agent_audit.log")
