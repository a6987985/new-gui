"""LLM-backed planner that asks a chat model for a structured plan.

The adapter follows the OpenAI Chat Completions JSON-mode protocol but talks
to any compatible endpoint, so it works with the official OpenAI API, Azure
OpenAI, and self-hosted gateways exposing the same schema. When the runtime
key is missing or the HTTP call fails, the adapter falls back to a supplied
``RulePlanner``, so the dock keeps working without network access.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Tuple

from new_gui.application.agent.action_catalog import catalog_as_dict
from new_gui.application.agent.agent_context import AgentSessionContext
from new_gui.application.agent.agent_planner import (
    AgentPlanStep,
    AgentPlanner,
    RulePlanner,
)


_LOGGER = logging.getLogger(__name__)

HttpFetcher = Callable[[str, dict, dict, float], str]


def _default_http_fetcher(url: str, headers: dict, body: dict, timeout: float) -> str:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


@dataclass(frozen=True)
class LLMPlannerSettings:
    """Configuration block for :class:`LLMPlanner`."""

    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls, prefix: str = "NEW_GUI_AGENT") -> "LLMPlannerSettings":
        return cls(
            api_base=os.environ.get(f"{prefix}_API_BASE", "https://api.openai.com/v1"),
            model=os.environ.get(f"{prefix}_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get(f"{prefix}_API_KEY")
            or os.environ.get("OPENAI_API_KEY"),
            timeout_seconds=float(os.environ.get(f"{prefix}_TIMEOUT", "20")),
        )

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)


_SYSTEM_PROMPT = (
    "You are the Executable Agent for the XMeta Console GUI. "
    "You may only call Registered GUI Actions from the catalog provided in "
    "the user message. Respond with a JSON object of the form "
    "{\"steps\": [{\"action_id\": \"...\", \"rationale\": \"...\", "
    "\"parameters\": {\"targets\": [\"...\"]}}]}. "
    "Omit 'parameters' when no targets are needed. Never invent action_ids. "
    "If no catalog entry fits, return {\"steps\": []}."
)


def _build_user_payload(prompt: str, context: AgentSessionContext) -> str:
    catalog = catalog_as_dict()
    payload = {
        "user_prompt": prompt,
        "session_context": {
            "current_run": context.current_run,
            "selected_targets": list(context.selected_targets),
            "visible_targets": list(context.visible_targets),
            "view_mode": context.view_mode,
        },
        "registered_actions": catalog,
    }
    return json.dumps(payload, ensure_ascii=False)


def _parse_llm_response(raw_text: str) -> List[AgentPlanStep]:
    try:
        envelope = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response was not valid JSON: {exc}") from exc

    choices = envelope.get("choices") or []
    if not choices:
        raise ValueError("LLM response had no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM message content was empty")

    try:
        body = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM content was not JSON: {exc}") from exc

    raw_steps = body.get("steps") or []
    if not isinstance(raw_steps, list):
        raise ValueError("'steps' must be a list")

    steps: List[AgentPlanStep] = []
    for raw in raw_steps:
        if not isinstance(raw, Mapping):
            continue
        action_id = str(raw.get("action_id") or "").strip()
        if not action_id:
            continue
        rationale = str(raw.get("rationale") or "")
        parameters_raw = raw.get("parameters") or {}
        if not isinstance(parameters_raw, Mapping):
            parameters_raw = {}
        steps.append(
            AgentPlanStep(
                action_id=action_id,
                rationale=rationale,
                parameters=dict(parameters_raw),
            )
        )
    return steps


class LLMPlanner:
    """Planner that delegates to a chat-completion compatible endpoint."""

    def __init__(
        self,
        *,
        settings: Optional[LLMPlannerSettings] = None,
        fallback: Optional[AgentPlanner] = None,
        http_fetcher: HttpFetcher = _default_http_fetcher,
    ) -> None:
        self._settings = settings or LLMPlannerSettings.from_env()
        self._fallback = fallback or RulePlanner()
        self._http_fetcher = http_fetcher

    def plan(
        self, prompt: str, context: AgentSessionContext
    ) -> Tuple[AgentPlanStep, ...]:
        if not self._settings.is_enabled:
            return self._fallback.plan(prompt, context)

        body = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_payload(prompt, context)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        url = self._settings.api_base.rstrip("/") + "/chat/completions"

        try:
            raw_text = self._http_fetcher(
                url, headers, body, self._settings.timeout_seconds
            )
            steps = _parse_llm_response(raw_text)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            _LOGGER.warning("LLM planner falling back due to error: %s", exc)
            return self._fallback.plan(prompt, context)

        if not steps:
            return self._fallback.plan(prompt, context)
        return tuple(steps)
