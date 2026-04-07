"""Top-panel and tree-area builder helpers for MainWindow."""

from typing import Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QStandardItemModel
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from new_gui.services import tree_rows, view_tabs
from new_gui.ui import style_sheets
from new_gui.ui.controllers import runtime_controller
from new_gui.ui.top_panel_widget_styles import (
    build_run_selector_style,
    build_tab_close_button_style,
)
from new_gui.ui.builders.top_button_layout import get_top_button_anchor_y, rebuild_top_action_buttons
from new_gui.ui.builders.top_button_specs import (
    DEFAULT_TOP_BUTTON_IDS,
    get_top_button_choices,
    normalize_visible_top_buttons,
)
from new_gui.ui.widgets.bounded_combo import BoundedComboBox
from new_gui.ui.widgets.notifications import NotificationManager
from new_gui.ui.widgets.scrollbars import RoundedScrollBar
from new_gui.ui.widgets.status_bar import StatusBar
from new_gui.ui.widgets.tree_view import ColorTreeView, TreeViewEventFilter
from new_gui.ui.widgets.bottom_output_panel import BottomOutputPanel
from new_gui.ui.widgets.workspace_sidebar import WorkspaceSidebar
from new_gui.ui.widgets.delegates import BorderItemDelegate, TuneComboBoxDelegate
from new_gui.ui.widgets.filter_header import FilterHeaderView
from new_gui.ui.widgets.labels import ClickableLabel


def init_top_panel(window) -> None:
    """Initialize the top control panel."""
    window.top_panel = QWidget()
    window.top_panel.setObjectName("topPanel")
    window.top_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    default_top_panel_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef)"
    window._default_top_panel_style = style_sheets.build_default_top_panel_style(default_top_panel_bg)
    window.top_panel.setStyleSheet(window._default_top_panel_style)
    shadow = QGraphicsDropShadowEffect(window)
    shadow.setBlurRadius(8)
    shadow.setOffset(0, 2)
    shadow.setColor(QColor(0, 0, 0, 30))
    window.top_panel.setGraphicsEffect(shadow)

    top_layout = QVBoxLayout(window.top_panel)
    top_layout.setContentsMargins(16, 8, 16, 8)
    top_layout.setSpacing(6)
    window._top_panel_base_margins = (16, 8, 16, 8)

    row1_layout = QHBoxLayout()
    row1_layout.setContentsMargins(0, 0, 0, 0)
    row1_layout.setSpacing(8)

    window.combo = BoundedComboBox()
    window.populate_run_combo()
    window.combo.setMinimumWidth(300)
    window.combo.popup_about_to_show.connect(window.refresh_available_runs)
    window.combo.currentIndexChanged.connect(window.on_run_changed)
    window.combo.setStyleSheet(build_run_selector_style())

    row1_layout.addWidget(window.combo)
    window._top_button_placeholder = QWidget()
    window._top_button_placeholder.setStyleSheet("background: transparent; border: none;")
    row1_layout.addWidget(window._top_button_placeholder)
    rebuild_top_action_buttons(window)

    top_layout.addLayout(row1_layout)
    window._main_layout.addWidget(window.top_panel)

    window.tab_bar = QWidget()
    window.tab_bar.setObjectName("tabBar")
    tab_bg_color = QColor(window.window_bg).darker(120)
    tab_bg_hex = tab_bg_color.name()
    window._default_tab_bar_style = style_sheets.build_tab_bar_style(
        tab_bg_hex,
        "border-bottom: 1px solid #d0d0d0;",
    )
    window.tab_bar.setStyleSheet(window._default_tab_bar_style)
    tab_layout = QHBoxLayout(window.tab_bar)
    tab_layout.setContentsMargins(12, 2, 12, 2)
    tab_layout.setSpacing(2)

    window.tab_widget = QWidget()
    window.tab_widget.setObjectName("tabWidget")
    tab_widget_bg = QColor(window.window_bg).lighter(108)
    tab_widget_bg_hex = tab_widget_bg.name()
    window._default_tab_widget_style = style_sheets.build_tab_widget_style(
        tab_widget_bg_hex,
        "border: 1px solid #d0d0d0;",
        "border-bottom: none;",
    )
    window.tab_widget.setStyleSheet(window._default_tab_widget_style)
    tab_inner_layout = QHBoxLayout(window.tab_widget)
    tab_inner_layout.setContentsMargins(14, 4, 10, 4)
    tab_inner_layout.setSpacing(6)

    window.tab_label = ClickableLabel("")
    window.tab_label.doubleClicked.connect(window.toggle_tree_expansion)
    window.tab_label.set_custom_tooltip("Double-click to Expand/Collapse All")
    window.tab_label.setStyleSheet(view_tabs.MAIN_RUN_TAB_STYLE)

    window.tab_close_btn = QPushButton("×")
    window.tab_close_btn.setFixedSize(20, 20)
    window.tab_close_btn.setCursor(Qt.PointingHandCursor)
    window.tab_close_btn.setToolTip("Close Tab")
    window.tab_close_btn.clicked.connect(window.close_tree_view)
    window.tab_close_btn.setStyleSheet(build_tab_close_button_style())

    tab_inner_layout.addWidget(window.tab_label)
    tab_inner_layout.addWidget(window.tab_close_btn)

    tab_layout.addWidget(window.tab_widget)
    tab_layout.addStretch()
    row1_layout.insertWidget(1, window.tab_bar, 1)
    QTimer.singleShot(0, window._position_top_action_buttons)

    window.tree = ColorTreeView()

    window.header = FilterHeaderView(Qt.Horizontal, window.tree, filter_column=1)
    window.header.setFixedHeight(46)
    window.tree.setHeader(window.header)
    window.header.filter_changed.connect(window._on_header_filter_changed)
    window.header.level_double_clicked.connect(window.toggle_tree_expansion)
    window.header.sectionResized.connect(window._on_tree_header_section_resized)

    window.delegate = BorderItemDelegate(window.tree)
    window.tree.setItemDelegate(window.delegate)

    window.tree.setHeaderHidden(False)
    window.tree.setIndentation(20)
    window.tree.setAlternatingRowColors(False)
    window.tree.setAnimated(True)
    window.tree.setUniformRowHeights(True)
    window.tree.setVerticalScrollMode(QTreeView.ScrollPerItem)
    window.tree.setSelectionMode(QTreeView.ExtendedSelection)
    window.tree.setSelectionBehavior(QTreeView.SelectRows)
    window.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window._default_tree_style = style_sheets.build_default_tree_style()
    window.tree.setStyleSheet(window._default_tree_style)

    window.model = QStandardItemModel()
    tree_rows.set_main_tree_headers(window.model)
    window.tree.setModel(window.model)
    window.set_column_widths()

    window.tree_view_event_filter = TreeViewEventFilter(window.tree, window)
    window.tree.viewport().installEventFilter(window.tree_view_event_filter)

    window.tune_delegate = TuneComboBoxDelegate(window.tree)
    window.tree.setItemDelegateForColumn(3, window.tune_delegate)

    window._content_splitter = QSplitter(Qt.Vertical)
    window._content_splitter.setChildrenCollapsible(False)
    window._content_splitter.setHandleWidth(6)
    window._tree_view_container = QWidget(window)
    tree_view_layout = QHBoxLayout(window._tree_view_container)
    tree_view_layout.setContentsMargins(0, 0, 0, 0)
    tree_view_layout.setSpacing(0)
    tree_view_layout.addWidget(window.tree, 1)

    window._tree_external_v_scrollbar = RoundedScrollBar(Qt.Vertical, window._tree_view_container, show_step_buttons=True)
    window._tree_external_v_scrollbar.setFixedWidth(16)
    window._tree_external_v_scrollbar.setFocusPolicy(Qt.NoFocus)
    tree_view_layout.addWidget(window._tree_external_v_scrollbar)
    _connect_external_tree_scrollbar(window)
    _sync_external_tree_scrollbar(window)

    window._content_splitter.addWidget(window._tree_view_container)

    window._bottom_output_panel = BottomOutputPanel(window)
    window._embedded_terminal = window._bottom_output_panel.terminal_widget
    window._embedded_terminal.set_terminal_background(window._get_xmeta_background_color(), restart_if_running=False)
    window._session_log_widget = window._bottom_output_panel.log_widget
    window._bottom_output_panel.terminal_follow_run_changed.connect(window.set_terminal_follow_run_enabled)
    window._bottom_output_panel.set_terminal_follow_run_enabled(window._terminal_follow_run)
    window._embedded_terminal.close_requested.connect(window.hide_embedded_terminal_panel)
    window._embedded_terminal.external_requested.connect(window.open_external_terminal)
    window._session_log_widget.close_requested.connect(window.hide_bottom_output_panel)
    window._content_splitter.addWidget(window._bottom_output_panel)

    window.left_sidebar = WorkspaceSidebar(window)
    window._left_sidebar_default_width = 208
    window.left_sidebar.setFixedWidth(window._left_sidebar_default_width)
    window._left_sidebar_visible = True
    window.left_sidebar.scope_changed.connect(window.on_left_sidebar_scope_changed)
    window.left_sidebar.category_changed.connect(window.on_left_sidebar_category_changed)

    window._content_row = QWidget(window)
    content_row_layout = QHBoxLayout(window._content_row)
    content_row_layout.setContentsMargins(0, 0, 0, 0)
    content_row_layout.setSpacing(0)
    content_row_layout.addWidget(window.left_sidebar)
    content_row_layout.addWidget(window._content_splitter, 1)

    window._main_layout.addWidget(window._content_row)
    window._set_bottom_output_panel_visible(False)

    window.tree.setContextMenuPolicy(Qt.CustomContextMenu)
    window.tree.customContextMenuRequested.connect(window.show_context_menu)
    window.tree.doubleClicked.connect(window.on_tree_double_clicked)

    window._status_bar = StatusBar(window)
    window._status_bar.status_filter_requested.connect(window.on_status_badge_double_clicked)
    window._main_layout.addWidget(window._status_bar)

    window._notification_manager = NotificationManager(window)

    window._init_top_panel_background()
    window._setup_keyboard_shortcuts()
    window._apply_initial_window_width()
    window.on_run_changed()
    runtime_controller.init_runtime_observers(window)
    window.expand_tree_default()


def set_left_sidebar_visible(window, visible: bool) -> None:
    """Show or hide the codex-style left sidebar."""
    if not hasattr(window, "left_sidebar"):
        return
    is_visible = bool(visible)
    if is_visible == bool(getattr(window, "_left_sidebar_visible", True)):
        return

    target_sidebar_width = window._left_sidebar_default_width if is_visible else 0
    previous_target_viewport_width = getattr(window, "_layout_target_viewport_width", None)
    window._layout_target_viewport_width = _estimate_tree_viewport_width_after_sidebar_toggle(
        window,
        target_sidebar_width,
    )
    transition_revision = _show_content_row_transition_overlay(window)
    _begin_tree_layout_transaction(window)
    try:
        window._left_sidebar_visible = is_visible
        if not is_visible and hasattr(window, "clear_left_sidebar_selection"):
            window.clear_left_sidebar_selection()

        window.left_sidebar.setFixedWidth(target_sidebar_width)
        window.left_sidebar.setEnabled(is_visible)
        window.left_sidebar.show()
        if hasattr(window, "_top_panel_left_placeholder_toggle_button"):
            button = window._top_panel_left_placeholder_toggle_button
            button.blockSignals(True)
            button.setChecked(is_visible)
            button.blockSignals(False)

        _activate_layout_after_sidebar_toggle(window)

        if not is_visible and hasattr(window, "show_full_target_view"):
            window.show_full_target_view()

        _refresh_tree_layout_after_sidebar_toggle(window)
    finally:
        _end_tree_layout_transaction(window)
        window._layout_target_viewport_width = previous_target_viewport_width
        _schedule_content_row_transition_overlay_clear(window, transition_revision)


def _activate_layout_after_sidebar_toggle(window) -> None:
    """Apply layout geometry immediately before recomputing tree widths."""
    content_row = getattr(window, "_content_row", None)
    if content_row is not None and content_row.layout() is not None:
        content_row.layout().activate()
        content_row.updateGeometry()
    main_layout = getattr(window, "_main_layout", None)
    if main_layout is not None:
        main_layout.activate()
    _sync_external_tree_scrollbar(window)


def _show_content_row_transition_overlay(window) -> int:
    """Freeze the visible content row while sidebar layout changes commit underneath."""
    current_revision = int(getattr(window, "_content_row_transition_revision", 0)) + 1
    window._content_row_transition_revision = current_revision
    content_row = getattr(window, "_content_row", None)
    if content_row is None or not content_row.isVisible():
        return current_revision

    width = content_row.width()
    height = content_row.height()
    if width <= 0 or height <= 0:
        return current_revision

    existing_overlay = getattr(window, "_content_row_transition_overlay", None)
    if existing_overlay is not None:
        existing_overlay.deleteLater()

    overlay = QLabel(content_row)
    overlay.setObjectName("contentRowTransitionOverlay")
    overlay.setGeometry(content_row.rect())
    overlay.setPixmap(content_row.grab())
    overlay.setScaledContents(False)
    overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    overlay.show()
    overlay.raise_()
    window._content_row_transition_overlay = overlay
    return current_revision


def _schedule_content_row_transition_overlay_clear(window, revision: int) -> None:
    """Clear one frozen content overlay after the final layout settles."""
    QTimer.singleShot(0, lambda: _clear_content_row_transition_overlay(window, revision))


def _clear_content_row_transition_overlay(window, revision: int) -> None:
    """Drop one frozen content overlay when it still belongs to the latest transition."""
    if revision != int(getattr(window, "_content_row_transition_revision", 0)):
        return

    overlay = getattr(window, "_content_row_transition_overlay", None)
    if overlay is None:
        return
    window._content_row_transition_overlay = None
    overlay.deleteLater()


def _connect_external_tree_scrollbar(window) -> None:
    """Mirror the hidden internal tree scrollbar onto the fixed outer gutter."""
    if not hasattr(window, "tree") or not hasattr(window, "_tree_external_v_scrollbar"):
        return

    internal_scrollbar = window.tree.verticalScrollBar()
    external_scrollbar = window._tree_external_v_scrollbar

    internal_scrollbar.rangeChanged.connect(lambda *_: _sync_external_tree_scrollbar(window))
    internal_scrollbar.valueChanged.connect(lambda *_: _sync_external_tree_scrollbar(window))
    external_scrollbar.valueChanged.connect(lambda value: internal_scrollbar.setValue(value))


def _sync_external_tree_scrollbar(window) -> None:
    """Keep the fixed outer scrollbar in sync with the hidden tree scrollbar."""
    if not hasattr(window, "tree") or not hasattr(window, "_tree_external_v_scrollbar"):
        return

    internal_scrollbar = window.tree.verticalScrollBar()
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
    external_scrollbar.update()


def _estimate_tree_viewport_width_after_sidebar_toggle(window, target_sidebar_width: int) -> Optional[int]:
    """Predict the tree viewport width after one sidebar width change."""
    if not hasattr(window, "tree") or window.tree is None:
        return None
    current_viewport_width = window.tree.viewport().width()
    if current_viewport_width <= 0:
        return None
    current_sidebar_width = window.left_sidebar.width() if hasattr(window, "left_sidebar") else 0
    viewport_delta = int(current_sidebar_width) - int(target_sidebar_width)
    target_viewport_width = current_viewport_width + viewport_delta
    if target_viewport_width <= 0:
        return None
    return target_viewport_width


def _begin_tree_layout_transaction(window) -> None:
    """Freeze tree/header painting so sidebar toggles commit as one visual update."""
    depth = int(getattr(window, "_tree_layout_transaction_depth", 0))
    window._tree_layout_transaction_depth = depth + 1
    if depth > 0 or not hasattr(window, "tree") or window.tree is None:
        return

    tree = window.tree
    header = tree.header()
    vertical_scrollbar = tree.verticalScrollBar()
    horizontal_scrollbar = tree.horizontalScrollBar()
    external_vertical_scrollbar = getattr(window, "_tree_external_v_scrollbar", None)
    window._tree_layout_transaction_state = {
        "previous_suspend": bool(getattr(window, "_suspend_header_layout_updates", False)),
        "previous_tree_updates": tree.updatesEnabled(),
        "previous_header_updates": header.updatesEnabled() if header is not None else True,
        "previous_header_blocked": header.signalsBlocked() if header is not None else False,
        "previous_v_scroll_updates": vertical_scrollbar.updatesEnabled() if vertical_scrollbar is not None else True,
        "previous_h_scroll_updates": horizontal_scrollbar.updatesEnabled() if horizontal_scrollbar is not None else True,
        "previous_v_scroll_blocked": vertical_scrollbar.signalsBlocked() if vertical_scrollbar is not None else False,
        "previous_h_scroll_blocked": horizontal_scrollbar.signalsBlocked() if horizontal_scrollbar is not None else False,
        "previous_external_v_scroll_updates": (
            external_vertical_scrollbar.updatesEnabled() if external_vertical_scrollbar is not None else True
        ),
        "previous_external_v_scroll_blocked": (
            external_vertical_scrollbar.signalsBlocked() if external_vertical_scrollbar is not None else False
        ),
    }
    window._suspend_header_layout_updates = True
    tree.setUpdatesEnabled(False)
    if header is not None:
        header.setUpdatesEnabled(False)
        header.blockSignals(True)
    if vertical_scrollbar is not None:
        vertical_scrollbar.setUpdatesEnabled(False)
        vertical_scrollbar.blockSignals(True)
    if horizontal_scrollbar is not None:
        horizontal_scrollbar.setUpdatesEnabled(False)
        horizontal_scrollbar.blockSignals(True)
    if external_vertical_scrollbar is not None:
        external_vertical_scrollbar.setUpdatesEnabled(False)
        external_vertical_scrollbar.blockSignals(True)


def _end_tree_layout_transaction(window) -> None:
    """Restore tree/header painting after one batched sidebar toggle."""
    depth = int(getattr(window, "_tree_layout_transaction_depth", 0))
    if depth <= 0:
        return
    depth -= 1
    window._tree_layout_transaction_depth = depth
    if depth > 0 or not hasattr(window, "tree") or window.tree is None:
        return

    tree = window.tree
    header = tree.header()
    vertical_scrollbar = tree.verticalScrollBar()
    horizontal_scrollbar = tree.horizontalScrollBar()
    external_vertical_scrollbar = getattr(window, "_tree_external_v_scrollbar", None)
    state = getattr(window, "_tree_layout_transaction_state", {}) or {}
    window._suspend_header_layout_updates = bool(state.get("previous_suspend", False))
    if header is not None:
        header.blockSignals(bool(state.get("previous_header_blocked", False)))
        header.setUpdatesEnabled(bool(state.get("previous_header_updates", True)))
    if vertical_scrollbar is not None:
        vertical_scrollbar.blockSignals(bool(state.get("previous_v_scroll_blocked", False)))
        vertical_scrollbar.setUpdatesEnabled(bool(state.get("previous_v_scroll_updates", True)))
    if horizontal_scrollbar is not None:
        horizontal_scrollbar.blockSignals(bool(state.get("previous_h_scroll_blocked", False)))
        horizontal_scrollbar.setUpdatesEnabled(bool(state.get("previous_h_scroll_updates", True)))
    if external_vertical_scrollbar is not None:
        external_vertical_scrollbar.blockSignals(bool(state.get("previous_external_v_scroll_blocked", False)))
        external_vertical_scrollbar.setUpdatesEnabled(bool(state.get("previous_external_v_scroll_updates", True)))
    tree.setUpdatesEnabled(bool(state.get("previous_tree_updates", True)))
    tree.viewport().update()
    if header is not None:
        header.viewport().update()
    if vertical_scrollbar is not None:
        vertical_scrollbar.update()
    if horizontal_scrollbar is not None:
        horizontal_scrollbar.update()
    _sync_external_tree_scrollbar(window)


def _refresh_tree_layout_after_sidebar_toggle(window) -> None:
    """Re-fit the tree after sidebar visibility changes alter the viewport width."""
    if not hasattr(window, "tree") or window.tree is None:
        return
    if int(getattr(window, "_tree_layout_transaction_depth", 0)) > 0:
        if hasattr(window, "_apply_adaptive_target_column_width"):
            window._apply_adaptive_target_column_width()
        if hasattr(window, "_fill_trailing_blank_with_last_column"):
            window._fill_trailing_blank_with_last_column()
        return
    tree = window.tree
    header = tree.header()
    previous_suspend = bool(getattr(window, "_suspend_header_layout_updates", False))
    previous_tree_updates = tree.updatesEnabled()
    previous_header_updates = header.updatesEnabled() if header is not None else True
    previous_header_blocked = header.signalsBlocked() if header is not None else False

    window._suspend_header_layout_updates = True
    tree.setUpdatesEnabled(False)
    if header is not None:
        header.setUpdatesEnabled(False)
        header.blockSignals(True)

    try:
        if hasattr(window, "_apply_adaptive_target_column_width"):
            window._apply_adaptive_target_column_width()
        if hasattr(window, "_fill_trailing_blank_with_last_column"):
            window._fill_trailing_blank_with_last_column()
    finally:
        window._suspend_header_layout_updates = previous_suspend
        if header is not None:
            header.blockSignals(previous_header_blocked)
            header.setUpdatesEnabled(previous_header_updates)
        tree.setUpdatesEnabled(previous_tree_updates)
        tree.viewport().update()
        if header is not None:
            header.viewport().update()


def toggle_left_sidebar(window) -> bool:
    """Toggle left sidebar visibility and return the new state."""
    current_visible = bool(getattr(window, "_left_sidebar_visible", True))
    set_left_sidebar_visible(window, not current_visible)
    return bool(getattr(window, "_left_sidebar_visible", True))
