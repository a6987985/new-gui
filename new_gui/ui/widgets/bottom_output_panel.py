"""Bottom output panel widgets for terminal and session log."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
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
        self.setStyleSheet(
            """
                QWidget#sessionLogWidget {
                    background-color: #f6f9fb;
                }
                QLabel#sessionLogTitle {
                    color: #526476;
                    font-weight: 600;
                    font-size: 12px;
                }
                QTextBrowser#sessionLogView {
                    background-color: #fcfdfe;
                    border: 1px solid #dbe3eb;
                    border-radius: 6px;
                    color: #314154;
                    padding: 5px;
                }
                QPushButton#sessionLogButton {
                    background-color: #fafcfd;
                    border: 1px solid #d9e1e8;
                    border-radius: 6px;
                    color: #5c6d7e;
                    font-weight: 600;
                    padding: 3px 10px;
                }
                QPushButton#sessionLogButton:hover {
                    background-color: #eef3f7;
                    border: 1px solid #c9d5e0;
                }
                QPushButton#sessionLogButton:pressed {
                    background-color: #e6edf4;
                    border: 1px solid #bccbda;
                }
            """
        )

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
        self._view.document().setDefaultStyleSheet(
            """
                body {
                    color: #314154;
                    font-size: 12px;
                }
                .entry { margin-bottom: 10px; }
                .meta { margin-bottom: 4px; }
                .timestamp { color: #7b8794; }
                .source { color: #6e8cac; }
                .message { color: #2f3d4c; }
                .command-label, .details-label {
                    color: #6885a2;
                    font-weight: 600;
                    margin-top: 4px;
                }
                pre {
                    white-space: pre-wrap;
                    margin: 4px 0 0 0;
                    padding: 6px 8px;
                    background: #f5f8fa;
                    border: 1px solid #dee5ec;
                    border-radius: 5px;
                    color: #314154;
                    font-family: monospace;
                }
            """
        )
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomOutputPanel")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            """
                QWidget#bottomOutputPanel {
                    background-color: #e9eff4;
                }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)
        self._tabs.setStyleSheet(
            """
                QTabWidget {
                    background-color: #e9eff4;
                }
                QTabWidget::tab-bar {
                    alignment: left;
                    left: 12px;
                }
                QTabWidget::pane {
                    border-top: 1px solid #d6dee7;
                    background-color: #f6f9fb;
                    top: -1px;
                }
                QTabBar::tab {
                    background: transparent;
                    color: #738293;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 5px 14px;
                    margin: 8px 4px 0 0;
                    font-size: 12px;
                    font-weight: 600;
                }
                QTabBar::tab:hover {
                    background: #e3eaf0;
                    color: #556779;
                }
                QTabBar::tab:selected {
                    background: #f6f9fb;
                    color: #334657;
                    border: 1px solid #d0d8e1;
                    border-bottom-color: #f6f9fb;
                    margin-bottom: -1px;
                }
                QTabBar::tab:selected:hover {
                    background: #f6f9fb;
                }
            """
        )

        self.terminal_widget = EmbeddedTerminalWidget(self)
        self.log_widget = SessionLogWidget(self)
        self._tabs.addTab(self.terminal_widget, "Terminal")
        self._tabs.addTab(self.log_widget, "Log")

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
