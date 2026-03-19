"""Bottom output panel widgets for terminal and session log."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from PyQt5.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from new_gui.ui.icon_factory import build_terminal_follow_run_icon
from new_gui.ui.output_panel_styles import (
    build_bottom_output_corner_style,
    build_bottom_output_panel_style,
    build_bottom_output_tab_style,
    build_session_log_document_style,
    build_session_log_style,
)
from new_gui.ui.widgets.embedded_terminal import EmbeddedTerminalWidget


@dataclass
class GuiLogEntry:
    """Represent one GUI-visible session log event."""

    timestamp: str
    level: str
    source: str
    message: str
    command: str = ""
    details: str = ""

    @classmethod
    def create(
        cls,
        level: str,
        source: str,
        message: str,
        command: str = "",
        details: str = "",
        timestamp: Optional[str] = None,
    ) -> "GuiLogEntry":
        """Create a log entry with a default current timestamp."""
        return cls(
            timestamp=timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level=(level or "INFO").upper(),
            source=(source or "system").lower(),
            message=message or "",
            command=command or "",
            details=details or "",
        )

    @classmethod
    def from_logging_record(cls, record: logging.LogRecord) -> "GuiLogEntry":
        """Build a GUI log entry from a Python logging record."""
        return cls.create(
            level=record.levelname,
            source=getattr(record, "ui_source", "system"),
            message=record.getMessage(),
            command=getattr(record, "ui_command", ""),
            details=getattr(record, "ui_details", ""),
            timestamp=datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
        )


class GuiLogSignalBridge(QObject):
    """Bridge session log events safely back to the GUI thread."""

    entry_requested = pyqtSignal(object)


class GuiLogHandler(logging.Handler):
    """Forward Python logging records into the GUI session log."""

    def __init__(self, emit_entry: Callable[[GuiLogEntry], None]):
        super().__init__(level=logging.INFO)
        self._emit_entry = emit_entry

    def emit(self, record: logging.LogRecord) -> None:
        """Emit one converted logging record to the GUI sink."""
        if record.levelno < logging.INFO or getattr(record, "ui_skip", False):
            return

        try:
            self._emit_entry(GuiLogEntry.from_logging_record(record))
        except Exception:
            self.handleError(record)


class SessionLogWidget(QWidget):
    """Read-only session log view with clear and close actions."""

    close_requested = pyqtSignal()

    _LEVEL_COLORS = {
        "INFO": "#4c7fb0",
        "WARNING": "#b7791f",
        "ERROR": "#c2410c",
        "CRITICAL": "#9f1239",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self.setObjectName("sessionLogWidget")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet(build_session_log_style())

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 7, 10, 9)
        root_layout.setSpacing(7)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("Session Log")
        title_label.setObjectName("sessionLogTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        clear_button = QPushButton("Clear")
        clear_button.setObjectName("sessionLogButton")
        clear_button.clicked.connect(self.clear_entries)
        header_layout.addWidget(clear_button)

        close_button = QPushButton("Close")
        close_button.setObjectName("sessionLogButton")
        close_button.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_button)

        root_layout.addLayout(header_layout)

        self._view = QTextBrowser()
        self._view.setObjectName("sessionLogView")
        self._view.setReadOnly(True)
        self._view.setOpenExternalLinks(False)
        self._view.document().setDefaultStyleSheet(build_session_log_document_style())
        root_layout.addWidget(self._view, 1)

    def append_entry(self, entry: GuiLogEntry) -> None:
        """Append one entry to the visible session log."""
        self._entries.append(entry)
        self._view.append(self._render_entry_html(entry))
        self._view.moveCursor(QTextCursor.End)
        self._view.ensureCursorVisible()

    def clear_entries(self) -> None:
        """Clear the in-memory session log and visible content."""
        self._entries.clear()
        self._view.clear()

    def entry_count(self) -> int:
        """Return the number of log entries kept in memory."""
        return len(self._entries)

    def _render_entry_html(self, entry: GuiLogEntry) -> str:
        """Render one entry as HTML for the QTextBrowser."""
        level_color = self._LEVEL_COLORS.get(entry.level, "#4a90d9")
        message = html.escape(entry.message)
        source = html.escape(entry.source.upper())
        timestamp = html.escape(entry.timestamp)

        blocks = [
            "<div class='entry'>",
            "<div class='meta'>",
            f"<span class='timestamp'>{timestamp}</span> ",
            f"<span style='color:{level_color}; font-weight:700;'>{html.escape(entry.level)}</span> ",
            f"<span class='source'>[{source}]</span>",
            "</div>",
            f"<div class='message'>{message}</div>",
        ]

        if entry.command:
            blocks.append("<div class='command-label'>Command</div>")
            blocks.append(f"<pre>{html.escape(entry.command)}</pre>")

        if entry.details:
            blocks.append("<div class='details-label'>Details</div>")
            blocks.append(f"<pre>{html.escape(entry.details)}</pre>")

        blocks.append("</div>")
        return "".join(blocks)


class BottomOutputPanel(QWidget):
    """IDE-style bottom output area with Terminal and Log tabs."""

    terminal_follow_run_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomOutputPanel")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumHeight(180)
        self.setStyleSheet(build_bottom_output_panel_style())

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)
        self._tabs.setStyleSheet(build_bottom_output_tab_style())

        self.terminal_widget = EmbeddedTerminalWidget(self)
        self.log_widget = SessionLogWidget(self)
        self._tabs.addTab(self.terminal_widget, "Terminal")
        self._tabs.addTab(self.log_widget, "Log")
        self._tabs.currentChanged.connect(self._sync_corner_controls)

        self._terminal_controls = QWidget(self)
        self._terminal_controls.setStyleSheet(build_bottom_output_corner_style())
        terminal_controls_layout = QHBoxLayout(self._terminal_controls)
        terminal_controls_layout.setContentsMargins(0, 8, 12, 0)
        terminal_controls_layout.setSpacing(8)

        self._terminal_follow_run_button = QToolButton(self._terminal_controls)
        self._terminal_follow_run_button.setObjectName("terminalFollowRunButton")
        self._terminal_follow_run_button.setCheckable(True)
        self._terminal_follow_run_button.setAutoRaise(False)
        self._terminal_follow_run_button.setFixedSize(30, 30)
        self._terminal_follow_run_button.setIcon(build_terminal_follow_run_icon())
        self._terminal_follow_run_button.setIconSize(QSize(16, 16))
        self._terminal_follow_run_button.toggled.connect(self._on_terminal_follow_run_toggled)
        terminal_controls_layout.addWidget(self._terminal_follow_run_button)

        restart_button = QPushButton("Restart")
        restart_button.setObjectName("bottomOutputActionButton")
        restart_button.clicked.connect(self.terminal_widget.restart_terminal)
        terminal_controls_layout.addWidget(restart_button)

        external_button = QPushButton("External")
        external_button.setObjectName("bottomOutputActionButton")
        external_button.clicked.connect(lambda: self.terminal_widget.external_requested.emit())
        terminal_controls_layout.addWidget(external_button)

        close_button = QPushButton("Close")
        close_button.setObjectName("bottomOutputActionButton")
        close_button.clicked.connect(lambda: self.terminal_widget.close_requested.emit())
        terminal_controls_layout.addWidget(close_button)

        self._tabs.setCornerWidget(self._terminal_controls, Qt.TopRightCorner)
        self._refresh_terminal_follow_run_tooltip()
        self._sync_corner_controls(self._tabs.currentIndex())

        root_layout.addWidget(self._tabs)

    def show_terminal_tab(self) -> None:
        """Switch to the embedded terminal tab."""
        self._tabs.setCurrentWidget(self.terminal_widget)

    def show_log_tab(self) -> None:
        """Switch to the session log tab."""
        self._tabs.setCurrentWidget(self.log_widget)

    def current_tab_name(self) -> str:
        """Return the visible tab label."""
        current_index = self._tabs.currentIndex()
        return self._tabs.tabText(current_index)

    def append_log_entry(self, entry: GuiLogEntry) -> None:
        """Append one entry to the log tab."""
        self.log_widget.append_entry(entry)

    def is_terminal_follow_run_enabled(self) -> bool:
        """Return whether terminal rundir follows run selection changes."""
        return self._terminal_follow_run_button.isChecked()

    def set_terminal_follow_run_enabled(self, enabled: bool) -> None:
        """Update the terminal follow-run toggle state."""
        self._terminal_follow_run_button.setChecked(bool(enabled))

    def _sync_corner_controls(self, current_index: int) -> None:
        """Show terminal actions only while the terminal tab is active."""
        current_widget = self._tabs.widget(current_index)
        self._terminal_controls.setVisible(current_widget is self.terminal_widget)

    def _on_terminal_follow_run_toggled(self, enabled: bool) -> None:
        """Update tooltip text and propagate follow-run state changes."""
        self._refresh_terminal_follow_run_tooltip()
        self.terminal_follow_run_changed.emit(bool(enabled))

    def _refresh_terminal_follow_run_tooltip(self) -> None:
        """Update the tooltip for the terminal follow-run toggle."""
        if self._terminal_follow_run_button.isChecked():
            self._terminal_follow_run_button.setToolTip(
                "Follow run enabled: terminal rundir follows current run selection"
            )
        else:
            self._terminal_follow_run_button.setToolTip(
                "Follow run disabled: terminal keeps the current rundir"
            )
