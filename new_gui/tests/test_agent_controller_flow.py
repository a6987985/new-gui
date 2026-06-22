"""End-to-end tests for the Agent controller wired against a fake MainWindow."""

import unittest
from typing import List, Tuple
from unittest.mock import MagicMock

from new_gui.application.agent import (
    AgentSessionContext,
    ConfirmationDecision,
    RulePlanner,
    snapshot_from_window,
)
from new_gui.application.agent.agent_executor import auto_approve_gate, auto_reject_gate
from new_gui.presentation.presenters.agent_controller import (
    AgentController,
    qt_confirmation_gate,
)


class _FakeCombo:
    def __init__(self, value: str) -> None:
        self._value = value

    def currentText(self) -> str:
        return self._value


class _FakeWindow:
    """Stand-in for MainWindow exposing only the attributes the Agent reads."""

    def __init__(
        self,
        *,
        run_name: str = "run-001",
        selected: Tuple[str, ...] = ("targetA",),
        visible: Tuple[Tuple[int, Tuple[str, ...]], ...] = ((0, ("targetA", "targetB")),),
        mode: str = "main",
    ) -> None:
        self.run_base_dir = "/runs"
        self.combo = _FakeCombo(run_name)
        self._selected = list(selected)
        self.cached_targets_by_level = {level: list(items) for level, items in visible}
        self._active_content_mode = mode
        self.start_calls: List[str] = []
        self.handle_log = MagicMock()
        self.handle_csh = MagicMock()
        self.handle_cmd = MagicMock()
        self.open_terminal = MagicMock()
        self.retrace_tab = MagicMock()

    def start(self, command: str) -> None:
        self.start_calls.append(command)

    def get_selected_targets(self):
        return list(self._selected)


class SnapshotFromWindowTests(unittest.TestCase):
    def test_snapshot_pulls_run_targets_and_mode(self) -> None:
        window = _FakeWindow()
        context = snapshot_from_window(window)
        self.assertIsInstance(context, AgentSessionContext)
        self.assertEqual("run-001", context.current_run)
        self.assertEqual("/runs", context.run_base_dir)
        self.assertEqual(("targetA",), context.selected_targets)
        self.assertIn("targetA", context.visible_targets)
        self.assertIn("targetB", context.visible_targets)
        self.assertEqual("main", context.view_mode)

    def test_snapshot_handles_no_runs_placeholder(self) -> None:
        window = _FakeWindow(run_name="No runs found")
        context = snapshot_from_window(window)
        self.assertIsNone(context.current_run)
        self.assertEqual((), context.visible_targets)

    def test_snapshot_handles_missing_combo(self) -> None:
        window = _FakeWindow()
        delattr(window, "combo")
        context = snapshot_from_window(window)
        self.assertIsNone(context.current_run)


class RulePlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RulePlanner()
        self.context = AgentSessionContext(
            run_base_dir="/runs",
            current_run="run-001",
            selected_targets=("targetA",),
        )

    def test_empty_prompt_returns_no_plan(self) -> None:
        self.assertEqual((), self.planner.plan("", self.context))

    def test_run_all_keyword(self) -> None:
        steps = self.planner.plan("please run all", self.context)
        self.assertEqual(1, len(steps))
        self.assertEqual("run_all", steps[0].action_id)

    def test_run_keyword(self) -> None:
        steps = self.planner.plan("run selected", self.context)
        self.assertEqual("run", steps[0].action_id)

    def test_explicit_action_id_wins(self) -> None:
        steps = self.planner.plan("trace_down", self.context)
        self.assertEqual("trace_down", steps[0].action_id)

    def test_unknown_prompt(self) -> None:
        self.assertEqual((), self.planner.plan("polish my hair", self.context))


class AgentControllerEndToEndTests(unittest.TestCase):
    def test_controller_runs_read_only_action(self) -> None:
        window = _FakeWindow()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_reject_gate,
        )
        record = controller.submit_prompt("open log")
        self.assertEqual(("log",), tuple(step.action_id for step in record.steps))
        self.assertTrue(record.ok)
        window.handle_log.assert_called_once_with()

    def test_controller_blocks_state_change_without_confirmation(self) -> None:
        window = _FakeWindow()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_reject_gate,
        )
        record = controller.submit_prompt("run all")
        self.assertEqual(("run_all",), tuple(step.action_id for step in record.steps))
        self.assertEqual([], window.start_calls)
        self.assertEqual("rejected", record.results[0].status)
        self.assertFalse(record.ok)

    def test_controller_runs_state_change_when_approved(self) -> None:
        window = _FakeWindow()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
        )
        record = controller.submit_prompt("run all")
        self.assertEqual(["XMeta_run all"], window.start_calls)
        self.assertTrue(record.ok)

    def test_unknown_prompt_records_planner_miss(self) -> None:
        window = _FakeWindow()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
        )
        record = controller.submit_prompt("teach me python")
        self.assertEqual((), record.steps)
        self.assertIn("no matching action", record.errors[0])

    def test_history_accumulates(self) -> None:
        window = _FakeWindow()
        controller = AgentController(
            window,
            planner=RulePlanner(),
            confirmation_gate=auto_approve_gate,
        )
        controller.submit_prompt("log")
        controller.submit_prompt("trace up")
        self.assertEqual(2, len(controller.history))
        self.assertEqual("log", controller.history[0].steps[0].action_id)
        self.assertEqual("trace_up", controller.history[1].steps[0].action_id)


class QtConfirmationGateFallbackTests(unittest.TestCase):
    def test_gate_factory_returns_callable(self) -> None:
        gate = qt_confirmation_gate(window=object())
        self.assertTrue(callable(gate))


if __name__ == "__main__":
    unittest.main()
