"""Selector that builds an :class:`AgentPlanner` from environment.

Environment variable ``NEW_GUI_AGENT_BACKEND`` chooses the strategy:

* ``rule``   -> :class:`RulePlanner` only (deterministic, offline)
* ``openai`` -> :class:`LLMPlanner` over the OpenAI Chat Completions schema
  (also matches Azure / self-hosted OpenAI-compatible gateways), falling back
  to :class:`RulePlanner` when no API key is configured or any call fails.
* ``claude`` -> :class:`ClaudeAgentPlanner` using the local ``claude`` CLI via
  claude-agent-sdk, falling back to :class:`RulePlanner` when the SDK/CLI is
  unavailable or any call fails.

The default backend is ``openai`` to preserve the previous behavior.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from new_gui.application.agent.agent_llm import LLMPlanner, LLMPlannerSettings
from new_gui.application.agent.agent_planner import AgentPlanner, RulePlanner
from new_gui.application.agent.agent_claude import (
    ClaudeAgentPlanner,
    ClaudePlannerSettings,
)


_LOGGER = logging.getLogger(__name__)

BACKEND_RULE = "rule"
BACKEND_OPENAI = "openai"
BACKEND_CLAUDE = "claude"
SUPPORTED_BACKENDS = (BACKEND_RULE, BACKEND_OPENAI, BACKEND_CLAUDE)


def resolve_backend(prefix: str = "NEW_GUI_AGENT") -> str:
    """Return the configured backend name, defaulting to ``openai``."""
    value = (os.environ.get(f"{prefix}_BACKEND") or "").strip().lower()
    if value in SUPPORTED_BACKENDS:
        return value
    if value:
        _LOGGER.warning("Unknown %s_BACKEND=%r; defaulting to openai", prefix, value)
    return BACKEND_OPENAI


def build_planner(
    *,
    backend: Optional[str] = None,
    fallback: Optional[AgentPlanner] = None,
    prefix: str = "NEW_GUI_AGENT",
) -> AgentPlanner:
    """Build a planner for the requested backend, with safe fallbacks."""
    rule_planner = fallback or RulePlanner()
    chosen = backend or resolve_backend(prefix)

    if chosen == BACKEND_RULE:
        return rule_planner

    if chosen == BACKEND_CLAUDE:
        settings = ClaudePlannerSettings.from_env(prefix=prefix)
        if not settings.is_enabled:
            settings = ClaudePlannerSettings(
                model=settings.model,
                max_turns=settings.max_turns,
                timeout_seconds=settings.timeout_seconds,
                enabled=True,
            )
        return ClaudeAgentPlanner(settings=settings, fallback=rule_planner)

    settings = LLMPlannerSettings.from_env(prefix=prefix)
    if settings.is_enabled:
        return LLMPlanner(settings=settings, fallback=rule_planner)
    return rule_planner
