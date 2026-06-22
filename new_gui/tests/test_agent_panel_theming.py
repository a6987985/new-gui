"""Regression tests for theme-aware behavior of the Executable Agent panel."""

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

from new_gui.application.agent.agent_audit_reader import AuditRecord
from new_gui.presentation.views.widgets.agent_panel import (
    AgentPanel,
    _coalesce_theme,
    _format_timestamp,
    _PromptLineEdit,
    format_audit_records,
)
from new_gui.shared.config.settings import THEMES


_APP = QApplication.instance() or QApplication(sys.argv)


class _StubController:
    """Minimal stand-in for AgentController used by AgentPanel construction."""

    audit_log = None

    def submit_prompt(self, prompt):  # pragma: no cover - not exercised here
        raise NotImplementedError


def _record(timestamp, prompt="run all"):
    return AuditRecord(
        timestamp=timestamp,
        prompt=prompt,
        plan=("run_all",),
        results=(
            {"action_id": "run_all", "status": "executed", "detail": "", "targets": []},
        ),
        errors=(),
        observation={"diff": {"status_delta": {"success": 1}}},
    )


class CoalesceThemeTests(unittest.TestCase):
    def test_defaults_fill_missing_keys(self):
        merged = _coalesce_theme(None)
        self.assertIn("text_color", merged)
        self.assertEqual(merged["text_color"], "#333333")

    def test_overrides_take_precedence(self):
        merged = _coalesce_theme({"text_color": "#abcdef"})
        self.assertEqual(merged["text_color"], "#abcdef")


class FormatTimestampTests(unittest.TestCase):
    def test_unix_seconds_become_human_readable(self):
        rendered = _format_timestamp(0)
        self.assertRegex(rendered, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_invalid_value_falls_back_to_repr(self):
        rendered = _format_timestamp("not a number")
        self.assertEqual(rendered, "not a number")


class FormatAuditRecordsOrderingTests(unittest.TestCase):
    def test_records_are_emitted_newest_first(self):
        text = format_audit_records([_record(100.0, "first"), _record(200.0, "second")])
        idx_first = text.index("'first'")
        idx_second = text.index("'second'")
        self.assertLess(idx_second, idx_first)

    def test_timestamp_is_rendered_as_human_string(self):
        text = format_audit_records([_record(0.0)])
        self.assertNotIn("[0]", text)
        self.assertRegex(text, r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]")


class PromptLineEditHistoryTests(unittest.TestCase):
    def _press(self, edit, key):
        event = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
        edit.keyPressEvent(event)

    def test_up_arrow_recalls_latest_then_older_entries(self):
        edit = _PromptLineEdit()
        edit.record_submission("first prompt")
        edit.record_submission("second prompt")
        edit.setText("draft")
        self._press(edit, Qt.Key_Up)
        self.assertEqual(edit.text(), "second prompt")
        self._press(edit, Qt.Key_Up)
        self.assertEqual(edit.text(), "first prompt")
        self._press(edit, Qt.Key_Down)
        self.assertEqual(edit.text(), "second prompt")
        self._press(edit, Qt.Key_Down)
        # Past newest entry: restore the pending draft.
        self.assertEqual(edit.text(), "draft")

    def test_duplicate_consecutive_entries_are_deduplicated(self):
        edit = _PromptLineEdit()
        edit.record_submission("only")
        edit.record_submission("only")
        self.assertEqual(edit.history_snapshot(), ["only"])


class AgentPanelThemingTests(unittest.TestCase):
    def test_apply_theme_emits_dark_colors_for_known_widgets(self):
        panel = AgentPanel(_StubController(), theme=THEMES["light"])
        panel.apply_theme(THEMES["dark"])
        sheet = panel.styleSheet()
        self.assertIn("agentHeader", sheet)
        self.assertIn(THEMES["dark"]["text_color"], sheet)
        self.assertIn(THEMES["dark"]["panel_bg"], sheet)

    def test_apply_theme_handles_none_input(self):
        panel = AgentPanel(_StubController())
        panel.apply_theme(None)
        sheet = panel.styleSheet()
        self.assertIn("agentHeader", sheet)


if __name__ == "__main__":
    unittest.main()
