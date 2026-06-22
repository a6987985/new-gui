"""Tests for the Second-Version Action Boundary, audit log, and LLM planner."""

import io
import json
import unittest
from typing import List, Tuple
from unittest.mock import MagicMock

from new_gui.application.agent import (
    ActionParameterError,
    AgentAuditLog,
    AgentExecutor,
    AgentSessionContext,
    LLMPlanner,
    LLMPlannerSettings,
    RulePlanner,
    snapshot_session_context,
    supports_targets_parameter,
    validate_action_parameters,
)
from new_gui.application.agent.agent_executor import (
    auto_approve_gate,
    auto_reject_gate,
)
from new_gui.application.agent.agent_planner import AgentPlanStep
from new_gui.presentation.presenters.agent_controller import AgentController


def _context(visible=("targetA", "targetB", "targetC"), selected=()):
    return snapshot_session_context(
        run_base_dir="/runs",
        current_run="run-001",
        selected_targets=selected,
        visible_targets=visible,
    )


class ActionParameterValidationTests(unittest.TestCase):
    def test_supports_targets_parameter_lists_expected_actions(self) -> None:
        for action_id in ("run", "stop", "skip", "unskip", "invalid"):
            self.assertTrue(supports_targets_parameter(action_id))
        for action_id in ("run_all", "log", "csh", "cmd", "term", "trace_up", "trace_down"):
            self.assertFalse(supports_targets_parameter(action_id))

    def test_unknown_action_id_rejected(self) -> None:
        with self.assertRaises(ActionParameterError):
            validate_action_parameters("nope", None, _context())

    def test_unknown_parameter_key_rejected(self) -> None:
        with self.assertRaises(ActionParameterError):
            validate_action_parameters("run", {"shell": "bash"}, _context())

    def test_targets_must_be_visible(self) -> None:
        with self.assertRaises(ActionParameterError):
            validate_action_parameters(
                "run", {"targets": ["ghost"]}, _context(visible=("targetA",))
            )

    def test_targets_passing_validation(self) -> None:
        result = validate_action_parameters(
            "run", {"targets": ["targetA", "targetB"]}, _context()
        )
        self.assertEqual(("targetA", "targetB"), result.targets)

    def test_run_all_does_not_accept_targets(self) -> None:
        with self.assertRaises(ActionParameterError):
            validate_action_parameters("run_all", {"targets": ["targetA"]}, _context())

    def test_string_targets_rejected_as_unsafe(self) -> None:
        with self.assertRaises(ActionParameterError):
            validate_action_parameters("run", {"targets": "targetA"}, _context())


class ParameterizedExecutorTests(unittest.TestCase):
    def _window(self):
        window = MagicMock()
        window.start = MagicMock()
        window._select_targets_in_tree = MagicMock()
        window.handle_log = MagicMock()
        return window

    def test_executor_applies_targets_to_selection_before_trigger(self) -> None:
        window = self._window()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        context = _context()
        result = executor.execute(
            "run", context, parameters={"targets": ["targetA", "targetC"]}
        )
        self.assertTrue(result.ok)
        self.assertEqual(("targetA", "targetC"), result.targets)
        # First call projects the Agent targets, the second restores the
        # operator's prior (empty) selection so user state survives.
        self.assertEqual(2, window._select_targets_in_tree.call_count)
        self.assertEqual(
            ["targetA", "targetC"],
            list(window._select_targets_in_tree.call_args_list[0].args[0]),
        )
        self.assertEqual(
            list(context.selected_targets),
            list(window._select_targets_in_tree.call_args_list[1].args[0]),
        )
        window.start.assert_called_once_with("XMeta_run")

    def test_executor_rejects_invalid_targets(self) -> None:
        window = self._window()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        context = _context(visible=("targetA",))
        result = executor.execute("run", context, parameters={"targets": ["ghost"]})
        self.assertEqual("rejected", result.status)
        window.start.assert_not_called()
        window._select_targets_in_tree.assert_not_called()

    def test_executor_uses_selection_when_no_targets_param(self) -> None:
        window = self._window()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        context = _context(selected=("targetB",))
        result = executor.execute("run", context)
        self.assertTrue(result.ok)
        self.assertEqual(("targetB",), result.targets)
        window._select_targets_in_tree.assert_not_called()
        window.start.assert_called_once_with("XMeta_run")

    def test_executor_passes_targets_to_audit_dict(self) -> None:
        window = self._window()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        result = executor.execute(
            "skip", _context(), parameters={"targets": ["targetA"]}
        )
        self.assertEqual(
            {"action_id": "skip", "status": "executed", "detail": "", "targets": ["targetA"]},
            result.as_audit_dict(),
        )


class RulePlannerTargetExtractionTests(unittest.TestCase):
    def test_planner_extracts_visible_targets_from_prompt(self) -> None:
        planner = RulePlanner()
        context = _context(visible=("targetA", "targetB", "targetC"))
        steps = planner.plan("run targetA targetC please", context)
        self.assertEqual(1, len(steps))
        self.assertEqual("run", steps[0].action_id)
        self.assertEqual(["targetA", "targetC"], list(steps[0].parameters["targets"]))

    def test_planner_skips_targets_for_non_parameterizable_action(self) -> None:
        planner = RulePlanner()
        context = _context(visible=("targetA",))
        steps = planner.plan("run all targetA", context)
        self.assertEqual("run_all", steps[0].action_id)
        self.assertEqual({"targets": ["targetA"]}, dict(steps[0].parameters))


class AuditLogTests(unittest.TestCase):
    def test_audit_writes_jsonl_to_sink(self) -> None:
        sink = io.StringIO()
        log = AgentAuditLog(sink=sink, clock=lambda: 12345.0)
        log.record(
            prompt="run all",
            plan=["run_all"],
            rationales=["matched"],
            results=[{"action_id": "run_all", "status": "executed"}],
            errors=[],
        )
        sink.seek(0)
        decoded = json.loads(sink.read().strip())
        self.assertEqual("run all", decoded["prompt"])
        self.assertEqual(["run_all"], decoded["plan"])
        self.assertEqual(12345.0, decoded["timestamp"])

    def test_controller_persists_each_interaction(self) -> None:
        window = MagicMock()
        window.combo = MagicMock()
        window.combo.currentText.return_value = "run-001"
        window.run_base_dir = "/runs"
        window.cached_targets_by_level = {0: ["targetA"]}
        window._active_content_mode = "main"
        window.get_selected_targets.return_value = ["targetA"]
        window.handle_log = MagicMock()

        sink = io.StringIO()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_reject_gate,
            audit_log=AgentAuditLog(sink=sink, clock=lambda: 1.0),
        )
        controller.submit_prompt("open log")
        controller.submit_prompt("unknown thing")
        sink.seek(0)
        lines = [line for line in sink.read().splitlines() if line]
        self.assertEqual(2, len(lines))
        first = json.loads(lines[0])
        self.assertEqual("open log", first["prompt"])
        self.assertEqual(["log"], first["plan"])
        self.assertEqual([], first["errors"])
        second = json.loads(lines[1])
        self.assertEqual("unknown thing", second["prompt"])
        self.assertEqual([], second["plan"])
        self.assertIn("no matching action", second["errors"][0])


class LLMPlannerFallbackTests(unittest.TestCase):
    def test_disabled_settings_fall_back_to_rule_planner(self) -> None:
        captured: List[Tuple[str, AgentSessionContext]] = []

        class _RecordingFallback:
            def plan(self, prompt, context):
                captured.append((prompt, context))
                return (AgentPlanStep(action_id="log", rationale="recorded"),)

        planner = LLMPlanner(
            settings=LLMPlannerSettings(api_key=None),
            fallback=_RecordingFallback(),
        )
        steps = planner.plan("open log", _context())
        self.assertEqual(("log",), tuple(step.action_id for step in steps))
        self.assertEqual(1, len(captured))

    def test_llm_response_is_parsed_into_steps(self) -> None:
        canned = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "steps": [
                                        {
                                            "action_id": "run",
                                            "rationale": "user asked to run A",
                                            "parameters": {"targets": ["targetA"]},
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }
        )

        def fake_http(url, headers, body, timeout):
            self.assertIn("/chat/completions", url)
            self.assertIn("Authorization", headers)
            return canned

        planner = LLMPlanner(
            settings=LLMPlannerSettings(api_key="sk-test", model="gpt-test"),
            fallback=RulePlanner(),
            http_fetcher=fake_http,
        )
        steps = planner.plan("please run target A", _context(visible=("targetA",)))
        self.assertEqual(1, len(steps))
        self.assertEqual("run", steps[0].action_id)
        self.assertEqual({"targets": ["targetA"]}, dict(steps[0].parameters))

    def test_http_error_triggers_fallback(self) -> None:
        def boom(url, headers, body, timeout):
            raise OSError("network down")

        planner = LLMPlanner(
            settings=LLMPlannerSettings(api_key="sk-test"),
            fallback=RulePlanner(),
            http_fetcher=boom,
        )
        steps = planner.plan("open log", _context())
        self.assertEqual(("log",), tuple(step.action_id for step in steps))


if __name__ == "__main__":
    unittest.main()
