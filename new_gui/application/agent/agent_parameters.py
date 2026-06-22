"""Second-version action boundary: typed parameters for Registered GUI Actions.

The first-version boundary restricted the Agent to "click the button as-is".
For state-mutating execute actions, operators want to ask the Agent to run a
specific subset of targets. This module introduces a small, declarative
schema, plus a validator that ensures requested targets are inside the
Agent's read-only ``AgentSessionContext`` (i.e. visible to the user).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from new_gui.application.agent.agent_context import AgentSessionContext
from new_gui.application.registries.action_registry import (
    UiActionDefinition,
    get_action_definition,
)


_PARAMETERIZABLE_TARGETS: Tuple[str, ...] = (
    "run",
    "stop",
    "skip",
    "unskip",
    "invalid",
)


def supports_targets_parameter(action_id: str) -> bool:
    """Return True when the action can be invoked against an explicit target list."""
    return action_id in _PARAMETERIZABLE_TARGETS


@dataclass(frozen=True)
class AgentActionParameters:
    """Validated parameter bundle for one Agent-initiated action."""

    targets: Tuple[str, ...] = ()
    raw: Mapping[str, object] = field(default_factory=dict)

    @property
    def has_targets(self) -> bool:
        return bool(self.targets)


class ActionParameterError(Exception):
    """Raised when parameters violate the second-version boundary."""


def _coerce_target_tuple(raw_targets: object) -> Tuple[str, ...]:
    if raw_targets is None:
        return ()
    if isinstance(raw_targets, (str, bytes)):
        raise ActionParameterError("'targets' must be a list, not a single string")
    result = []
    seen = set()
    try:
        iterator = iter(raw_targets)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ActionParameterError("'targets' must be iterable") from exc
    for value in iterator:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def validate_action_parameters(
    action_id: str,
    raw_parameters: Optional[Mapping[str, object]],
    context: AgentSessionContext,
) -> AgentActionParameters:
    """Validate ``raw_parameters`` against the boundary for ``action_id``.

    Rules:
    - Unknown actions are rejected (boundary enforcement).
    - Unknown parameter keys are rejected, so we never silently grow the API.
    - For actions that accept ``targets``, every requested target must already
      be visible to the user (present in ``context.visible_targets``).
    - For actions that do not accept ``targets``, supplying any is an error.
    """
    raw = dict(raw_parameters or {})

    try:
        get_action_definition(action_id)
    except KeyError as exc:
        raise ActionParameterError(
            f"unknown action_id {action_id!r}"
        ) from exc

    unknown_keys = sorted(set(raw.keys()) - {"targets"})
    if unknown_keys:
        raise ActionParameterError(
            f"unsupported parameter keys for {action_id!r}: {unknown_keys}"
        )

    targets = _coerce_target_tuple(raw.get("targets"))
    if targets and not supports_targets_parameter(action_id):
        raise ActionParameterError(
            f"action {action_id!r} does not accept a 'targets' parameter"
        )

    if targets:
        visible = set(context.visible_targets)
        if visible:
            missing = [name for name in targets if name not in visible]
            if missing:
                raise ActionParameterError(
                    f"targets outside visible scope for {action_id!r}: {missing}"
                )

    return AgentActionParameters(targets=targets, raw=raw)
