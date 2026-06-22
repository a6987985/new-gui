"""Top-panel and tree-area builder helpers for MainWindow."""

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QStandardItemModel
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTabWidget,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from new_gui.model.services import view_tabs
from new_gui.model.services import tree_rows
from new_gui.presentation.styles import style_sheets
from new_gui.presentation.presenters import runtime_controller
from new_gui.presentation.presenters import external_scrollbar_controller
from new_gui.presentation.styles.top_panel_widget_styles import (
    build_run_selector_style,
    build_tab_close_button_style,
)
from new_gui.presentation.views.builders.top_button_layout import get_top_button_anchor_y, rebuild_top_action_buttons
from new_gui.presentation.views.builders.top_button_specs import (
    DEFAULT_TOP_BUTTON_IDS,
    get_top_button_choices,
    normalize_visible_top_buttons,
)
from new_gui.presentation.views.widgets.bounded_combo import BoundedComboBox
from new_gui.presentation.views.widgets.notifications import NotificationManager
from new_gui.presentation.views.widgets.scrollbars import RoundedScrollBar
from new_gui.presentation.views.widgets.status_bar import StatusBar
from new_gui.presentation.views.widgets.tree_view import ColorTreeView, TreeViewEventFilter
from new_gui.presentation.views.widgets.bottom_output_panel import BottomOutputPanel
from new_gui.presentation.views.widgets.workspace_sidebar import WorkspaceSidebar
from new_gui.presentation.views.widgets.delegates import BorderItemDelegate, TuneComboBoxDelegate
from new_gui.presentation.views.widgets.filter_header import FilterHeaderView
from new_gui.presentation.views.widgets.labels import ClickableLabel


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
        "border: none;",
        "border-bottom: none;",
    )
    window.tab_widget.setStyleSheet(window._default_tab_widget_style)
    tab_inner_layout = QHBoxLayout(window.tab_widget)
    tab_inner_layout.setContentsMargins(6, 3, 6, 3)
    tab_inner_layout.setSpacing(4)

    window.tab_label = ClickableLabel("")
    window.tab_label.clicked.connect(window._on_top_tab_label_clicked)
    window.tab_label.doubleClicked.connect(window._on_top_tab_label_double_clicked)
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
    window.tree.setAnimated(False)
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
    tree_view_layout.setContentsMargins(0, 0, 16, 0)
    tree_view_layout.setSpacing(0)
    tree_view_layout.addWidget(window.tree, 1)

    window._content_splitter.addWidget(window._tree_view_container)

    window._bottom_output_panel = BottomOutputPanel(window)
    window._embedded_terminal = window._bottom_output_panel.terminal_widget
    window._embedded_terminal.set_terminal_background(window._get_xmeta_background_color(), restart_if_running=False)
    window._session_log_widget = window._bottom_output_panel.log_widget
    window._bottom_output_panel.terminal_follow_run_changed.connect(window.set_terminal_follow_run_enabled)
    window._bottom_output_panel.terminal_content_fill_changed.connect(
        window.set_terminal_output_content_filled
    )
    window._bottom_output_panel.set_terminal_follow_run_enabled(window._terminal_follow_run)
    window._embedded_terminal.close_requested.connect(window.hide_embedded_terminal_panel)
    window._embedded_terminal.external_requested.connect(window.open_external_terminal)
    window._session_log_widget.close_requested.connect(window.hide_bottom_output_panel)
    window._content_splitter.addWidget(window._bottom_output_panel)

    window.left_sidebar = WorkspaceSidebar(window)
    window._left_sidebar_default_width = 244
    window.left_sidebar.setFixedWidth(window._left_sidebar_default_width)
    window._left_sidebar_visible = True
    window._left_sidebar_content_mode_visible = True
    window.left_sidebar.scope_changed.connect(window.on_left_sidebar_scope_changed)
    window.left_sidebar.category_changed.connect(window.on_left_sidebar_category_changed)

    window._main_view_page = QWidget(window)
    main_view_layout = QVBoxLayout(window._main_view_page)
    main_view_layout.setContentsMargins(0, 0, 0, 0)
    main_view_layout.setSpacing(0)
    main_view_layout.addWidget(window._content_splitter)

    window._graph_view_page = QWidget(window)
    window._graph_view_layout = QVBoxLayout(window._graph_view_page)
    window._graph_view_layout.setContentsMargins(0, 0, 0, 0)
    window._graph_view_layout.setSpacing(0)

    window._content_mode_tabs = QTabWidget(window)
    window._content_mode_tabs.addTab(window._main_view_page, "TreeView")
    window._content_mode_tabs.addTab(window._graph_view_page, "Dependency Graph")
    window._content_mode_tabs.setTabEnabled(1, True)
    window._content_mode_tabs.setCurrentWidget(window._main_view_page)
    window._content_mode_tabs.tabBar().hide()
    window._content_mode_tabs.currentChanged.connect(window._on_content_mode_tab_changed)

    window._content_row = QWidget(window)
    content_row_layout = QHBoxLayout(window._content_row)
    content_row_layout.setContentsMargins(0, 0, 0, 0)
    content_row_layout.setSpacing(0)
    content_row_layout.addWidget(window.left_sidebar)
    content_row_layout.addWidget(window._content_mode_tabs, 1)

    window._tree_external_v_scrollbar = RoundedScrollBar(Qt.Vertical, window._content_row, show_step_buttons=True)
    window._tree_external_v_scrollbar.setFixedWidth(16)
    window._tree_external_v_scrollbar.setFocusPolicy(Qt.NoFocus)
    external_scrollbar_controller.connect_tree_scrollbar(window)
    external_scrollbar_controller.sync_external_scrollbar(window)

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
    QTimer.singleShot(0, window.set_column_widths)
    runtime_controller.init_runtime_observers(window)
    window.expand_tree_default()


def set_left_sidebar_visible(window, visible: bool) -> None:
    """Show or hide the codex-style left sidebar."""
    if not hasattr(window, "left_sidebar"):
        return
    is_visible = bool(visible)
    if is_visible == bool(getattr(window, "_left_sidebar_visible", True)):
        return

    content_mode_visible = bool(getattr(window, "_left_sidebar_content_mode_visible", True))
    effective_visible = is_visible and content_mode_visible
    target_sidebar_width = window._left_sidebar_default_width if effective_visible else 0
    had_active_sidebar_filter = False
    if not is_visible and hasattr(window, "get_active_category_target_set"):
        had_active_sidebar_filter = window.get_active_category_target_set() is not None
    had_sidebar_snapshot = bool(getattr(window, "_sidebar_filter_snapshot", None))
    window._left_sidebar_visible = is_visible
    if not is_visible and hasattr(window, "clear_left_sidebar_selection"):
        window.clear_left_sidebar_selection()

    if hasattr(window, "_top_panel_left_placeholder_toggle_button"):
        button = window._top_panel_left_placeholder_toggle_button
        button.blockSignals(True)
        button.setChecked(is_visible)
        button.blockSignals(False)

    _apply_left_sidebar_layout_state(
        window,
        effective_visible,
        target_sidebar_width,
        had_active_sidebar_filter,
        had_sidebar_snapshot,
    )


def set_left_sidebar_content_mode_visible(window, visible: bool) -> None:
    """Show or hide the sidebar for content-tab switches without clearing filters."""
    if not hasattr(window, "left_sidebar"):
        return
    is_visible = bool(visible)
    if is_visible == bool(getattr(window, "_left_sidebar_content_mode_visible", True)):
        return

    window._left_sidebar_content_mode_visible = is_visible
    base_visible = bool(getattr(window, "_left_sidebar_visible", True))
    effective_visible = base_visible and is_visible
    target_sidebar_width = window._left_sidebar_default_width if effective_visible else 0
    _apply_left_sidebar_layout_state(
        window,
        effective_visible,
        target_sidebar_width,
        False,
        False,
    )


def _apply_left_sidebar_layout_state(
    window,
    is_visible: bool,
    target_sidebar_width: int,
    had_active_sidebar_filter: bool,
    had_sidebar_snapshot: bool,
) -> None:
    """Commit the real sidebar layout state once without intermediate width animation."""
    tree = getattr(window, "tree", None)
    header = tree.header() if tree is not None else None
    horizontal_scrollbar = tree.horizontalScrollBar() if tree is not None else None
    previous_tree_updates = tree.updatesEnabled() if tree is not None else True
    previous_header_updates = header.updatesEnabled() if header is not None else True
    previous_horizontal_policy = tree.horizontalScrollBarPolicy() if tree is not None else Qt.ScrollBarAsNeeded
    previous_horizontal_blocked = (
        horizontal_scrollbar.signalsBlocked() if horizontal_scrollbar is not None else False
    )
    transaction_depth = int(getattr(window, "_tree_layout_transaction_depth", 0))
    window._tree_layout_transaction_depth = transaction_depth + 1
    if tree is not None:
        tree.setUpdatesEnabled(False)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    if header is not None:
        header.setUpdatesEnabled(False)
    if horizontal_scrollbar is not None:
        horizontal_scrollbar.blockSignals(True)

    sidebar = window.left_sidebar
    previous_layout_target_viewport_width = getattr(window, "_layout_target_viewport_width", None)
    try:
        _prepare_tree_viewport_width_for_sidebar_toggle(window, target_sidebar_width)
        if is_visible:
            sidebar.setFixedWidth(target_sidebar_width)
            sidebar.setEnabled(True)
            sidebar.show()
        else:
            sidebar.setEnabled(False)
            sidebar.hide()
            sidebar.setFixedWidth(0)

        _activate_layout_after_sidebar_toggle(window)

        if not is_visible and hasattr(window, "show_full_target_view"):
            if had_active_sidebar_filter or had_sidebar_snapshot:
                window.show_full_target_view(force_rebuild=False)
            window._sidebar_filter_snapshot = None
            window._main_view_tab_state = view_tabs.get_main_run_tab_state()
            if getattr(window, "_active_content_mode", "main") == "graph" and hasattr(window, "_apply_tab_state"):
                window._apply_tab_state(view_tabs.get_graph_tab_state())

        _refresh_tree_layout_after_sidebar_toggle(window)
        external_scrollbar_controller.sync_external_scrollbar(window)
        _ensure_tree_header_visible(window)
    finally:
        transaction_depth = int(getattr(window, "_tree_layout_transaction_depth", 1))
        window._tree_layout_transaction_depth = max(0, transaction_depth - 1)
        window._layout_target_viewport_width = previous_layout_target_viewport_width
        if horizontal_scrollbar is not None:
            horizontal_scrollbar.blockSignals(previous_horizontal_blocked)
        if header is not None:
            header.setUpdatesEnabled(previous_header_updates)
        if tree is not None:
            tree.setHorizontalScrollBarPolicy(previous_horizontal_policy)
            tree.setUpdatesEnabled(previous_tree_updates)
        if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0 and tree is not None:
            tree.viewport().update()
            if header is not None:
                header.viewport().update()


def _prepare_tree_viewport_width_for_sidebar_toggle(window, target_sidebar_width: int) -> None:
    """Precompute the final tree viewport width for one sidebar layout transaction."""
    content_row = getattr(window, "_content_row", None)
    tree = getattr(window, "tree", None)
    if content_row is None or tree is None:
        return

    content_width = max(0, content_row.width())
    if content_width <= 0:
        return

    tree_container = getattr(window, "_tree_view_container", None)
    margins_width = 0
    if tree_container is not None and tree_container.layout() is not None:
        margins = tree_container.layout().contentsMargins()
        margins_width = margins.left() + margins.right()

    target_width = content_width - max(0, int(target_sidebar_width or 0)) - margins_width
    window._layout_target_viewport_width = max(0, target_width)


def _ensure_tree_header_visible(window) -> None:
    """Force tree header visibility after sidebar layout transitions."""
    if not hasattr(window, "tree") or window.tree is None:
        return
    if hasattr(window, "_suspend_header_layout_updates"):
        window._suspend_header_layout_updates = False
    if hasattr(window, "header") and window.header is not None and window.tree.header() is not window.header:
        window.tree.setHeader(window.header)
    window.tree.setHeaderHidden(False)
    header = window.tree.header()
    if header is not None:
        header.blockSignals(False)
        header.setUpdatesEnabled(True)
        header.setVisible(True)
        header.show()
        if header.height() <= 0:
            header.setFixedHeight(46)
        if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0:
            header.viewport().update()
    if int(getattr(window, "_tree_layout_transaction_depth", 0)) <= 0:
        window.tree.setUpdatesEnabled(True)


def _activate_layout_after_sidebar_toggle(window) -> None:
    """Apply layout geometry immediately before recomputing tree widths."""
    content_row = getattr(window, "_content_row", None)
    if content_row is not None and content_row.layout() is not None:
        content_row.layout().activate()
        content_row.updateGeometry()
    main_layout = getattr(window, "_main_layout", None)
    if main_layout is not None:
        main_layout.activate()
    external_scrollbar_controller.position_external_scrollbar(window)


def _refresh_tree_layout_after_sidebar_toggle(window) -> None:
    """Re-fit the tree after sidebar visibility changes alter the viewport width."""
    if not hasattr(window, "tree") or window.tree is None:
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
