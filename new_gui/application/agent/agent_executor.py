"""Single execution entrypoint for the Executable Agent.

The First-Version Action Boundary is enforced here: the Agent can only invoke
actions registered in :mod:`new_gui.application.registries.action_registry`,
and every State-Changing Action must pass through a ``ConfirmationGate``
before its UI trigger is fired.

The Second-Version Boundary adds an optional, typed ``parameters`` channel
validated by :mod:`new_gui.application.agent.agent_parameters`. When the
parameters carry a ``targets`` list, the executor projects them onto the
window's selection just before invoking the existing ``trigger`` callable,
so the Agent never grows a parallel execution path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Tuple

from new_gui.application.agent.agent_context import AgentSessionContext
from new_gui.application.agent.agent_parameters import (
    ActionParameterError,
    AgentActionParameters,
    validate_action_parameters,
)
from new_gui.application.registries.action_registry import (
    UiActionDefinition,
    get_action_definition,
)


_LOGGER = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Raised when the Agent attempts to execute an invalid request."""


class ConfirmationDecision(Enum):
    """Outcome reported by a ``ConfirmationGate``."""

    APPROVED = "approved"
    REJECTED = "rejected"


ConfirmationGate = Callable[[UiActionDefinition, AgentSessionContext], ConfirmationDecision]


def auto_approve_gate(
    _definition: UiActionDefinition, _context: AgentSessionContext
) -> ConfirmationDecision:
    """Default gate used in headless/test contexts that always approves."""
    return ConfirmationDecision.APPROVED


def auto_reject_gate(
    _definition: UiActionDefinition, _context: AgentSessionContext
) -> ConfirmationDecision:
    """Convenience gate that always rejects, for safety-focused dry runs."""
    return ConfirmationDecision.REJECTED


SelectionApplier = Callable[[object, Tuple[str, ...]], None]


def default_selection_applier(window: object, targets: Tuple[str, ...]) -> None:
    """Project ``targets`` onto the live window selection when possible.

    The applier prefers the public ``_select_targets_in_tree`` hook so the
    executor stays inside the existing UI flow.
    """
    method = getattr(window, "_select_targets_in_tree", None)
    if not callable(method):
        return
    method(list(targets))


@dataclass(frozen=True)
class AgentExecutionResult:
    """Structured outcome of one Agent execution attempt."""

    action_id: str
    status: str
    detail: str = ""
    targets: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "executed"

    def as_audit_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "status": self.status,
            "detail": self.detail,
            "targets": list(self.targets),
        }


class AgentExecutor:
    """Mediator between the Agent layer and Registered GUI Actions."""

    def __init__(
        self,
        window: object,
        *,
        confirmation_gate: Optional[ConfirmationGate] = None,
        selection_applier: Optional[SelectionApplier] = None,
    ) -> None:
        self._window = window
        self._confirmation_gate = confirmation_gate or auto_approve_gate
        self._selection_applier = selection_applier or default_selection_applier

    def execute(
        self,
        action_id: str,
        context: AgentSessionContext,
        *,
        parameters: Optional[Mapping[str, object]] = None,
    ) -> AgentExecutionResult:
        """Execute one Registered GUI Action by id within the boundary."""
        try:
            definition = get_action_definition(action_id)
        except KeyError as exc:
            raise AgentExecutionError(
                f"unknown action_id outside the First-Version Action Boundary: {action_id!r}"
            ) from exc

        try:
            validated = validate_action_parameters(action_id, parameters, context)
        except ActionParameterError as exc:
            return AgentExecutionResult(
                action_id=action_id,
                status="rejected",
                detail=str(exc),
            )

        if validated.has_targets and context.view_mode != "main":
            # The tree-based selection projection has no effect outside the main
            # view (graph mode reads selection from a separate panel). Refusing
            # here keeps the Agent honest instead of silently executing against
            # the wrong selection source.
            return AgentExecutionResult(
                action_id=action_id,
                status="rejected",
                detail=(
                    f"action {action_id!r} with explicit targets requires the main "
                    f"view, but view_mode is {context.view_mode!r}"
                ),
            )

        effective_selection = (
            validated.targets if validated.has_targets else context.selected_targets
        )

        if definition.requires_selection and not effective_selection:
            return AgentExecutionResult(
                action_id=action_id,
                status="rejected",
                detail="action requires at least one target",
            )

        if definition.mutates_state:
            if not definition.requires_confirmation:
                raise AgentExecutionError(
                    f"invariant violated: state-changing action {action_id!r} "
                    "must require user confirmation"
                )
            decision = self._confirmation_gate(definition, context)
            if decision is not ConfirmationDecision.APPROVED:
                return AgentExecutionResult(
                    action_id=action_id,
                    status="rejected",
                    detail="user confirmation denied",
                    targets=tuple(effective_selection),
                )

        original_selection: Tuple[str, ...] = context.selected_targets
        if validated.has_targets:
            self._selection_applier(self._window, validated.targets)

        _LOGGER.info(
            "agent.execute action_id=%s mutates_state=%s run=%s selection=%s",
            action_id,
            definition.mutates_state,
            context.current_run,
            len(effective_selection),
        )
        try:
            definition.trigger(self._window)
        finally:
            # Restore the user's original selection after a parameterized invocation
            # so the Agent never silently overwrites what the operator had selected.
            if validated.has_targets and original_selection != validated.targets:
                try:
                    self._selection_applier(self._window, original_selection)
                except Exception:
                    # Selection restoration is best-effort; never surface a
                    # widget error past the executor boundary.
                    _LOGGER.warning(
                        "agent.execute selection restore failed for action_id=%s",
                        action_id,
                    )
        return AgentExecutionResult(
            action_id=action_id,
            status="executed",
            targets=tuple(effective_selection),
        )
