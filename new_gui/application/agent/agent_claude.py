"""Planner backed by claude-agent-sdk (Anthropic Claude via local CLI).

The adapter wraps ``claude_agent_sdk.query`` and converts every Registered GUI
Action into an SDK tool. Claude is steered to *plan only* (no actual side
effects) by giving each tool a no-op handler that records the requested
action_id, rationale, and parameters. The recorded tool_use blocks are then
mapped into :class:`AgentPlanStep` instances that the existing
:class:`AgentExecutor` runs through the Action Boundary as usual.

If the SDK is missing, the Claude CLI is not installed, or any error occurs
during the query, the planner transparently falls back to the supplied
``RulePlanner`` so the dock keeps working offline.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from new_gui.application.agent.action_catalog import (
    AgentActionEntry,
    build_action_catalog,
)
from new_gui.application.agent.agent_context import AgentSessionContext
from new_gui.application.agent.agent_planner import (
    AgentPlanStep,
    AgentPlanner,
    RulePlanner,
)


_LOGGER = logging.getLogger(__name__)


_CLAUDE_SYSTEM_PROMPT = (
    "You are the Executable Agent for the XMeta Console GUI. "
    "You may ONLY plan actions by calling the provided tools, one per "
    "Registered GUI Action. Never call any tool that is not in the provided "
    "set. For every tool call, supply a short `rationale` argument describing "
    "why the action is appropriate, and `targets` (a list of strings) only "
    "when the action operates on a selection. Do not call shell, file, or any "
    "other built-in tools. If no provided tool fits the user's request, reply "
    "with plain text explaining why and do not call any tool."
)


@dataclass(frozen=True)
class ClaudePlannerSettings:
    """Runtime configuration for :class:`ClaudeAgentPlanner`."""

    model: Optional[str] = None
    max_turns: int = 2
    timeout_seconds: float = 30.0
    enabled: bool = True

    @classmethod
    def from_env(cls, prefix: str = "NEW_GUI_AGENT") -> "ClaudePlannerSettings":
        backend = os.environ.get(f"{prefix}_BACKEND", "").lower()
        return cls(
            model=os.environ.get(f"{prefix}_CLAUDE_MODEL"),
            max_turns=int(os.environ.get(f"{prefix}_CLAUDE_MAX_TURNS", "2")),
            timeout_seconds=float(
                os.environ.get(f"{prefix}_CLAUDE_TIMEOUT", "30")
            ),
            enabled=(backend == "claude"),
        )

    @property
    def is_enabled(self) -> bool:
        return self.enabled


def _action_tool_name(action_id: str) -> str:
    """Map a Registered GUI Action id to an SDK tool name."""
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in action_id)
    return f"plan_{safe}"


def _build_tools_and_lookup(
    catalog: Tuple[AgentActionEntry, ...]
):
    """Return (mcp_server_config, tool_name -> action_id) for the catalog.

    Each tool handler is a no-op that simply echoes its input; the SDK still
    records the ``ToolUseBlock`` in the assistant stream, which is what we
    parse downstream. The handler exists only because the SDK requires one.
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool  # type: ignore

    tools = []
    lookup = {}
    for entry in catalog:
        tool_name = _action_tool_name(entry.action_id)
        lookup[tool_name] = entry.action_id

        description = (
            f"{entry.description} "
            f"[category={entry.category}, mutates_state={entry.mutates_state}, "
            f"requires_selection={entry.requires_selection}]"
        )

        schema: dict = {
            "type": "object",
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": "Short reason why this action fits the user request.",
                },
                "targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional target ids when the action operates on a selection.",
                },
            },
            "required": ["rationale"],
            "additionalProperties": False,
        }

        async def _noop_handler(args, _aid=entry.action_id):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"planned {_aid}",
                    }
                ]
            }

        decorated = tool(tool_name, description, schema)(_noop_handler)
        tools.append(decorated)

    server = create_sdk_mcp_server(name="new_gui_actions", tools=tools)
    return server, lookup


def _format_user_prompt(prompt: str, context: AgentSessionContext) -> str:
    """Wrap the user prompt with the current session context for Claude."""
    return (
        f"User request: {prompt}\n\n"
        f"Session context:\n"
        f"- current_run: {context.current_run!r}\n"
        f"- selected_targets: {list(context.selected_targets)!r}\n"
        f"- visible_targets: {list(context.visible_targets)!r}\n"
        f"- view_mode: {context.view_mode!r}\n\n"
        f"Plan by calling tools. Use no tool if nothing fits."
    )


async def _collect_tool_uses(
    prompt_text: str,
    options,
    timeout: float,
) -> List[dict]:
    """Run a single SDK query and collect tool_use blocks from Claude."""
    from claude_agent_sdk import (  # type: ignore
        query,
        AssistantMessage,
        ToolUseBlock,
    )

    collected: List[dict] = []

    async def _runner():
        async for message in query(prompt=prompt_text, options=options):
            if isinstance(message, AssistantMessage):
                for block in getattr(message, "content", []) or []:
                    if isinstance(block, ToolUseBlock):
                        collected.append(
                            {
                                "name": getattr(block, "name", ""),
                                "input": dict(getattr(block, "input", {}) or {}),
                            }
                        )

    await asyncio.wait_for(_runner(), timeout=timeout)
    return collected


class ClaudeAgentPlanner:
    """Planner that asks Claude (via claude-agent-sdk) for a tool-use plan."""

    def __init__(
        self,
        *,
        settings: Optional[ClaudePlannerSettings] = None,
        fallback: Optional[AgentPlanner] = None,
        catalog: Optional[Tuple[AgentActionEntry, ...]] = None,
    ) -> None:
        self._settings = settings or ClaudePlannerSettings.from_env()
        self._fallback = fallback or RulePlanner()
        self._catalog = tuple(catalog) if catalog is not None else build_action_catalog()
        self._known_ids = {entry.action_id for entry in self._catalog}

    def plan(
        self, prompt: str, context: AgentSessionContext
    ) -> Tuple[AgentPlanStep, ...]:
        if not self._settings.is_enabled:
            return self._fallback.plan(prompt, context)

        try:
            tool_uses = self._invoke_claude(prompt, context)
        except Exception as exc:  # SDK missing, CLI missing, network, etc.
            _LOGGER.warning("Claude planner falling back: %s", exc)
            return self._fallback.plan(prompt, context)

        steps = self._tool_uses_to_steps(tool_uses)
        if not steps:
            return self._fallback.plan(prompt, context)
        return tuple(steps)

    def _invoke_claude(
        self, prompt: str, context: AgentSessionContext
    ) -> List[dict]:
        from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

        server, lookup = _build_tools_and_lookup(self._catalog)
        self._tool_lookup = lookup

        allowed = [f"mcp__new_gui_actions__{name}" for name in lookup]

        options = ClaudeAgentOptions(
            system_prompt=_CLAUDE_SYSTEM_PROMPT,
            mcp_servers={"new_gui_actions": server},
            allowed_tools=allowed,
            disallowed_tools=[],
            max_turns=self._settings.max_turns,
            model=self._settings.model,
            permission_mode="bypassPermissions",
            include_partial_messages=False,
        )

        prompt_text = _format_user_prompt(prompt, context)
        return asyncio.run(
            _collect_tool_uses(
                prompt_text, options, self._settings.timeout_seconds
            )
        )

    def _tool_uses_to_steps(self, tool_uses: List[dict]) -> List[AgentPlanStep]:
        steps: List[AgentPlanStep] = []
        for use in tool_uses:
            tool_name = str(use.get("name") or "")
            short_name = tool_name.split("__")[-1]
            action_id = self._tool_lookup.get(short_name)
            if not action_id or action_id not in self._known_ids:
                continue
            args = use.get("input") or {}
            rationale = str(args.get("rationale") or "")
            params: dict = {}
            targets = args.get("targets")
            if isinstance(targets, list) and targets:
                params["targets"] = [str(t) for t in targets]
            steps.append(
                AgentPlanStep(
                    action_id=action_id,
                    rationale=rationale,
                    parameters=params,
                )
            )
        return steps
