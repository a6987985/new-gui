"""Planners that turn user intent into one or more Registered GUI Action ids.

The :class:`RulePlanner` is a deterministic, dependency-free placeholder that
covers the dogfooding loop without needing an LLM. Production planners (LLM
backed, retrieval backed, etc.) implement the same :class:`AgentPlanner`
protocol and stay swappable behind the :class:`AgentController`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional, Protocol, Tuple

from new_gui.application.agent.action_catalog import (
    AgentActionEntry,
    build_action_catalog,
)
from new_gui.application.agent.agent_context import AgentSessionContext


@dataclass(frozen=True)
class AgentPlanStep:
    """A single planned invocation produced by an :class:`AgentPlanner`."""

    action_id: str
    rationale: str = ""
    parameters: Mapping[str, object] = field(default_factory=dict)


class AgentPlanner(Protocol):
    """Plan strategies share this interface and stay swappable at runtime."""

    def plan(
        self, prompt: str, context: AgentSessionContext
    ) -> Tuple[AgentPlanStep, ...]:
        ...


_KEYWORD_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("run_all", ("run all", "run everything", "全部运行", "全部跑")),
    ("stop", ("stop", "abort", "kill", "停止", "中止")),
    ("skip", ("skip",)),
    ("unskip", ("unskip", "resume",)),
    ("invalid", ("invalid", "invalidate",)),
    ("run", ("run", "execute", "go", "跑", "执行")),
    ("term", ("terminal", "shell", "open term", "终端")),
    ("csh", ("csh", "shell file",)),
    ("log", ("log", "logs",)),
    ("cmd", ("cmd", "command file",)),
    ("trace_up", ("trace up", "upstream", "上游")),
    ("trace_down", ("trace down", "downstream", "下游")),
)


def _normalize(prompt: str) -> str:
    return (prompt or "").strip().lower()


def _resolve_by_keywords(prompt_lc: str) -> Optional[str]:
    """Return the action whose longest matching keyword wins."""
    best_action: Optional[str] = None
    best_length = 0
    for action_id, keywords in _KEYWORD_RULES:
        for keyword in keywords:
            if keyword in prompt_lc and len(keyword) > best_length:
                best_action = action_id
                best_length = len(keyword)
    return best_action


class RulePlanner:
    """Deterministic planner used as the offline default."""

    def __init__(
        self, catalog: Optional[Iterable[AgentActionEntry]] = None
    ) -> None:
        self._catalog: Tuple[AgentActionEntry, ...] = tuple(
            catalog if catalog is not None else build_action_catalog()
        )
        self._ids = {entry.action_id for entry in self._catalog}

    def plan(
        self, prompt: str, context: AgentSessionContext
    ) -> Tuple[AgentPlanStep, ...]:
        prompt_lc = _normalize(prompt)
        if not prompt_lc:
            return ()

        action_id = self._match_explicit_id(prompt_lc) or _resolve_by_keywords(prompt_lc)
        if action_id is None or action_id not in self._ids:
            return ()

        targets = self._extract_target_tokens(prompt, context)
        parameters: Mapping[str, object] = {"targets": list(targets)} if targets else {}
        return (
            AgentPlanStep(
                action_id=action_id,
                rationale=(
                    f"matched rule for prompt {prompt!r}"
                    + (f" with targets {list(targets)}" if targets else "")
                ),
                parameters=parameters,
            ),
        )

    def _extract_target_tokens(
        self, prompt: str, context: AgentSessionContext
    ) -> Tuple[str, ...]:
        """Pick visible target names that appear in the prompt, case-insensitively.

        Matching against the catalog/keyword set is already case-insensitive, so
        applying the same rule here keeps the user experience consistent. The
        returned names preserve the canonical casing taken from
        ``visible_targets``.
        """
        if not context.visible_targets:
            return ()
        raw_tokens = {
            token.strip()
            for token in prompt.replace(",", " ").split()
            if token.strip()
        }
        prompt_tokens_lc = {token.lower() for token in raw_tokens}
        matched: List[str] = []
        for target in context.visible_targets:
            if target.lower() in prompt_tokens_lc and target not in matched:
                matched.append(target)
        return tuple(matched)

    def _match_explicit_id(self, prompt_lc: str) -> Optional[str]:
        """Match only compound ids (e.g. ``trace_up``) to avoid shadowing keywords."""
        tokens = {token for token in prompt_lc.replace(",", " ").split() if token}
        for entry in self._catalog:
            if "_" not in entry.action_id:
                continue
            if entry.action_id in tokens:
                return entry.action_id
        return None
