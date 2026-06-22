"""Tests for ClaudeAgentPlanner + backend selector."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from new_gui.application.agent import (
    BACKEND_CLAUDE,
    BACKEND_OPENAI,
    BACKEND_RULE,
    ClaudeAgentPlanner,
    ClaudePlannerSettings,
    LLMPlanner,
    RulePlanner,
    build_planner,
    resolve_backend,
)
from new_gui.application.agent.agent_context import AgentSessionContext
from new_gui.application.agent.agent_planner import AgentPlanStep


def _ctx() -> AgentSessionContext:
    return AgentSessionContext(
        run_base_dir="/tmp/runs",
        current_run="r1",
        selected_targets=("t1",),
        visible_targets=("t1", "t2"),
        view_mode="main",
    )


class ResolveBackendTests(unittest.TestCase):
    def test_default_is_openai(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEW_GUI_AGENT_BACKEND", None)
            self.assertEqual(resolve_backend(), BACKEND_OPENAI)

    def test_explicit_claude(self):
        with mock.patch.dict(os.environ, {"NEW_GUI_AGENT_BACKEND": "claude"}):
            self.assertEqual(resolve_backend(), BACKEND_CLAUDE)

    def test_explicit_rule(self):
        with mock.patch.dict(os.environ, {"NEW_GUI_AGENT_BACKEND": "RULE"}):
            self.assertEqual(resolve_backend(), BACKEND_RULE)

    def test_unknown_backend_falls_back(self):
        with mock.patch.dict(os.environ, {"NEW_GUI_AGENT_BACKEND": "bogus"}):
            self.assertEqual(resolve_backend(), BACKEND_OPENAI)


class BuildPlannerTests(unittest.TestCase):
    def test_rule_backend(self):
        planner = build_planner(backend=BACKEND_RULE)
        self.assertIsInstance(planner, RulePlanner)

    def test_claude_backend(self):
        planner = build_planner(backend=BACKEND_CLAUDE)
        self.assertIsInstance(planner, ClaudeAgentPlanner)

    def test_openai_without_key_falls_back_to_rule(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ("NEW_GUI_AGENT_API_KEY", "OPENAI_API_KEY"):
                os.environ.pop(key, None)
            planner = build_planner(backend=BACKEND_OPENAI)
            self.assertIsInstance(planner, RulePlanner)

    def test_openai_with_key_returns_llm(self):
        with mock.patch.dict(os.environ, {"NEW_GUI_AGENT_API_KEY": "test"}):
            planner = build_planner(backend=BACKEND_OPENAI)
            self.assertIsInstance(planner, LLMPlanner)


class ClaudePlannerFallbackTests(unittest.TestCase):
    def test_disabled_falls_back_to_rule(self):
        settings = ClaudePlannerSettings(enabled=False)
        rule = RulePlanner()
        planner = ClaudeAgentPlanner(settings=settings, fallback=rule)
        steps = planner.plan("run all", _ctx())
        rule_steps = rule.plan("run all", _ctx())
        self.assertEqual(steps, rule_steps)

    def test_sdk_error_falls_back_to_rule(self):
        settings = ClaudePlannerSettings(enabled=True)
        rule = RulePlanner()
        planner = ClaudeAgentPlanner(settings=settings, fallback=rule)
        with mock.patch.object(
            planner,
            "_invoke_claude",
            side_effect=RuntimeError("simulated SDK failure"),
        ):
            steps = planner.plan("run all", _ctx())
        rule_steps = rule.plan("run all", _ctx())
        self.assertEqual(steps, rule_steps)

    def test_tool_uses_to_steps_maps_known_ids(self):
        settings = ClaudePlannerSettings(enabled=True)
        planner = ClaudeAgentPlanner(settings=settings)
        # Build a tool_lookup with at least one real action_id
        real_id = next(iter(planner._known_ids))
        planner._tool_lookup = {
            f"plan_{real_id}": real_id,
            "plan_bogus": "bogus_action_id",
        }
        tool_uses = [
            {
                "name": f"mcp__new_gui_actions__plan_{real_id}",
                "input": {"rationale": "fits the request", "targets": ["t1"]},
            },
            {
                "name": "mcp__new_gui_actions__plan_bogus",
                "input": {"rationale": "should be filtered"},
            },
        ]
        steps = planner._tool_uses_to_steps(tool_uses)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].action_id, real_id)
        self.assertEqual(steps[0].rationale, "fits the request")
        self.assertEqual(steps[0].parameters.get("targets"), ["t1"])

    def test_empty_tool_uses_falls_back(self):
        settings = ClaudePlannerSettings(enabled=True)
        rule = RulePlanner()
        planner = ClaudeAgentPlanner(settings=settings, fallback=rule)
        with mock.patch.object(planner, "_invoke_claude", return_value=[]):
            steps = planner.plan("run all", _ctx())
        rule_steps = rule.plan("run all", _ctx())
        self.assertEqual(steps, rule_steps)


if __name__ == "__main__":
    unittest.main()
