"""Backend helpers for embedded xterm support and X11 child-window resizing."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from typing import Optional, Tuple

from PyQt5.QtGui import QFont, QFontMetrics


def get_embedding_support() -> Tuple[bool, str]:
    """Return whether xterm embedding is supported in the current runtime."""
    if not sys.platform.startswith("linux"):
        return False, "Embedded terminal is currently implemented for Linux runtimes only."
    if not os.environ.get("DISPLAY"):
        return False, "Embedded terminal requires an X11 display with DISPLAY set."
    if shutil.which("xterm") is None:
        return False, "Embedded terminal requires xterm to be installed and available in PATH."
    return True, ""


def estimate_terminal_geometry(host_width: int, host_height: int, point_size: int = 11) -> Tuple[int, int]:
    """Estimate xterm columns and rows from host size and monospace metrics."""
    font = QFont("Monospace")
    font.setStyleHint(QFont.TypeWriter)
    font.setPointSize(point_size)
    metrics = QFontMetrics(font)

    cell_width = max(7, metrics.horizontalAdvance("W"))
    cell_height = max(14, metrics.height())
    usable_width = max(640, host_width - 6)
    usable_height = max(180, host_height - 6)
    columns = max(80, usable_width // cell_width)
    rows = max(16, usable_height // cell_height)
    return columns, rows


def build_xterm_arguments(
    host_win_id: int,
    run_dir: str,
    background_color: str,
    foreground_color: str,
    columns: int,
    rows: int,
) -> list:
    """Build xterm launch arguments for embedding mode."""
    return [
        "-into",
        str(int(host_win_id)),
        "-fa",
        "Monospace",
        "-fs",
        "11",
        "-geometry",
        f"{columns}x{rows}",
        "-bg",
        background_color,
        "-fg",
        foreground_color,
        "-sb",
        "-sl",
        "5000",
        "-title",
        f"XMeta Terminal - {os.path.basename(run_dir) or run_dir}",
    ]


def discover_embedded_child_window_id(host_win_id: int) -> Optional[int]:
    """Return the current embedded child window id inside one host window."""
    if not _is_x11_runtime():
        return None
    if host_win_id <= 0:
        return None

    x11 = _load_x11_library()
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


def resize_x11_window(child_win_id: int, x: int, y: int, width: int, height: int) -> None:
    """Resize and reposition one X11 child window."""
    if not _is_x11_runtime():
        return
    x11 = _load_x11_library()
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


def _is_x11_runtime() -> bool:
    """Return whether current runtime supports X11 calls."""
    return sys.platform.startswith("linux") and bool(os.environ.get("DISPLAY"))


def _load_x11_library():
    """Return configured ctypes bindings for libX11."""
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
