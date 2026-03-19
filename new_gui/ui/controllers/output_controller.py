"""Bottom output panel and GUI log orchestration helpers for MainWindow."""

import logging

from PyQt5.QtWidgets import QApplication

from new_gui.config.settings import DEFAULT_LOG_LEVEL, logger
from new_gui.ui.widgets.bottom_output_panel import GuiLogEntry, GuiLogHandler, GuiLogSignalBridge


def init_ui_log_dispatcher(window) -> None:
    """Create the thread-safe log bridge used by the GUI session log."""
    window._ui_log_dispatcher = GuiLogSignalBridge(window)
    window._ui_log_dispatcher.entry_requested.connect(window._append_ui_log_entry)


def install_gui_log_handler(window) -> None:
    """Attach a GUI-only log handler while keeping console logging unchanged."""
    if getattr(window, "_gui_log_handler", None) is not None:
        return

    root_logger = logging.getLogger()
    window._gui_log_previous_logger_level = logger.level
    window._gui_log_root_handler_levels = {
        id(handler): handler.level for handler in root_logger.handlers
    }

    for handler in root_logger.handlers:
        if handler.level < DEFAULT_LOG_LEVEL:
            handler.setLevel(DEFAULT_LOG_LEVEL)

    logger.setLevel(logging.INFO)
    window._gui_log_handler = GuiLogHandler(lambda entry: queue_ui_log_entry(window, entry))
    logger.addHandler(window._gui_log_handler)


def remove_gui_log_handler(window) -> None:
    """Detach the GUI log handler and restore previous logger settings."""
    if getattr(window, "_gui_log_handler", None) is None:
        return

    logger.removeHandler(window._gui_log_handler)
    window._gui_log_handler = None

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if id(handler) in window._gui_log_root_handler_levels:
            handler.setLevel(window._gui_log_root_handler_levels[id(handler)])

    if window._gui_log_previous_logger_level is not None:
        logger.setLevel(window._gui_log_previous_logger_level)

    window._gui_log_root_handler_levels = {}
    window._gui_log_previous_logger_level = None


def queue_ui_log_entry(window, entry: GuiLogEntry) -> None:
    """Queue one log entry back onto the GUI thread."""
    if getattr(window, "_ui_log_dispatcher", None) is not None:
        window._ui_log_dispatcher.entry_requested.emit(entry)


def normalize_ui_log_level(level: str) -> str:
    """Normalize GUI log levels to the supported INFO/WARNING/ERROR set."""
    level_name = (level or "INFO").upper()
    if level_name in ("ERROR", "CRITICAL"):
        return "ERROR"
    if level_name == "WARNING":
        return "WARNING"
    return "INFO"


def append_ui_log(
    window,
    level: str,
    source: str,
    message: str,
    command: str = "",
    details: str = "",
) -> None:
    """Append one session log entry through the thread-safe GUI sink."""
    entry = GuiLogEntry.create(
        level=normalize_ui_log_level(level),
        source=source,
        message=message,
        command=command,
        details=details,
    )
    queue_ui_log_entry(window, entry)


def append_ui_log_entry(window, entry) -> None:
    """Render one queued log entry and apply panel attention rules."""
    if not hasattr(window, "_bottom_output_panel"):
        return

    entry.level = normalize_ui_log_level(entry.level)
    window._bottom_output_panel.append_log_entry(entry)

    if entry.level in ("WARNING", "ERROR"):
        show_log_output_panel(window)


def set_bottom_output_panel_visible(window, visible: bool) -> None:
    """Show or collapse the bottom output panel inside the content splitter."""
    if not hasattr(window, "_content_splitter") or not hasattr(window, "_bottom_output_panel"):
        return

    panel = window._bottom_output_panel
    splitter = window._content_splitter

    if visible:
        panel.show()
        total_height = max(splitter.height(), window.height())
        requested_height = max(180, window._bottom_output_last_height)
        output_height = min(requested_height, max(180, total_height // 2))
        tree_height = max(220, total_height - output_height)
        splitter.setSizes([tree_height, output_height])
        panel.raise_()
        return

    current_sizes = splitter.sizes()
    if len(current_sizes) > 1 and current_sizes[1] > 0:
        window._bottom_output_last_height = current_sizes[1]
    splitter.setSizes([1, 0])
    panel.hide()


def set_embedded_terminal_panel_visible(window, visible: bool) -> None:
    """Backward-compatible wrapper for the old terminal-only panel API."""
    set_bottom_output_panel_visible(window, visible)


def show_embedded_terminal_panel(window, run_dir: str) -> bool:
    """Open the embedded terminal panel for the requested run directory."""
    if not hasattr(window, "_embedded_terminal"):
        return False
    set_bottom_output_panel_visible(window, True)
    window._bottom_output_panel.show_terminal_tab()
    QApplication.processEvents()
    if not window._embedded_terminal.show_for_directory(run_dir):
        return False
    return True


def hide_embedded_terminal_panel(window) -> None:
    """Close the embedded terminal session and collapse the bottom panel."""
    if not hasattr(window, "_embedded_terminal"):
        return
    window._embedded_terminal.stop_terminal()
    set_bottom_output_panel_visible(window, False)


def hide_bottom_output_panel(window) -> None:
    """Collapse the bottom output panel without stopping the terminal session."""
    set_bottom_output_panel_visible(window, False)


def show_log_output_panel(window) -> None:
    """Open the bottom output area and switch to the session log tab."""
    if not hasattr(window, "_bottom_output_panel"):
        return
    set_bottom_output_panel_visible(window, True)
    window._bottom_output_panel.show_log_tab()


def get_embedded_terminal_status_message(window) -> str:
    """Return the current embedded-terminal status text, if any."""
    if hasattr(window, "_embedded_terminal"):
        return window._embedded_terminal.status_message()
    return ""


def is_terminal_follow_run_enabled(window) -> bool:
    """Return whether the embedded terminal should follow run selection changes."""
    if hasattr(window, "_bottom_output_panel"):
        return window._bottom_output_panel.is_terminal_follow_run_enabled()
    return bool(getattr(window, "_terminal_follow_run", False))


def set_terminal_follow_run_enabled(window, enabled: bool) -> None:
    """Update the terminal follow-run preference in the window and panel."""
    enabled = bool(enabled)
    window._terminal_follow_run = enabled
    if hasattr(window, "_bottom_output_panel"):
        window._bottom_output_panel.set_terminal_follow_run_enabled(enabled)


def sync_embedded_terminal_run_dir(window, run_dir: str) -> bool:
    """Sync the embedded terminal session to the provided run directory when enabled."""
    if not is_terminal_follow_run_enabled(window):
        return False
    if not hasattr(window, "_embedded_terminal"):
        return False

    terminal = window._embedded_terminal
    if not run_dir:
        return False
    if not terminal.is_running() and not terminal.current_run_dir():
        return False

    return terminal.show_for_directory(run_dir)
