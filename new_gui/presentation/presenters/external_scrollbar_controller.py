"""External scrollbar coordination for main and graph content views."""

from PyQt5.QtCore import QPoint, Qt


def connect_tree_scrollbar(window) -> None:
    """Mirror the hidden internal tree scrollbar onto the fixed outer gutter."""
    if not hasattr(window, "tree") or not hasattr(window, "_tree_external_v_scrollbar"):
        return

    internal_scrollbar = window.tree.verticalScrollBar()
    external_scrollbar = window._tree_external_v_scrollbar

    internal_scrollbar.rangeChanged.connect(lambda *_: sync_external_scrollbar(window))
    internal_scrollbar.valueChanged.connect(lambda *_: sync_external_scrollbar(window))
    external_scrollbar.valueChanged.connect(
        lambda value: on_external_scrollbar_value_changed(window, value)
    )


def connect_graph_scrollbar(window) -> None:
    """Connect graph-view scrollbar updates to the shared external scrollbar once."""
    panel = getattr(window, "_dependency_graph_panel", None)
    if panel is None or not hasattr(panel, "view"):
        return
    if bool(getattr(window, "_graph_external_scrollbar_connected", False)):
        return

    graph_scrollbar = panel.view.verticalScrollBar()
    panel.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    graph_scrollbar.rangeChanged.connect(lambda *_: sync_external_scrollbar(window))
    graph_scrollbar.valueChanged.connect(lambda *_: sync_external_scrollbar(window))
    window._graph_external_scrollbar_connected = True
    sync_external_scrollbar(window)


def active_internal_scrollbar(window):
    """Return the active internal vertical scrollbar for the current content mode."""
    is_graph_mode = getattr(window, "_active_content_mode", "main") == "graph"
    if is_graph_mode:
        panel = getattr(window, "_dependency_graph_panel", None)
        if panel is not None and hasattr(panel, "view"):
            panel.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            return panel.view.verticalScrollBar()
    if hasattr(window, "tree"):
        return window.tree.verticalScrollBar()
    return None


def on_external_scrollbar_value_changed(window, value: int) -> None:
    """Drive the active internal scrollbar when the external scrollbar moves."""
    internal_scrollbar = active_internal_scrollbar(window)
    if internal_scrollbar is None:
        return
    internal_scrollbar.setValue(value)


def sync_external_scrollbar(window) -> None:
    """Keep the fixed outer scrollbar in sync with the active content scrollbar."""
    if not hasattr(window, "_tree_external_v_scrollbar"):
        return

    internal_scrollbar = active_internal_scrollbar(window)
    if internal_scrollbar is None:
        return
    external_scrollbar = window._tree_external_v_scrollbar
    previous_blocked = external_scrollbar.signalsBlocked()
    external_scrollbar.blockSignals(True)
    try:
        external_scrollbar.setRange(internal_scrollbar.minimum(), internal_scrollbar.maximum())
        external_scrollbar.setPageStep(internal_scrollbar.pageStep())
        external_scrollbar.setSingleStep(internal_scrollbar.singleStep())
        external_scrollbar.setValue(internal_scrollbar.value())
        external_scrollbar.setEnabled(internal_scrollbar.maximum() > internal_scrollbar.minimum())
    finally:
        external_scrollbar.blockSignals(previous_blocked)
    position_external_scrollbar(window)
    external_scrollbar.update()


def position_external_scrollbar(window) -> None:
    """Pin the external scrollbar to the right edge of the active content area."""
    if not hasattr(window, "_tree_external_v_scrollbar") or not hasattr(window, "_content_row"):
        return

    scrollbar = window._tree_external_v_scrollbar
    content_row = window._content_row
    if scrollbar is None or content_row is None:
        return
    if content_row.width() <= 0:
        return

    is_graph_mode = getattr(window, "_active_content_mode", "main") == "graph"
    target_widget = (
        getattr(window, "_graph_view_page", None)
        if is_graph_mode
        else getattr(window, "_tree_view_container", None)
    )
    if target_widget is None:
        return

    top_left = target_widget.mapTo(content_row, QPoint(0, 0))
    scrollbar_width = scrollbar.width() if scrollbar.width() > 0 else 16
    x_pos = max(0, content_row.width() - scrollbar_width)
    y_pos = max(0, top_left.y())
    height = max(0, target_widget.height())
    scrollbar.setGeometry(x_pos, y_pos, scrollbar_width, height)
    scrollbar.raise_()
