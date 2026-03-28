"""Embedded xterm-based terminal widget helpers."""

import os

from PyQt5.QtCore import QEvent, QProcess, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from new_gui.services.flow_background import choose_terminal_foreground, normalize_background_color
from new_gui.services import terminal_embed_backend
from new_gui.ui.output_panel_styles import build_embedded_terminal_style


class EmbeddedTerminalWidget(QWidget):
    """Host a native xterm process inside the Qt layout when supported."""

    close_requested = pyqtSignal()
    external_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._embedded_child_win_id = None
        self._current_run_dir = ""
        self._geometry_sync_attempts_remaining = 0
        self._background_color = "#ffffff"
        self._foreground_color = "#111827"

        self.setObjectName("embeddedTerminalPanel")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumHeight(180)
        self.setStyleSheet(build_embedded_terminal_style())

        self._resize_sync_timer = QTimer(self)
        self._resize_sync_timer.setSingleShot(True)
        self._resize_sync_timer.timeout.connect(self._sync_embedded_window_geometry)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 6, 10, 10)
        root_layout.setSpacing(0)

        body_container = QWidget()
        body_layout = QStackedLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self._terminal_host = QFrame()
        self._terminal_host.setObjectName("embeddedTerminalHost")
        self._terminal_host.setAttribute(Qt.WA_NativeWindow, True)
        self._terminal_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._terminal_host.installEventFilter(self)
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

    def set_terminal_background(self, background_color: str, restart_if_running: bool = True) -> None:
        """Update the xterm background and foreground palette."""
        normalized = normalize_background_color(background_color) or "#ffffff"
        foreground = choose_terminal_foreground(normalized)
        changed = (
            normalized != self._background_color
            or foreground != self._foreground_color
        )

        self._background_color = normalized
        self._foreground_color = foreground

        if changed and restart_if_running and self.is_running() and self.current_run_dir():
            self.restart_terminal()

    def show_for_directory(self, run_dir: str) -> bool:
        """Show or restart the embedded terminal for the requested run directory."""
        run_dir = os.path.abspath(run_dir or "")
        if not run_dir:
            self._show_message("No run directory is selected.")
            return False

        previous_run_dir = os.path.abspath(self._current_run_dir or "")

        supported, reason = terminal_embed_backend.get_embedding_support()
        if not supported:
            self._show_message(reason)
            return False

        if self.is_running() and previous_run_dir == run_dir:
            self._show_host()
            return True

        self._current_run_dir = run_dir
        return self.restart_terminal()

    def restart_terminal(self) -> bool:
        """Restart the embedded terminal in the current run directory."""
        supported, reason = terminal_embed_backend.get_embedding_support()
        if not supported:
            self._show_message(reason)
            return False
        if not self._current_run_dir:
            self._show_message("No run directory is selected.")
            return False

        self.stop_terminal()
        self._embedded_child_win_id = None
        self._geometry_sync_attempts_remaining = 6
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
        self._schedule_embedded_window_sync(delay_ms=120)
        return True

    def stop_terminal(self) -> None:
        """Stop the embedded terminal process if one is running."""
        if self._process is None:
            return

        process = self._process
        self._process = None
        self._embedded_child_win_id = None
        self._geometry_sync_attempts_remaining = 0
        self._resize_sync_timer.stop()
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

    def eventFilter(self, watched, event):
        """Resize the embedded X11 child window when the host area changes size."""
        if watched is self._terminal_host and event.type() in (QEvent.Resize, QEvent.Show):
            self._schedule_embedded_window_sync()
        return super().eventFilter(watched, event)

    def _build_xterm_arguments(self):
        """Return xterm arguments sized to the current host panel."""
        columns, rows = terminal_embed_backend.estimate_terminal_geometry(
            self._terminal_host.width(),
            self._terminal_host.height(),
            point_size=11,
        )
        return terminal_embed_backend.build_xterm_arguments(
            host_win_id=int(self._terminal_host.winId()),
            run_dir=self._current_run_dir,
            background_color=self._background_color,
            foreground_color=self._foreground_color,
            columns=columns,
            rows=rows,
        )

    def _schedule_embedded_window_sync(self, delay_ms: int = 40) -> None:
        """Queue one geometry sync for the embedded child window."""
        if not self.is_running():
            return
        self._resize_sync_timer.start(max(0, delay_ms))

    def _sync_embedded_window_geometry(self) -> None:
        """Resize the embedded xterm child to fill the current host frame."""
        if not self.is_running():
            return

        child_win_id = self._embedded_child_win_id or terminal_embed_backend.discover_embedded_child_window_id(
            int(self._terminal_host.winId())
        )
        if not child_win_id:
            if self._geometry_sync_attempts_remaining > 0:
                self._geometry_sync_attempts_remaining -= 1
                self._schedule_embedded_window_sync(delay_ms=120)
            return

        self._embedded_child_win_id = child_win_id
        self._geometry_sync_attempts_remaining = 0

        host_width = max(1, self._terminal_host.width() - 2)
        host_height = max(1, self._terminal_host.height() - 2)
        terminal_embed_backend.resize_x11_window(child_win_id, 1, 1, host_width, host_height)

    def _on_process_error(self, _error) -> None:
        """Show a fallback message when the embedded xterm process fails."""
        self._embedded_child_win_id = None
        self._show_message(
            "Embedded xterm failed to start or exited unexpectedly. Use the External button as a fallback."
        )

    def _on_process_finished(self, _exit_code: int, _exit_status) -> None:
        """Report a clean terminal exit once the shell closes."""
        self._process = None
        self._embedded_child_win_id = None
        self._geometry_sync_attempts_remaining = 0
        self._resize_sync_timer.stop()
        self._show_message("Embedded terminal exited. Click Restart to open a fresh shell.")
