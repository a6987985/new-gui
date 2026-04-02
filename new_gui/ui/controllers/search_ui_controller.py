"""Search UI bridge helpers for MainWindow."""

from PyQt5.QtCore import QTimer

from new_gui.ui.controllers import runtime_controller


def _set_header_rebuild_guard(window, enabled: bool) -> None:
    """Toggle guards that suppress header geometry/resize reactions during rebuild."""
    active = bool(enabled)
    window._suspend_header_layout_updates = active

    header = getattr(window, "header", None)
    if header is not None and hasattr(header, "set_filter_geometry_updates_enabled"):
        header.set_filter_geometry_updates_enabled(not active)


def _apply_tree_filter(window, text) -> None:
    """Apply one tree filter request.

    Defer every filter request to the next event-loop turn so active QLineEdit
    key handling always finishes before tree filtering mutates visibility and
    refresh guards. This also gives the latest request a clean way to cancel
    stale earlier keystrokes.
    """
    normalized_text = text or ""
    search_options = {}
    if hasattr(window, "header") and hasattr(window.header, "get_filter_options"):
        search_options = window.header.get_filter_options()
    request_id = int(getattr(window, "_search_filter_request_id", 0)) + 1
    window._search_filter_request_id = request_id

    def apply_if_latest() -> None:
        if getattr(window, "_search_filter_request_id", 0) != request_id:
            return

        _set_header_rebuild_guard(window, True)
        runtime_controller.pause_runtime_observers(window)
        try:
            window.filter_tree(normalized_text, search_options=search_options)
        finally:
            def release_guards() -> None:
                _set_header_rebuild_guard(window, False)
                runtime_controller.resume_runtime_observers(window)

            QTimer.singleShot(0, release_guards)

    QTimer.singleShot(0, apply_if_latest)


def focus_search(window) -> None:
    """Focus the visible search input or show the embedded header filter."""
    if hasattr(window, "quick_search_input"):
        window.quick_search_input.setFocus()
        window.quick_search_input.selectAll()
    elif hasattr(window, "header"):
        window.header.show_filter()


def set_quick_search_text(window, text) -> None:
    """Update the persistent search field without triggering another filter pass."""
    if hasattr(window, "quick_search_input"):
        was_blocked = window.quick_search_input.blockSignals(True)
        window.quick_search_input.setText(text)
        window.quick_search_input.blockSignals(was_blocked)


def set_header_filter_text_silent(window, text) -> None:
    """Update the header search state without emitting filter_changed again."""
    if not hasattr(window, "header"):
        return

    window.header._filter_text = text
    if window.header.filter_edit:
        was_blocked = window.header.filter_edit.blockSignals(True)
        window.header.filter_edit.setText(text)
        window.header.filter_edit.blockSignals(was_blocked)


def on_top_search_changed(window, text) -> None:
    """Keep the header search state in sync with the visible search field."""
    set_header_filter_text_silent(window, text)
    _apply_tree_filter(window, text)


def on_header_filter_changed(window, text) -> None:
    """Mirror header search edits back to the visible search field."""
    set_quick_search_text(window, text)
    _apply_tree_filter(window, text)
