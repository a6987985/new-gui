"""Invariant tests for the Executable Agent's First-Version Action Boundary."""

import unittest
from typing import List, Tuple
from unittest.mock import MagicMock

from new_gui.application.agent import (
    AgentExecutionError,
    AgentExecutor,
    ConfirmationDecision,
    build_action_catalog,
    catalog_as_dict,
    snapshot_session_context,
)
from new_gui.application.agent.agent_executor import (
    auto_approve_gate,
    auto_reject_gate,
)
from new_gui.application.registries.action_registry import (
    get_all_action_definitions,
    get_top_button_action_ids,
)


class ActionRegistryAgentMetadataTests(unittest.TestCase):
    def test_state_changing_actions_require_confirmation(self) -> None:
        offenders = [
            definition.action_id
            for definition in get_all_action_definitions()
            if definition.mutates_state and not definition.requires_confirmation
        ]
        self.assertEqual(
            [],
            offenders,
            "every State-Changing Action must require User Confirmation",
        )

    def test_read_only_actions_do_not_require_confirmation(self) -> None:
        offenders = [
            definition.action_id
            for definition in get_all_action_definitions()
            if (not definition.mutates_state) and definition.requires_confirmation
        ]
        self.assertEqual(
            [],
            offenders,
            "Read-Only Actions must not request a confirmation prompt",
        )

    def test_every_action_has_agent_description(self) -> None:
        missing = [
            definition.action_id
            for definition in get_all_action_definitions()
            if not (definition.agent_description or definition.tooltip)
        ]
        self.assertEqual([], missing)

    def test_categories_are_within_allowed_set(self) -> None:
        allowed = {"execute", "file", "trace", "terminal"}
        offenders = [
            definition.action_id
            for definition in get_all_action_definitions()
            if definition.category not in allowed
        ]
        self.assertEqual([], offenders)


class ActionCatalogTests(unittest.TestCase):
    def test_catalog_covers_every_registered_action(self) -> None:
        registered_ids = {d.action_id for d in get_all_action_definitions()}
        catalog_ids = {entry.action_id for entry in build_action_catalog()}
        self.assertEqual(registered_ids, catalog_ids)

    def test_catalog_dict_is_json_serializable(self) -> None:
        import json

        payload = catalog_as_dict()
        json.dumps(payload)
        self.assertTrue(payload)
        sample = payload[0]
        self.assertIn("action_id", sample)
        self.assertIn("mutates_state", sample)
        self.assertIn("requires_confirmation", sample)
        self.assertIn("description", sample)

    def test_catalog_does_not_expose_trigger(self) -> None:
        for entry in build_action_catalog():
            self.assertFalse(
                hasattr(entry, "trigger"),
                "AgentActionEntry must not leak the UI trigger callable",
            )

    def test_top_button_actions_are_in_catalog(self) -> None:
        catalog_ids = {entry.action_id for entry in build_action_catalog()}
        for action_id in get_top_button_action_ids():
            self.assertIn(action_id, catalog_ids)


class AgentExecutorBoundaryTests(unittest.TestCase):
    def _context_with_selection(self) -> object:
        return snapshot_session_context(
            run_base_dir="/runs",
            current_run="run-001",
            selected_targets=("targetA",),
            visible_targets=("targetA", "targetB"),
        )

    def _context_without_selection(self) -> object:
        return snapshot_session_context(
            run_base_dir="/runs",
            current_run="run-001",
            selected_targets=(),
            visible_targets=("targetA",),
        )

    def test_unknown_action_is_rejected(self) -> None:
        executor = AgentExecutor(window=MagicMock())
        with self.assertRaises(AgentExecutionError):
            executor.execute("rm_rf_root", self._context_with_selection())

    def test_state_changing_action_requires_approval(self) -> None:
        window = MagicMock()
        captured: List[Tuple[str, bool]] = []

        def gate(definition, context):
            captured.append((definition.action_id, definition.mutates_state))
            return ConfirmationDecision.REJECTED

        executor = AgentExecutor(window=window, confirmation_gate=gate)
        result = executor.execute("run", self._context_with_selection())
        self.assertEqual("rejected", result.status)
        self.assertFalse(result.ok)
        window.start.assert_not_called()
        self.assertEqual([("run", True)], captured)

    def test_state_changing_action_runs_when_approved(self) -> None:
        window = MagicMock()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        result = executor.execute("run", self._context_with_selection())
        self.assertEqual("executed", result.status)
        window.start.assert_called_once_with("XMeta_run")

    def test_read_only_action_bypasses_confirmation(self) -> None:
        window = MagicMock()
        executor = AgentExecutor(window=window, confirmation_gate=auto_reject_gate)
        result = executor.execute("log", self._context_with_selection())
        self.assertEqual("executed", result.status)
        window.handle_log.assert_called_once_with()

    def test_selection_required_action_rejected_without_selection(self) -> None:
        window = MagicMock()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        result = executor.execute("run", self._context_without_selection())
        self.assertEqual("rejected", result.status)
        window.start.assert_not_called()

    def test_run_all_works_without_selection(self) -> None:
        window = MagicMock()
        executor = AgentExecutor(window=window, confirmation_gate=auto_approve_gate)
        result = executor.execute("run_all", self._context_without_selection())
        self.assertEqual("executed", result.status)
        window.start.assert_called_once_with("XMeta_run all")


if __name__ == "__main__":
    unittest.main()
