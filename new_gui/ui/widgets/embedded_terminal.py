"""Embedded xterm-based terminal widget helpers."""

import ctypes
import os
import shutil
import sys

from PyQt5.QtCore import QEvent, QProcess, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
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
        self._embedded_child_win_id = None
        self._current_run_dir = ""
        self._geometry_sync_attempts_remaining = 0

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

    def show_for_directory(self, run_dir: str) -> bool:
        """Show or restart the embedded terminal for the requested run directory."""
        run_dir = os.path.abspath(run_dir or "")
        if not run_dir:
            self._show_message("No run directory is selected.")
            return False

        previous_run_dir = os.path.abspath(self._current_run_dir or "")

        supported, reason = self._get_embedding_support()
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
        supported, reason = self._get_embedding_support()
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

    def _schedule_embedded_window_sync(self, delay_ms: int = 40) -> None:
        """Queue one geometry sync for the embedded child window."""
        if not self.is_running():
            return
        self._resize_sync_timer.start(max(0, delay_ms))

    def _sync_embedded_window_geometry(self) -> None:
        """Resize the embedded xterm child to fill the current host frame."""
        if not self.is_running():
            return

        child_win_id = self._embedded_child_win_id or self._discover_embedded_child_window_id()
        if not child_win_id:
            if self._geometry_sync_attempts_remaining > 0:
                self._geometry_sync_attempts_remaining -= 1
                self._schedule_embedded_window_sync(delay_ms=120)
            return

        self._embedded_child_win_id = child_win_id
        self._geometry_sync_attempts_remaining = 0

        host_width = max(1, self._terminal_host.width() - 2)
        host_height = max(1, self._terminal_host.height() - 2)
        self._resize_x11_window(child_win_id, 1, 1, host_width, host_height)

    def _discover_embedded_child_window_id(self):
        """Return the current embedded child window id inside the host frame."""
        if not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"):
            return None

        host_win_id = int(self._terminal_host.winId())
        if host_win_id <= 0:
            return None

        x11 = self._load_x11_library()
        if x11 is None:
            return None

        display = x11.XOpenDisplay(os.environ["DISPLAY"].encode("utf-8"))
        if not display:
            return None

        root_return = ctypes.c_ulong()
        parent_return = ctypes.c_ulong()
        children_return = ctypes.POINTER(ctypes.c_ulong)()
        child_count = ctypes.c_uint()

        try:
            status = x11.XQueryTree(
                display,
                ctypes.c_ulong(host_win_id),
                ctypes.byref(root_return),
                ctypes.byref(parent_return),
                ctypes.byref(children_return),
                ctypes.byref(child_count),
            )
            if not status or child_count.value == 0:
                return None
            return int(children_return[child_count.value - 1])
        finally:
            if children_return:
                x11.XFree(children_return)
            x11.XCloseDisplay(display)

    def _resize_x11_window(self, child_win_id: int, x: int, y: int, width: int, height: int) -> None:
        """Resize and reposition one X11 child window inside the terminal host."""
        if not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"):
            return

        x11 = self._load_x11_library()
        if x11 is None:
            return

        display = x11.XOpenDisplay(os.environ["DISPLAY"].encode("utf-8"))
        if not display:
            return

        try:
            x11.XMoveResizeWindow(
                display,
                ctypes.c_ulong(int(child_win_id)),
                ctypes.c_int(x),
                ctypes.c_int(y),
                ctypes.c_uint(max(1, width)),
                ctypes.c_uint(max(1, height)),
            )
            x11.XFlush(display)
        finally:
            x11.XCloseDisplay(display)

    @staticmethod
    def _load_x11_library():
        """Return a configured ctypes handle for libX11, if available."""
        try:
            x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        except OSError:
            try:
                x11 = ctypes.cdll.LoadLibrary("libX11.so")
            except OSError:
                return None

        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = ctypes.c_int
        x11.XQueryTree.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
            ctypes.POINTER(ctypes.c_uint),
        ]
        x11.XQueryTree.restype = ctypes.c_int
        x11.XMoveResizeWindow.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        x11.XMoveResizeWindow.restype = ctypes.c_int
        x11.XFree.argtypes = [ctypes.c_void_p]
        x11.XFree.restype = ctypes.c_int
        return x11

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
