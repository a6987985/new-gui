"""Presenter that wires the Executable Agent to a live MainWindow.

Responsibilities:

* Build an :class:`AgentSessionContext` snapshot from the current window state.
* Plan one or more :class:`AgentPlanStep` invocations from a user prompt.
* Run each plan step through :class:`AgentExecutor`, which enforces the
  First-Version and Second-Version Action Boundaries.
* Persist every interaction to an :class:`AgentAuditLog` so reviewers can
  audit Agent behavior offline.
* Provide a Qt-aware :func:`qt_confirmation_gate` so State-Changing Actions
  surface as a real ``QMessageBox`` prompt to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from new_gui.application.agent import (
    AgentExecutionError,
    AgentExecutionResult,
    AgentExecutor,
    AgentSessionContext,
    ConfirmationDecision,
    ConfirmationGate,
)
from new_gui.application.agent.agent_audit import AgentAuditLog
from new_gui.application.agent.agent_context_snapshot import snapshot_from_window
from new_gui.application.agent.agent_observation import (
    ObservationCollector,
    ObservationDiff,
    RunStateObservation,
    default_collector,
    diff_observations,
)
from new_gui.application.agent.agent_planner import (
    AgentPlanStep,
    AgentPlanner,
    RulePlanner,
)
from new_gui.application.registries.action_registry import (
    UiActionDefinition,
    get_action_definition,
)


@dataclass(frozen=True)
class AgentInteractionRecord:
    """Structured outcome of one prompt -> plan -> execute cycle."""

    prompt: str
    steps: Tuple[AgentPlanStep, ...]
    results: Tuple[AgentExecutionResult, ...]
    errors: Tuple[str, ...] = ()
    observation_before: Optional[RunStateObservation] = None
    observation_after: Optional[RunStateObservation] = None
    observation_diff: Optional[ObservationDiff] = None

    @property
    def ok(self) -> bool:
        return bool(self.results) and all(result.ok for result in self.results)


def qt_confirmation_gate(window: object) -> ConfirmationGate:
    """Build a confirmation gate that pops a ``QMessageBox`` on the window."""

    def _gate(
        definition: UiActionDefinition, context: AgentSessionContext
    ) -> ConfirmationDecision:
        try:
            from PyQt5.QtWidgets import QMessageBox
        except Exception:
            return ConfirmationDecision.APPROVED

        targets_preview = ", ".join(context.selected_targets[:5]) or "(none)"
        body = (
            f"Action: {definition.button_label} ({definition.action_id})\n"
            f"Run: {context.current_run or '(none)'}\n"
            f"Selected: {targets_preview}\n\n"
            f"{definition.agent_description or definition.tooltip}\n\n"
            "Proceed?"
        )
        reply = QMessageBox.question(
            window if hasattr(window, "isVisible") else None,
            "Confirm Agent Action",
            body,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            return ConfirmationDecision.APPROVED
        return ConfirmationDecision.REJECTED

    return _gate


class AgentController:
    """Bridge between MainWindow events and the Agent execution boundary."""

    def __init__(
        self,
        window: object,
        *,
        planner: Optional[AgentPlanner] = None,
        confirmation_gate: Optional[ConfirmationGate] = None,
        audit_log: Optional[AgentAuditLog] = None,
        observation_collector: Optional[ObservationCollector] = None,
    ) -> None:
        self._window = window
        self._planner: AgentPlanner = planner or RulePlanner()
        self._executor = AgentExecutor(
            window=window,
            confirmation_gate=confirmation_gate or qt_confirmation_gate(window),
        )
        self._history: List[AgentInteractionRecord] = []
        self._audit_log = audit_log
        self._observation_collector: ObservationCollector = (
            observation_collector or default_collector
        )

    @property
    def history(self) -> Tuple[AgentInteractionRecord, ...]:
        return tuple(self._history)

    @property
    def audit_log(self) -> Optional[AgentAuditLog]:
        return self._audit_log

    def set_planner(self, planner: AgentPlanner) -> None:
        """Swap planner strategy (rule -> LLM) without touching the executor."""
        self._planner = planner

    def set_audit_log(self, audit_log: Optional[AgentAuditLog]) -> None:
        """Install or detach the audit sink at runtime."""
        self._audit_log = audit_log

    def snapshot(self) -> AgentSessionContext:
        return snapshot_from_window(self._window)

    def _collect_observation(self) -> Optional[RunStateObservation]:
        try:
            return self._observation_collector(self._window)
        except Exception:
            return None

    def submit_prompt(self, prompt: str) -> AgentInteractionRecord:
        """Run one prompt through plan -> execute -> observe -> audit."""
        context = self.snapshot()
        before = self._collect_observation()
        steps = self._planner.plan(prompt, context)
        results: List[AgentExecutionResult] = []
        errors: List[str] = []

        if not steps:
            after = self._collect_observation()
            diff = (
                diff_observations(before, after)
                if before is not None and after is not None
                else None
            )
            record = AgentInteractionRecord(
                prompt=prompt,
                steps=(),
                results=(),
                errors=("planner returned no matching action",),
                observation_before=before,
                observation_after=after,
                observation_diff=diff,
            )
            self._history.append(record)
            self._write_audit(record)
            return record

        for step in steps:
            try:
                get_action_definition(step.action_id)
            except KeyError:
                errors.append(
                    f"planner suggested {step.action_id!r} outside the boundary"
                )
                continue
            try:
                result = self._executor.execute(
                    step.action_id,
                    context,
                    parameters=dict(step.parameters or {}),
                )
            except AgentExecutionError as exc:
                errors.append(str(exc))
                continue
            results.append(result)

        after = self._collect_observation()
        diff = (
            diff_observations(before, after)
            if before is not None and after is not None
            else None
        )

        record = AgentInteractionRecord(
            prompt=prompt,
            steps=steps,
            results=tuple(results),
            errors=tuple(errors),
            observation_before=before,
            observation_after=after,
            observation_diff=diff,
        )
        self._history.append(record)
        self._write_audit(record)
        return record

    def _write_audit(self, record: AgentInteractionRecord) -> None:
        if self._audit_log is None:
            return
        observation_payload = None
        if record.observation_before or record.observation_after:
            observation_payload = {
                "before": record.observation_before.to_dict()
                if record.observation_before
                else None,
                "after": record.observation_after.to_dict()
                if record.observation_after
                else None,
                "diff": record.observation_diff.to_dict()
                if record.observation_diff
                else None,
            }
        self._audit_log.record(
            prompt=record.prompt,
            plan=[step.action_id for step in record.steps],
            rationales=[step.rationale for step in record.steps],
            results=[result.as_audit_dict() for result in record.results],
            errors=list(record.errors),
            observation=observation_payload,
        )
