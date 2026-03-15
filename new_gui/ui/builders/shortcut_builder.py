"""Keyboard shortcut builder helpers for MainWindow."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

from new_gui.config.settings import SHORTCUTS


def setup_keyboard_shortcuts(window) -> None:
    """Setup global keyboard shortcuts."""
    shortcut_search = QShortcut(QKeySequence(SHORTCUTS["search"]["key"]), window)
    shortcut_search.activated.connect(window._focus_search)
    shortcut_search.setContext(Qt.ApplicationShortcut)

    shortcut_refresh = QShortcut(QKeySequence(SHORTCUTS["refresh"]["key"]), window)
    shortcut_refresh.activated.connect(window._refresh_view)
    shortcut_refresh.setContext(Qt.ApplicationShortcut)

    shortcut_expand = QShortcut(QKeySequence(SHORTCUTS["expand_all"]["key"]), window)
    shortcut_expand.activated.connect(window.expand_tree_default)
    shortcut_expand.setContext(Qt.ApplicationShortcut)

    shortcut_collapse = QShortcut(QKeySequence(SHORTCUTS["collapse_all"]["key"]), window)
    shortcut_collapse.activated.connect(window.tree.collapseAll)
    shortcut_collapse.setContext(Qt.ApplicationShortcut)

    shortcut_theme = QShortcut(QKeySequence(SHORTCUTS["toggle_theme"]["key"]), window)
    shortcut_theme.activated.connect(window._toggle_theme)
    shortcut_theme.setContext(Qt.ApplicationShortcut)

    shortcut_graph = QShortcut(QKeySequence(SHORTCUTS["show_graph"]["key"]), window)
    shortcut_graph.activated.connect(window.show_dependency_graph)
    shortcut_graph.setContext(Qt.ApplicationShortcut)

    shortcut_copy = QShortcut(QKeySequence(SHORTCUTS["copy_target"]["key"]), window)
    shortcut_copy.activated.connect(window._copy_selected_target)
    shortcut_copy.setContext(Qt.ApplicationShortcut)

    shortcut_run = QShortcut(QKeySequence(SHORTCUTS["run_selected"]["key"]), window)
    shortcut_run.activated.connect(lambda: window.start("XMeta_run"))
    shortcut_run.setContext(Qt.ApplicationShortcut)

    shortcut_trace_up = QShortcut(QKeySequence(SHORTCUTS["trace_up"]["key"]), window)
    shortcut_trace_up.activated.connect(lambda: window.retrace_tab("in"))
    shortcut_trace_up.setContext(Qt.ApplicationShortcut)

    shortcut_trace_down = QShortcut(QKeySequence(SHORTCUTS["trace_down"]["key"]), window)
    shortcut_trace_down.activated.connect(lambda: window.retrace_tab("out"))
    shortcut_trace_down.setContext(Qt.ApplicationShortcut)

    shortcut_user_params = QShortcut(QKeySequence(SHORTCUTS["user_params"]["key"]), window)
    shortcut_user_params.activated.connect(window.open_user_params)
    shortcut_user_params.setContext(Qt.ApplicationShortcut)

    shortcut_tile_params = QShortcut(QKeySequence(SHORTCUTS["tile_params"]["key"]), window)
    shortcut_tile_params.activated.connect(window.open_tile_params)
    shortcut_tile_params.setContext(Qt.ApplicationShortcut)
