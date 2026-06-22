"""Tests for multi-step planning, audit reader, and history formatters."""

import io
import json
import os
import tempfile
import unittest
from typing import List
from unittest.mock import MagicMock

from new_gui.application.agent import (
    AgentAuditLog,
    AgentPlanStep,
    AgentSessionContext,
    AuditRecord,
    MultiStepAgentLoop,
    RulePlanner,
    RunStateObservation,
    load_audit_file,
    parse_audit_lines,
    summarize_records,
)
from new_gui.application.agent.agent_executor import (
    auto_approve_gate,
    auto_reject_gate,
)
from new_gui.presentation.presenters.agent_controller import AgentController
from new_gui.presentation.views.widgets.agent_panel import (
    format_audit_records,
    format_audit_summary,
)


def _build_window(*, selected=("targetA",)):
    window = MagicMock()
    combo = MagicMock()
    combo.currentText.return_value = "run-001"
    window.combo = combo
    window.run_base_dir = "/runs"
    window.cached_targets_by_level = {0: ["targetA", "targetB", "targetC"]}
    window._active_content_mode = "main"
    window._status_cache = {}
    window.get_selected_targets.return_value = list(selected)
    window.handle_log = MagicMock()
    window._select_targets_in_tree = MagicMock()
    return window


class MultiStepAgentLoopTests(unittest.TestCase):
    def test_loop_stops_when_planner_returns_no_steps(self) -> None:
        controller = MagicMock()
        controller.submit_prompt.side_effect = [
            MagicMock(
                steps=(AgentPlanStep(action_id="log", rationale="r1"),),
                results=(MagicMock(),),
                errors=(),
                observation_before=RunStateObservation(current_run="r"),
                observation_after=RunStateObservation(
                    current_run="r", status_counts={"success": 1}
                ),
                observation_diff=MagicMock(
                    is_empty=MagicMock(return_value=False),
                    to_dict=MagicMock(return_value={"status_delta": {"success": 1}}),
                ),
            ),
            MagicMock(
                steps=(),
                results=(),
                errors=("planner returned no matching action",),
                observation_before=RunStateObservation(current_run="r"),
                observation_after=RunStateObservation(current_run="r"),
                observation_diff=MagicMock(is_empty=MagicMock(return_value=True)),
            ),
        ]

        loop = MultiStepAgentLoop(controller, max_iterations=4)
        record = loop.run("inspect then act")
        self.assertEqual("planner_finished", record.stop_reason)
        self.assertEqual(2, len(record.turns))
        self.assertEqual("inspect then act", record.turns[0].prompt)
        self.assertIn("[loop iteration 2]", record.turns[1].prompt)

    def test_loop_stops_when_no_state_change(self) -> None:
        empty_diff = MagicMock(is_empty=MagicMock(return_value=True))
        controller = MagicMock()
        controller.submit_prompt.return_value = MagicMock(
            steps=(AgentPlanStep(action_id="log", rationale="r"),),
            results=(MagicMock(),),
            errors=(),
            observation_before=RunStateObservation(current_run="r"),
            observation_after=RunStateObservation(current_run="r"),
            observation_diff=empty_diff,
        )
        record = MultiStepAgentLoop(controller, max_iterations=3).run("x")
        self.assertEqual("no_state_change", record.stop_reason)
        self.assertEqual(1, len(record.turns))

    def test_loop_hits_max_iterations(self) -> None:
        non_empty = MagicMock(
            is_empty=MagicMock(return_value=False),
            to_dict=MagicMock(return_value={"status_delta": {"success": 1}}),
        )
        controller = MagicMock()
        # Return distinct steps each iteration so the loop is not short-circuited
        # by the plan_repeated detector; we want the max_iterations cap to fire.
        controller.submit_prompt.side_effect = [
            MagicMock(
                steps=(AgentPlanStep(action_id="log", rationale="r1"),),
                results=(MagicMock(),),
                errors=(),
                observation_before=RunStateObservation(current_run="r"),
                observation_after=RunStateObservation(current_run="r"),
                observation_diff=non_empty,
            ),
            MagicMock(
                steps=(AgentPlanStep(action_id="trace_up", rationale="r2"),),
                results=(MagicMock(),),
                errors=(),
                observation_before=RunStateObservation(current_run="r"),
                observation_after=RunStateObservation(current_run="r"),
                observation_diff=non_empty,
            ),
        ]
        record = MultiStepAgentLoop(controller, max_iterations=2).run("x")
        self.assertEqual("max_iterations", record.stop_reason)
        self.assertEqual(2, len(record.turns))

    def test_loop_rejects_invalid_max_iterations(self) -> None:
        with self.assertRaises(ValueError):
            MultiStepAgentLoop(MagicMock(), max_iterations=0)


class AuditReaderTests(unittest.TestCase):
    def _sample_records(self):
        return [
            json.dumps({
                "timestamp": 1.0,
                "prompt": "open log",
                "plan": ["log"],
                "rationales": [""],
                "results": [{"action_id": "log", "status": "executed"}],
                "errors": [],
                "observation": {
                    "diff": {"status_delta": {"success": 1}},
                },
            }),
            "garbage line",
            json.dumps({
                "timestamp": 2.0,
                "prompt": "polish hair",
                "plan": [],
                "rationales": [],
                "results": [],
                "errors": ["planner returned no matching action"],
                "observation": None,
            }),
            json.dumps({
                "timestamp": 3.0,
                "prompt": "run all",
                "plan": ["run_all"],
                "rationales": [""],
                "results": [{"action_id": "run_all", "status": "rejected"}],
                "errors": ["user confirmation denied"],
                "observation": None,
            }),
        ]

    def test_parse_skips_malformed_lines(self) -> None:
        records = parse_audit_lines(self._sample_records())
        self.assertEqual(3, len(records))
        self.assertEqual("open log", records[0].prompt)
        self.assertEqual(("run_all",), records[2].plan)

    def test_summarize_counts(self) -> None:
        records = parse_audit_lines(self._sample_records())
        summary = summarize_records(records)
        self.assertEqual(3, summary["total_prompts"])
        self.assertEqual(2, summary["total_actions"])
        self.assertEqual(1, summary["executed"])
        self.assertEqual(1, summary["rejected"])
        self.assertEqual(1, summary["planner_misses"])
        self.assertEqual({"log": 1, "run_all": 1}, summary["actions_by_id"])

    def test_load_audit_file_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.log")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(self._sample_records()) + "\n")
            records = load_audit_file(path)
            self.assertEqual(3, len(records))

    def test_load_audit_file_missing_returns_empty(self) -> None:
        self.assertEqual([], load_audit_file("/nonexistent/path"))


class AgentPanelFormattersTests(unittest.TestCase):
    def _record(self, **overrides) -> AuditRecord:
        defaults = dict(
            timestamp=1.0,
            prompt="run all",
            plan=("run_all",),
            results=(
                {"action_id": "run_all", "status": "executed", "detail": "", "targets": []},
            ),
            errors=(),
            observation={"diff": {"status_delta": {"success": 2}}},
        )
        defaults.update(overrides)
        return AuditRecord(**defaults)

    def test_summary_formatter_lists_action_counts(self) -> None:
        text = format_audit_summary([
            self._record(),
            self._record(prompt="open log", plan=("log",), results=(
                {"action_id": "log", "status": "executed"},
            )),
        ])
        self.assertIn("Prompts: 2", text)
        self.assertIn("executed: 2", text)
        self.assertIn("log=1", text)
        self.assertIn("run_all=1", text)

    def test_records_formatter_renders_status_delta(self) -> None:
        text = format_audit_records([self._record()])
        self.assertIn("run all", text)
        self.assertIn("run_all=executed", text)
        self.assertIn("success+2", text)

    def test_records_formatter_handles_empty(self) -> None:
        self.assertIn("no audit records", format_audit_records([]))


class ControllerLoopIntegrationTests(unittest.TestCase):
    """End-to-end multi-step run using the real controller."""

    def test_two_step_log_then_no_op(self) -> None:
        snapshots: List[RunStateObservation] = [
            RunStateObservation(current_run="r", status_counts={"success": 1}),
            RunStateObservation(current_run="r", status_counts={"success": 2}),
            RunStateObservation(current_run="r", status_counts={"success": 2}),
            RunStateObservation(current_run="r", status_counts={"success": 2}),
        ]

        def fake_collector(_window):
            return snapshots.pop(0) if snapshots else RunStateObservation(current_run="r")

        sink = io.StringIO()
        controller = AgentController(
            _build_window(),
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
            audit_log=AgentAuditLog(sink=sink, clock=lambda: 1.0),
            observation_collector=fake_collector,
        )
        record = MultiStepAgentLoop(controller, max_iterations=3).run("open log")
        self.assertGreaterEqual(len(record.turns), 1)
        first_turn_prompt = record.turns[0].prompt
        self.assertEqual("open log", first_turn_prompt)
        self.assertIn(record.stop_reason, {"planner_finished", "no_state_change"})


if __name__ == "__main__":
    unittest.main()
