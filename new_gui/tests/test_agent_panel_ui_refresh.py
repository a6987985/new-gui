"""Tests for the refreshed Agent panel: multi-line prompt, status badge, KPI cards."""

from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from new_gui.application.agent import AgentAuditEntry, AgentAuditLog
from new_gui.application.agent.agent_audit_reader import AuditRecord
from new_gui.application.agent.agent_executor import AgentExecutionResult
from new_gui.application.agent.agent_planner import AgentPlanStep
from new_gui.presentation.presenters.agent_controller import AgentInteractionRecord
from new_gui.presentation.views.widgets.agent_panel import (
    AgentPanel,
    _PromptTextEdit,
    kpi_counts,
)
from new_gui.shared.config.settings import THEMES


_APP = QApplication.instance() or QApplication(sys.argv)


class _StubController:
    """Minimal controller stub used by AgentPanel constructors."""

    audit_log = None

    def __init__(self, record=None, raise_exc=None):
        self._record = record
        self._raise_exc = raise_exc

    def submit_prompt(self, prompt):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._record


def _record_with_results(prompt, *statuses, errors=()):
    steps = tuple(
        AgentPlanStep(action_id=f"a{i}", rationale="t") for i, _ in enumerate(statuses)
    )
    results = tuple(
        AgentExecutionResult(action_id=f"a{i}", status=status, detail="", targets=())
        for i, status in enumerate(statuses)
    )
    return AgentInteractionRecord(
        prompt=prompt,
        steps=steps,
        results=results,
        errors=errors,
    )


def _press(widget, key, modifiers=Qt.NoModifier):
    event = QKeyEvent(QEvent.KeyPress, key, modifiers)
    widget.keyPressEvent(event)


class PromptTextEditBehaviorTests(unittest.TestCase):
    def test_enter_invokes_submit_callback(self):
        called = []
        edit = _PromptTextEdit(submit_callback=lambda: called.append(True))
        edit.setPlainText("hello")
        _press(edit, Qt.Key_Return)
        self.assertEqual(called, [True])

    def test_shift_enter_inserts_newline_without_submit(self):
        called = []
        edit = _PromptTextEdit(submit_callback=lambda: called.append(True))
        edit.setPlainText("line one")
        edit.moveCursor(edit.textCursor().End)
        _press(edit, Qt.Key_Return, Qt.ShiftModifier)
        self.assertIn("\n", edit.toPlainText())
        self.assertEqual(called, [])

    def test_ctrl_up_walks_history(self):
        edit = _PromptTextEdit(submit_callback=lambda: None)
        edit.record_submission("first")
        edit.record_submission("second")
        edit.setPlainText("draft")
        _press(edit, Qt.Key_Up, Qt.ControlModifier)
        self.assertEqual(edit.toPlainText(), "second")
        _press(edit, Qt.Key_Up, Qt.ControlModifier)
        self.assertEqual(edit.toPlainText(), "first")
        _press(edit, Qt.Key_Down, Qt.ControlModifier)
        self.assertEqual(edit.toPlainText(), "second")
        _press(edit, Qt.Key_Down, Qt.ControlModifier)
        # Past newest entry restores the pending draft.
        self.assertEqual(edit.toPlainText(), "draft")


class AgentPanelStatusBadgeTests(unittest.TestCase):
    def test_idle_state_by_default(self):
        panel = AgentPanel(_StubController(), theme=THEMES["light"])
        self.assertEqual(panel._status_badge.property("agentStatus"), "idle")
        self.assertEqual(panel._status_badge.text(), "Idle")

    def test_successful_record_sets_ok_status(self):
        record = _record_with_results("run all", "executed", "executed")
        panel = AgentPanel(_StubController(record=record), theme=THEMES["light"])
        panel._prompt_edit.setPlainText("run all")
        panel._on_submit_clicked()
        self.assertEqual(panel._status_badge.property("agentStatus"), "ok")
        self.assertIn("Executed", panel._footer_status.text())

    def test_controller_exception_sets_fail_status_and_error_bubble(self):
        panel = AgentPanel(
            _StubController(raise_exc=RuntimeError("boom")), theme=THEMES["light"]
        )
        panel._prompt_edit.setPlainText("explode")
        panel._on_submit_clicked()
        self.assertEqual(panel._status_badge.property("agentStatus"), "fail")
        self.assertIn("Error", panel._transcript.toHtml())

    def test_rejected_only_results_yield_fail_status(self):
        record = _record_with_results("danger", "rejected")
        panel = AgentPanel(_StubController(record=record), theme=THEMES["light"])
        panel._prompt_edit.setPlainText("danger")
        panel._on_submit_clicked()
        self.assertEqual(panel._status_badge.property("agentStatus"), "fail")


class AgentPanelTranscriptTests(unittest.TestCase):
    def test_user_bubble_contains_prompt_text(self):
        record = _record_with_results("hello agent", "executed")
        panel = AgentPanel(_StubController(record=record), theme=THEMES["light"])
        panel._prompt_edit.setPlainText("hello agent")
        panel._on_submit_clicked()
        html = panel._transcript.toHtml()
        self.assertIn("hello agent", html)
        self.assertIn("Plan", html)
        self.assertIn("Result", html)

    def test_clear_transcript_resets_status_and_html(self):
        record = _record_with_results("ping", "executed")
        panel = AgentPanel(_StubController(record=record), theme=THEMES["light"])
        panel._prompt_edit.setPlainText("ping")
        panel._on_submit_clicked()
        panel.clear_transcript()
        self.assertEqual(panel._transcript.toPlainText(), "")
        self.assertEqual(panel._status_badge.property("agentStatus"), "idle")


class AgentPanelHistoryKpiTests(unittest.TestCase):
    def test_kpi_counts_helper_matches_records(self):
        records = [
            AuditRecord(
                timestamp=1.0,
                prompt="p1",
                plan=("a",),
                results=({"action_id": "a", "status": "executed"},),
                errors=(),
                observation=None,
            ),
            AuditRecord(
                timestamp=2.0,
                prompt="p2",
                plan=(),
                results=(),
                errors=(),
                observation=None,
            ),
        ]
        counts = kpi_counts(records)
        self.assertEqual(counts["prompts"], 2)
        self.assertEqual(counts["executed"], 1)
        self.assertEqual(counts["misses"], 1)

    def test_refresh_history_updates_kpi_labels(self):
        controller = _StubController()
        import io
        sink = io.StringIO()
        controller.audit_log = AgentAuditLog(sink=sink)
        controller.audit_log.record(
            prompt="p",
            plan=["run_all"],
            rationales=["because"],
            results=[{"action_id": "run_all", "status": "executed", "detail": "", "targets": []}],
            errors=[],
            observation=None,
        )
        panel = AgentPanel(controller, theme=THEMES["light"])
        panel.refresh_history()
        self.assertEqual(panel._kpi_cards["prompts"].text(), "1")
        self.assertEqual(panel._kpi_cards["executed"].text(), "1")
        self.assertEqual(panel._kpi_cards["rejected"].text(), "0")


class AgentPanelThemeIntegrationTests(unittest.TestCase):
    def test_dark_theme_uses_new_tokens(self):
        panel = AgentPanel(_StubController(), theme=THEMES["light"])
        panel.apply_theme(THEMES["dark"])
        sheet = panel.styleSheet()
        self.assertIn("agentHeader", sheet)
        self.assertIn("agentStatusBadge", sheet)
        self.assertIn("agentKpiCard", sheet)
        self.assertIn(THEMES["dark"]["panel_bg"], sheet)
        self.assertEqual(panel._theme["agent_user_bubble"], THEMES["dark"]["agent_user_bubble"])
        self.assertEqual(panel._theme["agent_agent_bubble"], THEMES["dark"]["agent_agent_bubble"])

    def test_high_contrast_theme_renders_without_errors(self):
        panel = AgentPanel(_StubController(), theme=THEMES["high_contrast"])
        sheet = panel.styleSheet()
        # High contrast tokens flow through the merged theme dict, not the sheet.
        self.assertEqual(
            panel._theme["agent_user_bubble"],
            THEMES["high_contrast"]["agent_user_bubble"],
        )
        self.assertIn("agentKpiCard", sheet)


if __name__ == "__main__":
    unittest.main()
