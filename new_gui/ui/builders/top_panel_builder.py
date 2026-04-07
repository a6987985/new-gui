"""Top-panel and tree-area builder helpers for MainWindow."""

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QStandardItemModel
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
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
    window.tab_label.setToolTip("Double-click to Expand/Collapse All")
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
    window._content_splitter.addWidget(window.tree)

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
    window._left_sidebar_visible = is_visible
    window.left_sidebar.setVisible(is_visible)
    if is_visible and hasattr(window, "_left_sidebar_default_width"):
        window.left_sidebar.setFixedWidth(window._left_sidebar_default_width)
    if hasattr(window, "_top_panel_left_placeholder_toggle_button"):
        button = window._top_panel_left_placeholder_toggle_button
        button.blockSignals(True)
        button.setChecked(is_visible)
        button.blockSignals(False)
    QTimer.singleShot(0, lambda: _refresh_tree_layout_after_sidebar_toggle(window))


def _refresh_tree_layout_after_sidebar_toggle(window) -> None:
    """Re-fit the tree after sidebar visibility changes alter the viewport width."""
    if not hasattr(window, "tree") or window.tree is None:
        return
    if hasattr(window, "_apply_adaptive_target_column_width"):
        window._apply_adaptive_target_column_width()
    if hasattr(window, "_fill_trailing_blank_with_last_column"):
        window._fill_trailing_blank_with_last_column()


def toggle_left_sidebar(window) -> bool:
    """Toggle left sidebar visibility and return the new state."""
    current_visible = bool(getattr(window, "_left_sidebar_visible", True))
    set_left_sidebar_visible(window, not current_visible)
    return bool(getattr(window, "_left_sidebar_visible", True))
