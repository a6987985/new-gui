"""Agent panel widget displayed in a side dock of the MainWindow.

The panel exposes:

* A compact header with title, status badge, and a clear-transcript control.
* A chat tab with a multi-line prompt input and a bubble-styled transcript
  rendered as HTML so each user, plan, result, observation, and error
  segment is visually distinct.
* A history tab with KPI cards and a scrollable audit log.

The widget is theme-aware; callers should invoke :meth:`apply_theme`
whenever the active theme changes so colors stay legible on the supported
light, dark, and high-contrast palettes.
"""

from __future__ import annotations

import html
import time
from typing import Iterable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QKeyEvent, QTextCursor
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from new_gui.application.agent.agent_audit_reader import (
    AuditRecord,
    load_audit_file,
    summarize_records,
)
from new_gui.presentation.presenters.agent_controller import (
    AgentController,
    AgentInteractionRecord,
)


DEFAULT_THEME = {
    "panel_bg": "#f8f9fa",
    "text_color": "#333333",
    "border_color": "#e0e0e0",
    "accent_color": "#1976d2",
    "menu_bg": "#ffffff",
    "menu_hover": "#e3f2fd",
    "hint_color": "#666666",
    "muted_color": "#777777",
    "agent_user_bubble": "#e3f2fd",
    "agent_user_border": "#90caf9",
    "agent_agent_bubble": "#ffffff",
    "agent_agent_border": "#d0d7de",
    "agent_hint_bg": "#fff8e1",
    "agent_hint_border": "#ffe082",
    "success_color": "#2e7d32",
    "danger_color": "#c62828",
    "info_color": "#0277bd",
}


def _coalesce_theme(theme):
    """Return a theme dict merged onto safe defaults."""
    merged = dict(DEFAULT_THEME)
    if theme:
        for key, value in theme.items():
            if value is not None:
                merged[key] = value
    merged.setdefault("hint_color", merged.get("text_color", DEFAULT_THEME["text_color"]))
    merged.setdefault("muted_color", merged.get("text_color", DEFAULT_THEME["text_color"]))
    merged.setdefault("agent_user_bubble", merged.get("menu_hover", DEFAULT_THEME["agent_user_bubble"]))
    merged.setdefault("agent_user_border", merged.get("accent_color", DEFAULT_THEME["agent_user_border"]))
    merged.setdefault("agent_agent_bubble", merged.get("menu_bg", DEFAULT_THEME["agent_agent_bubble"]))
    merged.setdefault("agent_agent_border", merged.get("border_color", DEFAULT_THEME["agent_agent_border"]))
    merged.setdefault("agent_hint_bg", merged.get("menu_hover", DEFAULT_THEME["agent_hint_bg"]))
    merged.setdefault("agent_hint_border", merged.get("border_color", DEFAULT_THEME["agent_hint_border"]))
    merged.setdefault("success_color", DEFAULT_THEME["success_color"])
    merged.setdefault("danger_color", DEFAULT_THEME["danger_color"])
    merged.setdefault("info_color", DEFAULT_THEME["info_color"])
    return merged


def _format_timestamp(value):
    """Render a Unix timestamp as local YYYY-MM-DD HH:MM:SS."""
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(value)))
    except (TypeError, ValueError, OverflowError, OSError):
        return str(value)


def _monospace_font():
    """Return the platform's default monospace font."""
    return QFontDatabase.systemFont(QFontDatabase.FixedFont)


def format_audit_summary(records: Iterable[AuditRecord]) -> str:
    """Render aggregated audit metrics as plain text for the history tab."""
    summary = summarize_records(records)
    actions_section = ", ".join(
        f"{name}={count}" for name, count in sorted(summary["actions_by_id"].items())
    ) or "(none)"
    return (
        f"Prompts: {summary['total_prompts']}\n"
        f"Actions attempted: {summary['total_actions']}\n"
        f"  executed: {summary['executed']}\n"
        f"  rejected: {summary['rejected']}\n"
        f"  planner misses: {summary['planner_misses']}\n"
        f"Actions by id: {actions_section}"
    )


def format_audit_records(records: Iterable[AuditRecord], limit: int = 50) -> str:
    """Render audit records (newest first) as a readable log."""
    materialized = list(records)
    tail = materialized[-limit:]
    lines: List[str] = []
    for record in reversed(tail):
        statuses = ", ".join(
            f"{entry.get('action_id', '?')}={entry.get('status', '?')}"
            for entry in record.results
        ) or "(no result)"
        diff = ""
        observation = record.observation or {}
        observation_diff = observation.get("diff") if isinstance(observation, dict) else None
        if isinstance(observation_diff, dict):
            status_delta = observation_diff.get("status_delta") or {}
            if status_delta:
                diff = " | delta: " + ", ".join(
                    f"{name}{value:+d}" for name, value in status_delta.items()
                )
        lines.append(
            f"[{_format_timestamp(record.timestamp)}] {record.prompt!r} -> {statuses}{diff}"
        )
        for error in record.errors:
            lines.append(f"    error: {error}")
    return "\n".join(lines) if lines else "(no audit records yet)"


def kpi_counts(records: Iterable[AuditRecord]) -> dict:
    """Return KPI numbers used by the history tab."""
    summary = summarize_records(records)
    return {
        "prompts": summary["total_prompts"],
        "executed": summary["executed"],
        "rejected": summary["rejected"],
        "misses": summary["planner_misses"],
    }


class _PromptLineEdit(QLineEdit):
    """Legacy single-line prompt input retained for backwards compatibility."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._history: List[str] = []
        self._cursor: Optional[int] = None
        self._pending_draft: str = ""

    def record_submission(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._cursor = None
        self._pending_draft = ""

    def history_snapshot(self) -> List[str]:
        return list(self._history)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key_Up and self._history:
            if self._cursor is None:
                self._pending_draft = self.text()
                self._cursor = len(self._history) - 1
            elif self._cursor > 0:
                self._cursor -= 1
            self.setText(self._history[self._cursor])
            return
        if event.key() == Qt.Key_Down and self._cursor is not None:
            if self._cursor < len(self._history) - 1:
                self._cursor += 1
                self.setText(self._history[self._cursor])
            else:
                self._cursor = None
                self.setText(self._pending_draft)
            return
        super().keyPressEvent(event)


class _PromptTextEdit(QPlainTextEdit):
    """Multi-line prompt input with history navigation and submit-on-Enter.

    Behavior:

    * Plain ``Enter`` submits the prompt via the supplied submit callback.
    * ``Shift+Enter`` (or ``Ctrl+Enter``) inserts a newline.
    * ``Ctrl+Up`` / ``Ctrl+Down`` walk the prompt history.
    """

    def __init__(self, submit_callback, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._submit_callback = submit_callback
        self._history: List[str] = []
        self._cursor_index: Optional[int] = None
        self._pending_draft: str = ""
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)

    def record_submission(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._cursor_index = None
        self._pending_draft = ""

    def history_snapshot(self) -> List[str]:
        return list(self._history)

    def _set_text_at_end(self, text: str) -> None:
        self.setPlainText(text)
        self.moveCursor(QTextCursor.End)

    def _walk_history(self, direction: int) -> bool:
        if not self._history:
            return False
        if direction < 0:
            if self._cursor_index is None:
                self._pending_draft = self.toPlainText()
                self._cursor_index = len(self._history) - 1
            elif self._cursor_index > 0:
                self._cursor_index -= 1
            else:
                return True
            self._set_text_at_end(self._history[self._cursor_index])
            return True
        if self._cursor_index is None:
            return False
        if self._cursor_index < len(self._history) - 1:
            self._cursor_index += 1
            self._set_text_at_end(self._history[self._cursor_index])
        else:
            self._cursor_index = None
            self._set_text_at_end(self._pending_draft)
        return True

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        mods = event.modifiers()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if mods & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier):
                super().keyPressEvent(event)
                return
            if callable(self._submit_callback):
                self._submit_callback()
            return
        if mods & Qt.ControlModifier and key == Qt.Key_Up:
            if self._walk_history(-1):
                return
        if mods & Qt.ControlModifier and key == Qt.Key_Down:
            if self._walk_history(1):
                return
        super().keyPressEvent(event)


class AgentPanel(QWidget):
    """Refined Agent console: header + chat tab + history tab."""

    HEADER_LABEL = "Executable Agent"
    SUBTITLE_LABEL = "Plan, confirm, run \u2014 every step audited."
    TRANSCRIPT_PLACEHOLDER = (
        "Send a prompt above to begin. Plans, results, and rejections appear here."
    )
    HINT_TEXT = (
        "Try: \u201Crun all\u201D, \u201Copen log\u201D, \u201Ctrace up\u201D. "
        "Only Registered GUI Actions can run; State-Changing actions ask for confirmation."
    )

    STATUS_IDLE = "idle"
    STATUS_BUSY = "busy"
    STATUS_OK = "ok"
    STATUS_FAIL = "fail"

    def __init__(
        self,
        controller: AgentController,
        *,
        parent: Optional[QWidget] = None,
        audit_path: Optional[str] = None,
        theme: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("agentPanel")
        self._controller = controller
        self._audit_path = audit_path
        self._theme = _coalesce_theme(theme)
        self._status_state = self.STATUS_IDLE
        self._build_ui()
        self.apply_theme(self._theme)

    # ------------------------------------------------------------ Layout

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        outer.addWidget(self._build_header())
        outer.addWidget(self._build_hint_card())

        self._tabs = QTabWidget()
        self._tabs.setObjectName("agentTabs")
        self._tabs.addTab(self._build_chat_tab(), "Chat")
        self._tabs.addTab(self._build_history_tab(), "History")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(self._tabs, 1)

        outer.addWidget(self._build_footer())
        self.setLayout(outer)

    def _build_header(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("agentHeaderFrame")
        wrapper.setFrameShape(QFrame.NoFrame)

        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(0)

        self._header_label = QLabel(self.HEADER_LABEL)
        self._header_label.setObjectName("agentHeader")
        title_block.addWidget(self._header_label)

        self._subtitle_label = QLabel(self.SUBTITLE_LABEL)
        self._subtitle_label.setObjectName("agentSubtitle")
        title_block.addWidget(self._subtitle_label)

        row.addLayout(title_block, 1)

        self._status_badge = QLabel("Idle")
        self._status_badge.setObjectName("agentStatusBadge")
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setProperty("agentStatus", self._status_state)
        row.addWidget(self._status_badge)

        self._clear_button = QPushButton("Clear")
        self._clear_button.setObjectName("agentClearButton")
        self._clear_button.setToolTip("Clear transcript")
        self._clear_button.clicked.connect(self.clear_transcript)
        row.addWidget(self._clear_button)

        return wrapper

    def _build_hint_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("agentHintCard")
        card.setFrameShape(QFrame.NoFrame)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)

        self._hint_label = QLabel(self.HINT_TEXT)
        self._hint_label.setObjectName("agentHint")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)
        return card

    def _build_chat_tab(self) -> QWidget:
        container = QWidget()
        container.setObjectName("agentChatTab")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self._transcript = QTextBrowser()
        self._transcript.setObjectName("agentTranscript")
        self._transcript.setOpenExternalLinks(False)
        self._transcript.setOpenLinks(False)
        self._transcript.setReadOnly(True)
        self._transcript.setPlaceholderText(self.TRANSCRIPT_PLACEHOLDER)
        self._transcript.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._transcript, 1)

        prompt_row = QFrame()
        prompt_row.setObjectName("agentPromptRow")
        prompt_layout = QHBoxLayout(prompt_row)
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.setSpacing(6)

        self._prompt_edit = _PromptTextEdit(submit_callback=self._on_submit_clicked)
        self._prompt_edit.setObjectName("agentPrompt")
        self._prompt_edit.setPlaceholderText(
            "Ask the agent\u2026 (Enter to send, Shift+Enter for newline, Ctrl+\u2191/\u2193 for history)"
        )
        self._prompt_edit.setMinimumHeight(60)
        self._prompt_edit.setMaximumHeight(120)
        prompt_layout.addWidget(self._prompt_edit, 1)

        button_block = QVBoxLayout()
        button_block.setContentsMargins(0, 0, 0, 0)
        button_block.setSpacing(4)
        self._submit_button = QPushButton("Send")
        self._submit_button.setObjectName("agentSendButton")
        self._submit_button.setDefault(True)
        self._submit_button.clicked.connect(self._on_submit_clicked)
        button_block.addWidget(self._submit_button)
        button_block.addStretch(1)
        prompt_layout.addLayout(button_block)

        layout.addWidget(prompt_row)

        self._prompt_hint = QLabel(
            "Enter to send  ·  Shift+Enter newline  ·  Ctrl+↑/↓ history"
        )
        self._prompt_hint.setObjectName("agentPromptHint")
        self._prompt_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._prompt_hint)
        return container

    def _build_history_tab(self) -> QWidget:
        container = QWidget()
        container.setObjectName("agentHistoryTab")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # KPI grid
        kpi_frame = QFrame()
        kpi_frame.setObjectName("agentKpiRow")
        kpi_layout = QGridLayout(kpi_frame)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setHorizontalSpacing(8)
        kpi_layout.setVerticalSpacing(4)
        self._kpi_cards = {}
        kpi_specs = [
            ("prompts", "Prompts", "neutral"),
            ("executed", "Executed", "success"),
            ("rejected", "Rejected", "danger"),
            ("misses", "Misses", "muted"),
        ]
        for col, (key, label, kind) in enumerate(kpi_specs):
            card, value_label = self._make_kpi_card(label, kind=kind)
            kpi_layout.addWidget(card, 0, col)
            self._kpi_cards[key] = value_label
        layout.addWidget(kpi_frame)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.setObjectName("agentRefreshButton")
        self._refresh_button.clicked.connect(self.refresh_history)
        action_row.addWidget(self._refresh_button)
        layout.addLayout(action_row)

        self._summary_label = QLabel("(load history to see metrics)")
        self._summary_label.setObjectName("agentHistorySummary")
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        self._history_view = QTextEdit()
        self._history_view.setObjectName("agentHistoryView")
        self._history_view.setReadOnly(True)
        self._history_view.setLineWrapMode(QTextEdit.WidgetWidth)
        self._history_view.setFont(_monospace_font())
        self._history_view.setPlaceholderText("(no audit records yet)")
        layout.addWidget(self._history_view, 1)
        return container

    def _make_kpi_card(self, label_text: str, kind: str = "neutral"):
        card = QFrame()
        card.setObjectName("agentKpiCard")
        card.setFrameShape(QFrame.NoFrame)
        card.setProperty("kpiKind", kind)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        value_label = QLabel("0")
        value_label.setObjectName("agentKpiValue")
        value_label.setProperty("kpiKind", kind)
        value_label.setAlignment(Qt.AlignCenter)
        caption = QLabel(label_text)
        caption.setObjectName("agentKpiCaption")
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        layout.addWidget(caption)
        return card, value_label

    def _build_footer(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("agentFooter")
        wrapper.setFrameShape(QFrame.NoFrame)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._footer_status = QLabel("Ready")
        self._footer_status.setObjectName("agentFooterStatus")
        layout.addWidget(self._footer_status, 1)
        return wrapper


    # ------------------------------------------------------------ Events

    def _on_submit_clicked(self) -> None:
        prompt = self._prompt_edit.toPlainText().strip()
        if not prompt:
            return
        self._set_busy(True)
        self._set_status(self.STATUS_BUSY, "Running\u2026")
        try:
            try:
                record = self._controller.submit_prompt(prompt)
            except Exception as exc:  # defensive: surface failures in UI
                self._append_user_bubble(prompt)
                self._append_error_bubble(f"Controller error: {exc!r}")
                self._prompt_edit.record_submission(prompt)
                self._prompt_edit.clear()
                self._set_status(self.STATUS_FAIL, "Last prompt errored")
                return
            self._append_user_bubble(prompt)
            self._append_record_bubbles(record)
            self._prompt_edit.record_submission(prompt)
            self._prompt_edit.clear()
            self._set_status(*self._summarize_status(record))
        finally:
            self._set_busy(False)
            self._prompt_edit.setFocus(Qt.OtherFocusReason)

    def _on_tab_changed(self, index: int) -> None:
        if self._tabs.tabText(index) == "History":
            self.refresh_history()

    def refresh_history(self) -> None:
        records = self._load_records()
        self._summary_label.setText(format_audit_summary(records))
        self._history_view.setPlainText(format_audit_records(records))
        counts = kpi_counts(records)
        for key, value_label in self._kpi_cards.items():
            value_label.setText(str(counts.get(key, 0)))

    def on_dock_shown(self) -> None:
        """Refresh data when the dock becomes visible again."""
        try:
            if self._tabs.tabText(self._tabs.currentIndex()) == "History":
                self.refresh_history()
        except Exception:
            pass

    def focus_prompt(self) -> None:
        self._prompt_edit.setFocus(Qt.OtherFocusReason)

    def clear_transcript(self) -> None:
        """Clear the transcript pane and reset the status footer."""
        self._transcript.clear()
        self._set_status(self.STATUS_IDLE, "Ready")

    def _set_busy(self, busy: bool) -> None:
        self._submit_button.setEnabled(not busy)
        self._submit_button.setText("Sending\u2026" if busy else "Send")
        self._prompt_edit.setEnabled(not busy)

    def _set_status(self, state: str, text: str) -> None:
        self._status_state = state
        label_text = {
            self.STATUS_IDLE: "○ Idle",
            self.STATUS_BUSY: "◔ Busy",
            self.STATUS_OK: "● Ready",
            self.STATUS_FAIL: "● Alert",
        }.get(state, "○ Idle")
        self._status_badge.setText(label_text)
        self._status_badge.setProperty("agentStatus", state)
        # Re-polish to pick up the new property selector
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)
        self._footer_status.setText(text)

    def _summarize_status(self, record: AgentInteractionRecord):
        if record.errors:
            return (
                self.STATUS_FAIL,
                f"Last prompt: {len(record.errors)} error(s)",
            )
        if not record.steps:
            return (self.STATUS_FAIL, "Planner produced no actionable steps")
        executed = sum(
            1 for r in record.results if getattr(r, "status", "") == "executed"
        )
        rejected = sum(
            1 for r in record.results if getattr(r, "status", "") == "rejected"
        )
        if executed and not rejected:
            return (self.STATUS_OK, f"Executed {executed} action(s)")
        if rejected and not executed:
            return (self.STATUS_FAIL, f"Rejected {rejected} action(s)")
        return (
            self.STATUS_OK,
            f"Executed {executed}, rejected {rejected}",
        )

    # ------------------------------------------------------------ Loader

    def _load_records(self):
        if self._audit_path:
            return load_audit_file(self._audit_path)
        in_memory = self._controller.audit_log
        if in_memory is None:
            return []
        return [
            AuditRecord(
                timestamp=entry.timestamp,
                prompt=entry.prompt,
                plan=tuple(entry.plan),
                results=tuple(entry.results),
                errors=tuple(entry.errors),
                observation=dict(entry.observation) if entry.observation else None,
            )
            for entry in in_memory.entries
        ]

    # ------------------------------------------------------------ HTML rendering

    def _append_html_block(self, html_block: str) -> None:
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html_block)
        self._transcript.setTextCursor(cursor)
        self._transcript.ensureCursorVisible()

    def _append_plain_lines(self, lines: Iterable[str]) -> None:
        """Append plain lines (kept for compatibility with older callers)."""
        items = list(lines)
        if not items:
            return
        escaped = [html.escape(line) for line in items]
        block = (
            "<div style=\"margin:4px 0; font-family:monospace;\">"
            + "<br/>".join(escaped)
            + "</div>"
        )
        self._append_html_block(block)

    def _bubble(self, role: str, title: str, body_lines: List[str]) -> str:
        merged = self._theme
        role_colors = {
            "user": (merged["agent_user_bubble"], merged["agent_user_border"]),
            "agent": (merged["agent_agent_bubble"], merged["agent_agent_border"]),
            "error": (
                self._mix_with_panel(merged["danger_color"], merged["panel_bg"]),
                merged["danger_color"],
            ),
            "info": (
                self._mix_with_panel(merged["info_color"], merged["panel_bg"]),
                merged["info_color"],
            ),
        }
        bg, border = role_colors.get(role, role_colors["agent"])
        text_color = merged["text_color"]
        align = "right" if role == "user" else "left"
        margin_side = "margin-left:40px;" if role == "user" else "margin-right:40px;"
        body_html = "<br/>".join(html.escape(line) for line in body_lines if line)
        return (
            f"<table style=\"margin:6px 0; width:100%;\" cellspacing=\"0\" cellpadding=\"0\">"
            f"<tr><td align=\"{align}\">"
            f"<div style=\"display:inline-block; max-width:90%;"
            f" background:{bg}; color:{text_color};"
            f" border:1px solid {border}; border-radius:8px;"
            f" padding:6px 10px; {margin_side}\">"
            f"<div style=\"font-size:10px; opacity:0.7; margin-bottom:2px;\">"
            f"{html.escape(title)}</div>"
            f"<div style=\"font-family:monospace; font-size:12px;\">{body_html}</div>"
            f"</div></td></tr></table>"
        )

    def _append_user_bubble(self, prompt: str) -> None:
        self._append_html_block(self._bubble("user", "You", [prompt]))

    def _append_error_bubble(self, message: str) -> None:
        self._append_html_block(self._bubble("error", "Error", [message]))

    def _append_record_bubbles(self, record: AgentInteractionRecord) -> None:
        plan_lines: List[str] = []
        if not record.steps:
            plan_lines.append("(no matching Registered GUI Action)")
        for step in record.steps:
            plan_lines.append(f"{step.action_id} \u2014 {step.rationale}")

        result_lines: List[str] = []
        for result in record.results:
            extra = f" targets={list(result.targets)}" if result.targets else ""
            detail = f" ({result.detail})" if result.detail else ""
            result_lines.append(
                f"{result.action_id}: {result.status}{detail}{extra}"
            )

        if plan_lines:
            self._append_html_block(self._bubble("agent", "Plan", plan_lines))
        if result_lines:
            self._append_html_block(self._bubble("agent", "Result", result_lines))

        if record.errors:
            self._append_html_block(
                self._bubble("error", "Errors", list(record.errors))
            )

        diff = record.observation_diff
        if diff is not None and not diff.is_empty():
            diff_lines: List[str] = []
            if diff.status_delta:
                diff_lines.append(
                    "Status: "
                    + ", ".join(
                        f"{name}{change:+d}" for name, change in diff.status_delta.items()
                    )
                )
            if diff.selection_added:
                diff_lines.append(f"Selection +{list(diff.selection_added)}")
            if diff.selection_removed:
                diff_lines.append(f"Selection -{list(diff.selection_removed)}")
            if diff.run_changed:
                diff_lines.append("Active run changed")
            if diff_lines:
                self._append_html_block(self._bubble("info", "Observed", diff_lines))

    @staticmethod
    def _mix_with_panel(accent: str, panel: str) -> str:
        """Return a soft tint by mixing an accent color with the panel bg."""

        def _channels(value: str):
            value = value.strip().lstrip("#")
            if len(value) == 3:
                value = "".join(ch * 2 for ch in value)
            if len(value) != 6:
                return None
            try:
                return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                return None

        a = _channels(accent)
        b = _channels(panel)
        if a is None or b is None:
            return panel
        mix = tuple(int(b[i] * 0.82 + a[i] * 0.18) for i in range(3))
        return "#" + "".join(f"{c:02x}" for c in mix)


    # ------------------------------------------------------------ Theme

    def apply_theme(self, theme: Optional[dict]) -> None:
        """Apply a theme dictionary to all widgets owned by this panel."""
        merged = _coalesce_theme(theme)
        self._theme = merged

        text = merged["text_color"]
        bg = merged["panel_bg"]
        menu_bg = merged["menu_bg"]
        hover = merged["menu_hover"]
        accent = merged["accent_color"]
        border = merged["border_color"]
        hint = merged.get("hint_color") or text
        muted = merged.get("muted_color") or text
        success = merged["success_color"]
        danger = merged["danger_color"]
        info = merged["info_color"]
        user_bubble = merged["agent_user_bubble"]
        agent_bubble = merged["agent_agent_bubble"]
        hint_bg = merged["agent_hint_bg"]
        hint_border = merged["agent_hint_border"]

        stylesheet = (
            f"QWidget#agentPanel {{ background-color: {bg}; }}"
            f"QWidget#agentChatTab, QWidget#agentHistoryTab {{ background-color: {bg}; }}"
            # Header
            f"QLabel#agentHeader {{"
            f" color: {text}; font-weight: 600; font-size: 14px;"
            f" padding: 0px; }}"
            f"QLabel#agentSubtitle {{"
            f" color: {muted}; font-size: 11px; padding: 0px 0px 2px 0px; }}"
            # Status badge with property selectors
            f"QLabel#agentStatusBadge {{"
            f" color: {text}; background-color: {menu_bg};"
            f" border: 1px solid {border}; border-radius: 10px;"
            f" padding: 2px 10px; font-size: 11px; min-width: 48px; }}"
            f"QLabel#agentStatusBadge[agentStatus=\"idle\"] {{"
            f" color: {muted}; background-color: {menu_bg};"
            f" border: 1px solid {border}; }}"
            f"QLabel#agentStatusBadge[agentStatus=\"busy\"] {{"
            f" color: {info}; background-color: {self._mix_with_panel(info, bg)};"
            f" border: 1px solid {info}; }}"
            f"QLabel#agentStatusBadge[agentStatus=\"ok\"] {{"
            f" color: {success}; background-color: {self._mix_with_panel(success, bg)};"
            f" border: 1px solid {success}; }}"
            f"QLabel#agentStatusBadge[agentStatus=\"fail\"] {{"
            f" color: {danger}; background-color: {self._mix_with_panel(danger, bg)};"
            f" border: 1px solid {danger}; }}"
            # Hint card
            f"QFrame#agentHintCard {{"
            f" background-color: {hint_bg}; border: 1px solid {hint_border};"
            f" border-radius: 6px; }}"
            f"QLabel#agentHint {{ color: {hint}; font-size: 11px; }}"
            f"QLabel#agentHistorySummary {{ color: {muted}; }}"
            # KPI cards
            f"QFrame#agentKpiCard {{"
            f" background-color: {menu_bg}; border: 1px solid {border};"
            f" border-radius: 6px; }}"
            f"QLabel#agentKpiValue {{"
            f" color: {accent}; font-size: 18px; font-weight: 600; }}"
            f"QLabel#agentKpiValue[kpiKind=\"success\"] {{ color: {success}; }}"
            f"QLabel#agentKpiValue[kpiKind=\"danger\"] {{ color: {danger}; }}"
            f"QLabel#agentKpiValue[kpiKind=\"muted\"] {{ color: {muted}; }}"
            f"QLabel#agentKpiCaption {{ color: {muted}; font-size: 10px; }}"
            # Prompt input (text edit)
            f"QPlainTextEdit#agentPrompt {{"
            f" color: {text}; background-color: {menu_bg};"
            f" border: 1px solid {border}; border-radius: 6px;"
            f" padding: 6px 8px; }}"
            f"QPlainTextEdit#agentPrompt:focus {{ border: 1px solid {accent}; }}"
            f"QPlainTextEdit#agentPrompt:disabled {{"
            f" color: {muted}; background-color: {bg}; }}"
            # Legacy single-line prompt fallback
            f"QLineEdit#agentPrompt {{"
            f" color: {text}; background-color: {menu_bg};"
            f" border: 1px solid {border}; border-radius: 4px;"
            f" padding: 4px 6px; }}"
            f"QLineEdit#agentPrompt:focus {{ border: 1px solid {accent}; }}"
            # Buttons
            f"QPushButton#agentSendButton, QPushButton#agentRefreshButton,"
            f" QPushButton#agentClearButton {{"
            f" color: {text}; background-color: {menu_bg};"
            f" border: 1px solid {border}; border-radius: 6px;"
            f" padding: 5px 12px; }}"
            f"QPushButton#agentSendButton:hover,"
            f" QPushButton#agentRefreshButton:hover,"
            f" QPushButton#agentClearButton:hover {{ background-color: {hover}; }}"
            f"QPushButton#agentSendButton:disabled {{"
            f" color: {muted}; background-color: {bg}; }}"
            f"QPushButton#agentSendButton:default {{"
            f" border: 1px solid {accent}; color: {accent}; font-weight: 600; }}"
            # Transcript / history text views
            f"QTextBrowser#agentTranscript {{"
            f" color: {text}; background-color: {agent_bubble};"
            f" border: 1px solid {border}; border-radius: 6px;"
            f" padding: 4px; }}"
            f"QTextEdit#agentHistoryView {{"
            f" color: {text}; background-color: {menu_bg};"
            f" border: 1px solid {border}; border-radius: 6px; }}"
            # Tabs
            f"QTabWidget#agentTabs::pane {{"
            f" border: 1px solid {border}; background: {bg};"
            f" border-radius: 6px; top: -1px; }}"
            f"QTabBar::tab {{"
            f" color: {muted}; background: transparent;"
            f" border: 1px solid transparent; padding: 4px 14px;"
            f" margin-right: 2px; border-top-left-radius: 6px;"
            f" border-top-right-radius: 6px; }}"
            f"QTabBar::tab:hover {{ color: {text}; }}"
            f"QTabBar::tab:selected {{"
            f" color: {accent}; background: {menu_bg};"
            f" border: 1px solid {border}; border-bottom-color: {menu_bg}; }}"
            # Prompt hint
            f"QLabel#agentPromptHint {{ color: {muted}; font-size: 10px;"
            f" padding: 2px 4px; }}"
            # Footer
            f"QFrame#agentFooter {{ background: transparent; }}"
            f"QLabel#agentFooterStatus {{ color: {muted}; font-size: 11px; }}"
        )
        self.setStyleSheet(stylesheet)
