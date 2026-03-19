"""Search UI bridge helpers for MainWindow."""


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
    window.filter_tree(text)


def on_header_filter_changed(window, text) -> None:
    """Mirror header search edits back to the visible search field."""
    set_quick_search_text(window, text)
    window.filter_tree(text)
