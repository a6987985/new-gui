"""Regression tests for the Agent bug fixes (cache staleness, selection
restore, graph-mode rejection, case-insensitive targets, plan loops).
"""

import unittest
from typing import List
from unittest.mock import MagicMock

from new_gui.application.agent import (
    AgentExecutor,
    AgentPlanStep,
    AgentSessionContext,
    MultiStepAgentLoop,
    ObservationDiff,
    RulePlanner,
    RunStateObservation,
    diff_observations,
    snapshot_from_window,
    snapshot_session_context,
)
from new_gui.application.agent.agent_executor import auto_approve_gate


class StaleDependencyCacheTests(unittest.TestCase):
    """snapshot must not treat a previous-run cache as visibility for the new run."""

    def _window(self, *, run_name="run-002", cached_run="run-001"):
        combo = MagicMock()
        combo.currentText.return_value = run_name
        window = MagicMock()
        window.combo = combo
        window.run_base_dir = "/runs"
        window.cached_targets_by_level = {0: ["legacyA", "legacyB"]}
        window._cached_targets_run = cached_run
        window._active_content_mode = "main"
        window._status_cache = {}
        window.get_selected_targets.return_value = []
        return window

    def test_visible_targets_blanked_when_cache_belongs_to_other_run(self) -> None:
        window = self._window(run_name="run-002", cached_run="run-001")
        context = snapshot_from_window(window)
        self.assertEqual("run-002", context.current_run)
        self.assertEqual((), context.visible_targets)

    def test_visible_targets_used_when_cache_matches_run(self) -> None:
        window = self._window(run_name="run-001", cached_run="run-001")
        context = snapshot_from_window(window)
        self.assertEqual(("legacyA", "legacyB"), context.visible_targets)


class DiffSuppressionTests(unittest.TestCase):
    def test_run_change_suppresses_status_delta(self) -> None:
        before = RunStateObservation(
            current_run="A",
            status_counts={"success": 5, "failed": 1},
        )
        after = RunStateObservation(
            current_run="B",
            status_counts={"success": 1},
        )
        diff = diff_observations(before, after)
        self.assertTrue(diff.run_changed)
        self.assertEqual({}, dict(diff.status_delta))

    def test_first_cache_fill_does_not_trigger_status_delta(self) -> None:
        before = RunStateObservation(current_run="A", status_counts={})
        after = RunStateObservation(
            current_run="A",
            status_counts={"success": 3, "pending": 2},
        )
        diff = diff_observations(before, after)
        self.assertFalse(diff.run_changed)
        self.assertEqual({}, dict(diff.status_delta))

    def test_real_status_change_still_reported(self) -> None:
        before = RunStateObservation(current_run="A", status_counts={"success": 1})
        after = RunStateObservation(current_run="A", status_counts={"success": 2})
        diff = diff_observations(before, after)
        self.assertEqual({"success": 1}, dict(diff.status_delta))


class SelectionRestoreTests(unittest.TestCase):
    def test_executor_restores_original_selection(self) -> None:
        applied: List[List[str]] = []
        window = MagicMock()

        def applier(_window, targets):
            applied.append(list(targets))

        executor = AgentExecutor(
            window=window,
            confirmation_gate=auto_approve_gate,
            selection_applier=applier,
        )
        context = snapshot_session_context(
            run_base_dir="/r",
            current_run="r",
            selected_targets=("user_choice_A", "user_choice_B"),
            visible_targets=(
                "user_choice_A",
                "user_choice_B",
                "agent_target_C",
                "agent_target_D",
            ),
        )
        result = executor.execute(
            "run",
            context,
            parameters={"targets": ["agent_target_C", "agent_target_D"]},
        )
        self.assertTrue(result.ok)
        self.assertEqual(2, len(applied))
        self.assertEqual(["agent_target_C", "agent_target_D"], applied[0])
        self.assertEqual(["user_choice_A", "user_choice_B"], applied[1])

    def test_executor_does_not_restore_when_no_targets_param(self) -> None:
        applied: List[List[str]] = []

        def applier(_window, targets):
            applied.append(list(targets))

        executor = AgentExecutor(
            window=MagicMock(),
            confirmation_gate=auto_approve_gate,
            selection_applier=applier,
        )
        context = snapshot_session_context(
            run_base_dir="/r",
            current_run="r",
            selected_targets=("user_choice",),
            visible_targets=("user_choice",),
        )
        result = executor.execute("run", context)
        self.assertTrue(result.ok)
        self.assertEqual([], applied)


class GraphModeParameterRejectionTests(unittest.TestCase):
    def test_graph_mode_rejects_parameterized_targets(self) -> None:
        applied: List[List[str]] = []
        window = MagicMock()

        def applier(_w, targets):
            applied.append(list(targets))

        executor = AgentExecutor(
            window=window,
            confirmation_gate=auto_approve_gate,
            selection_applier=applier,
        )
        context = snapshot_session_context(
            run_base_dir="/r",
            current_run="r",
            visible_targets=("A", "B"),
            view_mode="graph",
        )
        result = executor.execute(
            "run", context, parameters={"targets": ["A", "B"]}
        )
        self.assertEqual("rejected", result.status)
        self.assertIn("graph", result.detail.lower() + "|" + context.view_mode)
        window.start.assert_not_called()
        self.assertEqual([], applied)

    def test_graph_mode_still_allows_unparameterized_actions(self) -> None:
        window = MagicMock()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        context = snapshot_session_context(
            run_base_dir="/r",
            current_run="r",
            selected_targets=("A",),
            visible_targets=("A",),
            view_mode="graph",
        )
        result = executor.execute("log", context)
        self.assertTrue(result.ok)
        window.handle_log.assert_called_once_with()


class CaseInsensitiveTargetExtractionTests(unittest.TestCase):
    def test_target_token_match_ignores_case(self) -> None:
        planner = RulePlanner()
        context = snapshot_session_context(
            run_base_dir="/r",
            current_run="r",
            visible_targets=("targetAlpha", "targetBeta"),
        )
        steps = planner.plan("Run TARGETALPHA targetbeta", context)
        self.assertEqual(1, len(steps))
        self.assertEqual("run", steps[0].action_id)
        self.assertEqual(
            ["targetAlpha", "targetBeta"], list(steps[0].parameters["targets"])
        )


class PlanLoopDetectionTests(unittest.TestCase):
    def test_loop_breaks_when_plan_repeats(self) -> None:
        non_empty_diff = ObservationDiff(
            run_changed=False,
            status_delta={"success": 1},
            selection_added=(),
            selection_removed=(),
        )
        controller = MagicMock()
        controller.submit_prompt.return_value = MagicMock(
            steps=(AgentPlanStep(action_id="log", rationale="r", parameters={}),),
            results=(MagicMock(),),
            errors=(),
            observation_before=RunStateObservation(current_run="r"),
            observation_after=RunStateObservation(
                current_run="r", status_counts={"success": 1}
            ),
            observation_diff=non_empty_diff,
        )
        record = MultiStepAgentLoop(controller, max_iterations=5).run("open log")
        self.assertEqual("plan_repeated", record.stop_reason)
        self.assertEqual(2, len(record.turns))

    def test_loop_handles_list_parameters_for_signature(self) -> None:
        non_empty_diff = ObservationDiff(
            run_changed=False,
            status_delta={"success": 1},
            selection_added=(),
            selection_removed=(),
        )
        controller = MagicMock()
        controller.submit_prompt.return_value = MagicMock(
            steps=(
                AgentPlanStep(
                    action_id="run",
                    rationale="r",
                    parameters={"targets": ["A", "B"]},
                ),
            ),
            results=(MagicMock(),),
            errors=(),
            observation_before=RunStateObservation(current_run="r"),
            observation_after=RunStateObservation(
                current_run="r", status_counts={"success": 1}
            ),
            observation_diff=non_empty_diff,
        )
        # Must not raise on unhashable list parameters
        record = MultiStepAgentLoop(controller, max_iterations=4).run("run A B")
        self.assertEqual("plan_repeated", record.stop_reason)


if __name__ == "__main__":
    unittest.main()
