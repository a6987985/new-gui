"""Multi-step Agent loop: re-planning between actions with feedback.

The base ``AgentController.submit_prompt`` runs a planner once and executes
every returned step. For interactive multi-turn behavior (the planner wants
to react to what happened after step N before deciding step N+1) the
:class:`MultiStepAgentLoop` wraps an :class:`AgentController` and feeds each
fresh observation back into the planner via a structured continuation prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Mapping, Optional, Tuple

from new_gui.application.agent.agent_planner import AgentPlanner, AgentPlanStep
from new_gui.application.agent.agent_observation import RunStateObservation
from new_gui.application.agent.agent_context import AgentSessionContext


CONTINUATION_PROMPT_TEMPLATE = (
    "{original_prompt}\n\n"
    "[loop iteration {iteration}] "
    "Last action returned observation diff: {diff_json}. "
    "Plan the next action, or return no steps to finish."
)


@dataclass(frozen=True)
class MultiStepTurnRecord:
    """One iteration inside a :class:`MultiStepAgentLoop` run."""

    iteration: int
    prompt: str
    steps: Tuple[AgentPlanStep, ...]
    results: Tuple[object, ...]
    errors: Tuple[str, ...]
    observation_before: Optional[RunStateObservation]
    observation_after: Optional[RunStateObservation]


@dataclass(frozen=True)
class MultiStepRunRecord:
    """The full multi-step run produced by :class:`MultiStepAgentLoop`."""

    original_prompt: str
    turns: Tuple[MultiStepTurnRecord, ...]
    stop_reason: str

    @property
    def total_executed(self) -> int:
        return sum(len(turn.results) for turn in self.turns)


class MultiStepAgentLoop:
    """Iterative driver that re-plans after every action."""

    def __init__(self, controller, *, max_iterations: int = 4) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        self._controller = controller
        self._max_iterations = max_iterations

    def run(self, prompt: str) -> MultiStepRunRecord:
        turns: List[MultiStepTurnRecord] = []
        active_prompt = prompt
        stop_reason = "max_iterations"
        last_signature: Optional[tuple] = None

        for iteration in range(1, self._max_iterations + 1):
            record = self._controller.submit_prompt(active_prompt)
            turns.append(
                MultiStepTurnRecord(
                    iteration=iteration,
                    prompt=active_prompt,
                    steps=record.steps,
                    results=record.results,
                    errors=record.errors,
                    observation_before=record.observation_before,
                    observation_after=record.observation_after,
                )
            )

            if not record.steps:
                stop_reason = "planner_finished"
                break

            # Detect a planner stuck in a loop: if the new plan matches the
            # previous one verbatim (same action ids + same parameters) we have
            # converged regardless of any observation noise.
            def _freeze(value):
                if isinstance(value, list):
                    return tuple(value)
                if isinstance(value, dict):
                    return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
                return value

            signature = tuple(
                (
                    step.action_id,
                    tuple(
                        sorted(
                            (key, _freeze(val))
                            for key, val in (step.parameters or {}).items()
                        )
                    ),
                )
                for step in record.steps
            )
            if last_signature is not None and signature == last_signature:
                stop_reason = "plan_repeated"
                break
            last_signature = signature

            if record.observation_diff is None or record.observation_diff.is_empty():
                stop_reason = "no_state_change"
                break

            diff_payload = record.observation_diff.to_dict()
            active_prompt = CONTINUATION_PROMPT_TEMPLATE.format(
                original_prompt=prompt,
                iteration=iteration + 1,
                diff_json=json.dumps(diff_payload, sort_keys=True),
            )
        else:
            stop_reason = "max_iterations"

        return MultiStepRunRecord(
            original_prompt=prompt,
            turns=tuple(turns),
            stop_reason=stop_reason,
        )
