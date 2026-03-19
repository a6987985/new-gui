"""Embedded xterm-based terminal widget helpers."""

import os
import shutil
import sys

from PyQt5.QtCore import QProcess, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from new_gui.ui.output_panel_styles import build_embedded_terminal_style


class EmbeddedTerminalWidget(QWidget):
    """Host a native xterm process inside the Qt layout when supported."""

    close_requested = pyqtSignal()
    external_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._current_run_dir = ""

        self.setObjectName("embeddedTerminalPanel")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumHeight(180)
        self.setStyleSheet(build_embedded_terminal_style())

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 7, 10, 9)
        root_layout.setSpacing(7)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("Embedded Terminal")
        title_label.setObjectName("embeddedTerminalTitle")
        header_layout.addWidget(title_label)

        self._cwd_label = QLabel("")
        self._cwd_label.setObjectName("embeddedTerminalPath")
        self._cwd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header_layout.addWidget(self._cwd_label, 1)

        self._restart_button = QPushButton("Restart")
        self._restart_button.setObjectName("embeddedTerminalButton")
        self._restart_button.clicked.connect(self.restart_terminal)
        header_layout.addWidget(self._restart_button)

        self._external_button = QPushButton("External")
        self._external_button.setObjectName("embeddedTerminalButton")
        self._external_button.clicked.connect(self.external_requested.emit)
        header_layout.addWidget(self._external_button)

        close_button = QPushButton("Close")
        close_button.setObjectName("embeddedTerminalButton")
        close_button.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_button)

        root_layout.addLayout(header_layout)

        body_container = QWidget()
        body_layout = QStackedLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self._terminal_host = QFrame()
        self._terminal_host.setObjectName("embeddedTerminalHost")
        self._terminal_host.setAttribute(Qt.WA_NativeWindow, True)
        self._terminal_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body_layout.addWidget(self._terminal_host)

        message_view = QWidget()
        message_layout = QVBoxLayout(message_view)
        message_layout.setContentsMargins(16, 16, 16, 16)
        message_layout.setSpacing(10)
        message_layout.addStretch()
        self._message_label = QLabel("")
        self._message_label.setObjectName("embeddedTerminalMessage")
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignCenter)
        message_layout.addWidget(self._message_label)
        message_layout.addStretch()
        body_layout.addWidget(message_view)

        self._body_layout = body_layout
        self._message_view = message_view
        self._show_message("Embedded terminal is idle.")
        root_layout.addWidget(body_container, 1)

    def current_run_dir(self) -> str:
        """Return the run directory currently bound to the panel."""
        return self._current_run_dir

    def status_message(self) -> str:
        """Return the current status or fallback text shown by the widget."""
        return self._message_label.text()

    def is_running(self) -> bool:
        """Return whether the embedded xterm process is active."""
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def show_for_directory(self, run_dir: str) -> bool:
        """Show or restart the embedded terminal for the requested run directory."""
        run_dir = os.path.abspath(run_dir or "")
        if not run_dir:
            self._show_message("No run directory is selected.")
            return False

        self._current_run_dir = run_dir
        self._cwd_label.setText(run_dir)

        supported, reason = self._get_embedding_support()
        if not supported:
            self._show_message(reason)
            return False

        if self.is_running() and self.current_run_dir() == run_dir:
            self._show_host()
            return True

        return self.restart_terminal()

    def restart_terminal(self) -> bool:
        """Restart the embedded terminal in the current run directory."""
        supported, reason = self._get_embedding_support()
        if not supported:
            self._show_message(reason)
            return False
        if not self._current_run_dir:
            self._show_message("No run directory is selected.")
            return False

        self.stop_terminal()
        self._show_host()
        self._terminal_host.show()
        self._terminal_host.update()
        self._terminal_host.winId()

        process = QProcess(self)
        process.setWorkingDirectory(self._current_run_dir)
        process.setProgram("xterm")
        process.setArguments(self._build_xterm_arguments())
        process.errorOccurred.connect(self._on_process_error)
        process.finished.connect(self._on_process_finished)
        process.start()
        if not process.waitForStarted(3000):
            self._show_message(
                "Failed to start xterm inside the panel. Use the External button as a fallback."
            )
            process.deleteLater()
            return False

        self._process = process
        return True

    def stop_terminal(self) -> None:
        """Stop the embedded terminal process if one is running."""
        if self._process is None:
            return

        process = self._process
        self._process = None
        if process.state() != QProcess.NotRunning:
            process.terminate()
            if not process.waitForFinished(1500):
                process.kill()
                process.waitForFinished(1500)
        process.deleteLater()

    def shutdown(self) -> None:
        """Release any external resources owned by the widget."""
        self.stop_terminal()

    def _show_host(self) -> None:
        """Switch the body area back to the native terminal host view."""
        self._body_layout.setCurrentWidget(self._terminal_host)

    def _show_message(self, message: str) -> None:
        """Display a centered status message instead of the terminal host."""
        self._message_label.setText(message)
        self._body_layout.setCurrentWidget(self._message_view)

    def _build_xterm_arguments(self):
        """Return xterm arguments sized to the current host panel."""
        columns, rows = self._estimate_geometry()
        return [
            "-into",
            str(int(self._terminal_host.winId())),
            "-fa",
            "Monospace",
            "-fs",
            "11",
            "-geometry",
            f"{columns}x{rows}",
            "-bg",
            "white",
            "-fg",
            "black",
            "-sb",
            "-sl",
            "5000",
            "-title",
            f"XMeta Terminal - {os.path.basename(self._current_run_dir) or self._current_run_dir}",
        ]

    def _estimate_geometry(self):
        """Estimate xterm columns and rows from the current host size."""
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPointSize(11)
        metrics = QFontMetrics(font)

        cell_width = max(7, metrics.horizontalAdvance("W"))
        cell_height = max(14, metrics.height())
        host_width = max(640, self._terminal_host.width() - 6)
        host_height = max(180, self._terminal_host.height() - 6)

        columns = max(80, host_width // cell_width)
        rows = max(16, host_height // cell_height)
        return columns, rows

    def _on_process_error(self, _error) -> None:
        """Show a fallback message when the embedded xterm process fails."""
        self._show_message(
            "Embedded xterm failed to start or exited unexpectedly. Use the External button as a fallback."
        )

    def _on_process_finished(self, _exit_code: int, _exit_status) -> None:
        """Report a clean terminal exit once the shell closes."""
        self._process = None
        self._show_message("Embedded terminal exited. Click Restart to open a fresh shell.")

    @staticmethod
    def _get_embedding_support():
        """Return whether xterm embedding is supported in the current runtime."""
        if not sys.platform.startswith("linux"):
            return False, "Embedded terminal is currently implemented for Linux runtimes only."
        if not os.environ.get("DISPLAY"):
            return False, "Embedded terminal requires an X11 display with DISPLAY set."
        if shutil.which("xterm") is None:
            return False, "Embedded terminal requires xterm to be installed and available in PATH."
        return True, ""
