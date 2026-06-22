"""Bottom output panel and GUI log orchestration helpers for MainWindow."""

import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from new_gui.shared.config.settings import DEFAULT_LOG_LEVEL, logger
from new_gui.presentation.views.widgets.bottom_output_panel import (
    GuiLogEntry,
    GuiLogHandler,
    GuiLogSignalBridge,
)


class ActionRefreshSignalBridge(QObject):
    """Bridge action-complete refresh requests safely back to the GUI thread."""

    refresh_requested = pyqtSignal(object)


def init_ui_log_dispatcher(window) -> None:
    """Create the thread-safe log bridge used by the GUI session log."""
    window._ui_log_dispatcher = GuiLogSignalBridge(window)
    window._ui_log_dispatcher.entry_requested.connect(window._append_ui_log_entry)


def init_action_refresh_dispatcher(window) -> None:
    """Create the thread-safe bridge used by async action refresh callbacks."""
    window._action_refresh_dispatcher = ActionRefreshSignalBridge(window)
    window._action_refresh_dispatcher.refresh_requested.connect(window._handle_action_refresh_request)


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


def queue_action_refresh_request(window, payload: object) -> None:
    """Queue one action-refresh request onto the GUI thread."""
    if getattr(window, "_action_refresh_dispatcher", None) is not None:
        window._action_refresh_dispatcher.refresh_requested.emit(payload)


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


def _content_area_height(window, splitter) -> int:
    """Return the available splitter height for bottom-output sizing."""
    return max(splitter.height(), window.height())


def _normal_bottom_output_sizes(
    window,
    splitter,
    requested_height: int | None = None,
) -> list:
    """Return tree/output splitter sizes for normal bottom-panel mode."""
    total_height = _content_area_height(window, splitter)
    requested_height = max(180, requested_height or window._bottom_output_last_height)
    output_height = min(requested_height, max(180, total_height // 2))
    tree_height = max(220, total_height - output_height)
    return [tree_height, output_height]


def _sync_terminal_content_fill_button(window, filled: bool) -> None:
    """Synchronize the terminal fill button without assuming it exists."""
    panel = getattr(window, "_bottom_output_panel", None)
    if panel is not None and hasattr(panel, "set_terminal_content_filled"):
        panel.set_terminal_content_filled(filled)


def set_bottom_output_panel_visible(window, visible: bool) -> None:
    """Show or collapse the bottom output panel inside the content splitter."""
    if not hasattr(window, "_content_splitter") or not hasattr(window, "_bottom_output_panel"):
        return

    panel = window._bottom_output_panel
    splitter = window._content_splitter

    if visible:
        panel.show()
        if getattr(window, "_terminal_output_content_filled", False):
            set_terminal_output_content_filled(window, True)
        else:
            splitter.setSizes(_normal_bottom_output_sizes(window, splitter))
        panel.raise_()
        if hasattr(window, "_top_panel_terminal_toggle_button"):
            was_blocked = window._top_panel_terminal_toggle_button.blockSignals(True)
            window._top_panel_terminal_toggle_button.setChecked(True)
            window._top_panel_terminal_toggle_button.blockSignals(was_blocked)
        return

    current_sizes = splitter.sizes()
    if getattr(window, "_terminal_output_content_filled", False):
        window._terminal_output_content_filled = False
        restore_height = getattr(window, "_terminal_output_restore_height", 0)
        if restore_height > 0:
            window._bottom_output_last_height = restore_height
        _sync_terminal_content_fill_button(window, False)
    elif len(current_sizes) > 1 and current_sizes[1] > 0:
        window._bottom_output_last_height = current_sizes[1]
    splitter.setSizes([1, 0])
    panel.hide()
    if hasattr(window, "_top_panel_terminal_toggle_button"):
        was_blocked = window._top_panel_terminal_toggle_button.blockSignals(True)
        window._top_panel_terminal_toggle_button.setChecked(False)
        window._top_panel_terminal_toggle_button.blockSignals(was_blocked)


def set_embedded_terminal_panel_visible(window, visible: bool) -> None:
    """Backward-compatible wrapper for the old terminal-only panel API."""
    set_bottom_output_panel_visible(window, visible)


def set_terminal_output_content_filled(window, filled: bool) -> None:
    """Expand or restore the terminal inside the content splitter."""
    if not hasattr(window, "_content_splitter") or not hasattr(window, "_bottom_output_panel"):
        return

    panel = window._bottom_output_panel
    splitter = window._content_splitter
    filled = bool(filled)

    if filled:
        if not getattr(window, "_terminal_output_content_filled", False):
            current_sizes = splitter.sizes()
            if len(current_sizes) > 1 and current_sizes[1] > 0:
                window._terminal_output_restore_height = current_sizes[1]
                window._bottom_output_last_height = current_sizes[1]
            else:
                window._terminal_output_restore_height = window._bottom_output_last_height

        panel.show()
        total_height = _content_area_height(window, splitter)
        splitter.setSizes([1, max(1, total_height - 1)])
        panel.raise_()
        window._terminal_output_content_filled = True
        _sync_terminal_content_fill_button(window, True)
        if hasattr(window, "_top_panel_terminal_toggle_button"):
            was_blocked = window._top_panel_terminal_toggle_button.blockSignals(True)
            window._top_panel_terminal_toggle_button.setChecked(True)
            window._top_panel_terminal_toggle_button.blockSignals(was_blocked)
        return

    restore_height = getattr(
        window,
        "_terminal_output_restore_height",
        window._bottom_output_last_height,
    )
    was_filled = getattr(window, "_terminal_output_content_filled", False)
    window._terminal_output_content_filled = False
    _sync_terminal_content_fill_button(window, False)
    if was_filled and panel.isVisible():
        splitter.setSizes(_normal_bottom_output_sizes(window, splitter, restore_height))


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


def toggle_terminal_output_panel(window) -> bool:
    """Toggle the bottom terminal panel from the top icon button."""
    panel = getattr(window, "_bottom_output_panel", None)
    if panel is not None and panel.isVisible():
        hide_bottom_output_panel(window)
        return False

    run_dir = getattr(window, "combo_sel", "")
    if show_embedded_terminal_panel(window, run_dir):
        return True

    hide_bottom_output_panel(window)
    return False


def show_log_output_panel(window) -> None:
    """Open the bottom output area and switch to the session log tab."""
    if not hasattr(window, "_bottom_output_panel"):
        return
    set_terminal_output_content_filled(window, False)
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
