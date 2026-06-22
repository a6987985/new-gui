"""Projection of the action registry into an Agent-facing catalog.

The catalog is what an Executable Agent (or any LLM-backed planner) is allowed
to see. It exposes the semantic metadata of every Registered GUI Action but
intentionally hides the underlying ``trigger`` callable, so the only way to
invoke an action remains :class:`AgentExecutor`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from new_gui.application.registries.action_registry import (
    UiActionDefinition,
    get_all_action_definitions,
)


@dataclass(frozen=True)
class AgentActionEntry:
    """Agent-facing description of a single Registered GUI Action."""

    action_id: str
    category: str
    button_label: str
    description: str
    mutates_state: bool
    requires_confirmation: bool
    requires_selection: bool

    @classmethod
    def from_definition(cls, definition: UiActionDefinition) -> "AgentActionEntry":
        description = definition.agent_description or definition.tooltip
        return cls(
            action_id=definition.action_id,
            category=str(definition.category),
            button_label=definition.button_label,
            description=description,
            mutates_state=bool(definition.mutates_state),
            requires_confirmation=bool(definition.requires_confirmation),
            requires_selection=bool(definition.requires_selection),
        )


def build_action_catalog() -> Tuple[AgentActionEntry, ...]:
    """Return the immutable catalog of Agent-visible actions."""
    return tuple(
        AgentActionEntry.from_definition(definition)
        for definition in get_all_action_definitions()
    )


def catalog_as_dict() -> List[Dict[str, object]]:
    """Return the catalog as a JSON-serializable list (one dict per action)."""
    return [asdict(entry) for entry in build_action_catalog()]
