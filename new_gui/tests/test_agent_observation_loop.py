"""Tests for the post-action observation loop wired into AgentController."""

import io
import json
import unittest
from typing import List
from unittest.mock import MagicMock

from new_gui.application.agent import (
    AgentAuditLog,
    ObservationDiff,
    RulePlanner,
    RunStateObservation,
    default_collector,
    diff_observations,
)
from new_gui.application.agent.agent_executor import (
    auto_approve_gate,
    auto_reject_gate,
)
from new_gui.presentation.presenters.agent_controller import AgentController


def _build_window(*, status_cache=None, selected=("targetA",), run="run-001"):
    window = MagicMock()
    combo = MagicMock()
    combo.currentText.return_value = run
    window.combo = combo
    window.run_base_dir = "/runs"
    window.cached_targets_by_level = {0: ["targetA", "targetB", "targetC"]}
    window._active_content_mode = "main"
    window._status_cache = dict(status_cache or {})
    window.get_selected_targets.return_value = list(selected)
    window.handle_log = MagicMock()
    window._select_targets_in_tree = MagicMock()
    return window


class DefaultCollectorTests(unittest.TestCase):
    def test_collector_aggregates_status_counts(self) -> None:
        window = _build_window(
            status_cache={
                "targetA": "success",
                "targetB": "success",
                "targetC": "failed",
            },
            selected=("targetA",),
        )
        observation = default_collector(window)
        self.assertEqual("run-001", observation.current_run)
        self.assertEqual(2, observation.status_counts["success"])
        self.assertEqual(1, observation.status_counts["failed"])
        self.assertEqual(("targetA",), observation.selected_targets)

    def test_collector_handles_missing_state(self) -> None:
        window = MagicMock(spec=[])
        observation = default_collector(window)
        self.assertIsNone(observation.current_run)
        self.assertEqual({}, dict(observation.status_counts))
        self.assertEqual((), observation.selected_targets)


class ObservationDiffTests(unittest.TestCase):
    def test_diff_reports_status_change_and_selection_change(self) -> None:
        before = RunStateObservation(
            current_run="r",
            status_counts={"success": 1, "pending": 2},
            selected_targets=("a",),
        )
        after = RunStateObservation(
            current_run="r",
            status_counts={"success": 2, "pending": 1, "failed": 1},
            selected_targets=("a", "b"),
        )
        diff = diff_observations(before, after)
        self.assertFalse(diff.run_changed)
        self.assertEqual({"success": 1, "pending": -1, "failed": 1}, dict(diff.status_delta))
        self.assertEqual(("b",), diff.selection_added)
        self.assertEqual((), diff.selection_removed)
        self.assertFalse(diff.is_empty())

    def test_diff_empty_when_state_unchanged(self) -> None:
        snap = RunStateObservation(
            current_run="r", status_counts={"success": 1}, selected_targets=("a",)
        )
        diff = diff_observations(snap, snap)
        self.assertTrue(diff.is_empty())


class ControllerObservationLoopTests(unittest.TestCase):
    def test_record_captures_before_and_after_observations(self) -> None:
        snapshots: List[RunStateObservation] = [
            RunStateObservation(
                current_run="r",
                status_counts={"success": 1},
                selected_targets=("targetA",),
            ),
            RunStateObservation(
                current_run="r",
                status_counts={"success": 2},
                selected_targets=("targetA",),
            ),
        ]

        def fake_collector(_window):
            return snapshots.pop(0)

        window = _build_window(selected=("targetA",))
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
            observation_collector=fake_collector,
        )
        record = controller.submit_prompt("open log")
        self.assertTrue(record.ok)
        self.assertIsNotNone(record.observation_before)
        self.assertIsNotNone(record.observation_after)
        self.assertIsNotNone(record.observation_diff)
        self.assertEqual({"success": 1}, dict(record.observation_diff.status_delta))

    def test_collector_exception_does_not_break_submit(self) -> None:
        def broken_collector(_window):
            raise RuntimeError("collector down")

        window = _build_window(selected=("targetA",))
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
            observation_collector=broken_collector,
        )
        record = controller.submit_prompt("open log")
        self.assertTrue(record.ok)
        self.assertIsNone(record.observation_before)
        self.assertIsNone(record.observation_after)
        self.assertIsNone(record.observation_diff)

    def test_audit_log_includes_observation_payload(self) -> None:
        snapshots: List[RunStateObservation] = [
            RunStateObservation(
                current_run="r",
                status_counts={"success": 1},
                selected_targets=("targetA",),
            ),
            RunStateObservation(
                current_run="r",
                status_counts={"success": 2},
                selected_targets=("targetA",),
            ),
        ]

        def fake_collector(_window):
            return snapshots.pop(0)

        sink = io.StringIO()
        controller = AgentController(
            _build_window(selected=("targetA",)),
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
            audit_log=AgentAuditLog(sink=sink, clock=lambda: 1.0),
            observation_collector=fake_collector,
        )
        controller.submit_prompt("open log")
        sink.seek(0)
        decoded = json.loads(sink.read().strip())
        self.assertIn("observation", decoded)
        observation = decoded["observation"]
        self.assertIsNotNone(observation)
        self.assertEqual(
            {"success": 1}, dict(observation["diff"]["status_delta"])
        )
        self.assertEqual("r", observation["before"]["current_run"])

    def test_planner_miss_still_records_observations(self) -> None:
        snapshots = [
            RunStateObservation(current_run="r"),
            RunStateObservation(current_run="r"),
        ]

        def fake_collector(_window):
            return snapshots.pop(0)

        controller = AgentController(
            _build_window(),
            planner=RulePlanner(),
            confirmation_gate=auto_reject_gate,
            observation_collector=fake_collector,
        )
        record = controller.submit_prompt("hello there")
        self.assertEqual((), record.steps)
        self.assertIsNotNone(record.observation_before)
        self.assertIsNotNone(record.observation_after)
        self.assertIsNotNone(record.observation_diff)
        self.assertTrue(record.observation_diff.is_empty())


if __name__ == "__main__":
    unittest.main()
