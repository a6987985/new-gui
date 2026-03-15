"""Top-panel and tree-area builder helpers for MainWindow."""

from PyQt5.QtCore import QFileSystemWatcher, QTimer, Qt
from PyQt5.QtGui import QColor, QStandardItemModel
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from new_gui.config.settings import BACKUP_TIMER_INTERVAL_MS
from new_gui.services import tree_rows, view_tabs
from new_gui.ui import style_sheets
from new_gui.ui.widgets.bounded_combo import BoundedComboBox
from new_gui.ui.widgets.notifications import NotificationManager
from new_gui.ui.widgets.status_bar import StatusBar
from new_gui.ui.widgets.tree_view import ColorTreeView, TreeViewEventFilter
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

    row1_layout = QHBoxLayout()
    row1_layout.setContentsMargins(0, 0, 0, 0)
    row1_layout.setSpacing(8)

    window.combo = BoundedComboBox()
    window.populate_run_combo()
    window.combo.setMinimumWidth(300)
    window.combo.currentIndexChanged.connect(window.on_run_changed)
    window.combo.setStyleSheet(
        """
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #a0a0a0;
                border-radius: 6px;
                padding: 6px 12px;
                padding-right: 32px;
                color: #000000;
                font-size: 14px;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 1px solid #808080;
                background-color: #f5f5f5;
            }
            QComboBox:focus {
                border: 1px solid #808080;
            }
            QComboBox:disabled {
                background-color: #EEF1F4;
                border: 1px solid #9BA5B7;
                color: #9BA5B7;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
                subcontrol-origin: padding;
                subcontrol-position: right center;
            }
            QComboBox:on {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                border-bottom: none;
            }
            QComboBox QAbstractItemView {
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #a0a0a0;
                border-top: none;
                selection-background-color: #EEF1F4;
                selection-color: #000000;
                outline: none;
                padding-left: 10px;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
            }
        """
    )

    btn_style = """
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #cfd8e3;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 500;
            font-size: 12px;
            color: #314154;
        }
        QPushButton:hover {
            background-color: #f7fbff;
            border: 1px solid #7ba4d9;
            color: #0f5fa8;
        }
        QPushButton:pressed {
            background-color: #e7f1fb;
            border: 1px solid #5d8fcf;
        }
    """

    action_btn_style = """
        QPushButton {
            background-color: #1976d2;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 600;
            font-size: 12px;
            color: #ffffff;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0d47a1;
        }
    """

    warning_btn_style = """
        QPushButton {
            background-color: #fff8f8;
            border: 1px solid #f3c5c5;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 600;
            font-size: 12px;
            color: #b42318;
        }
        QPushButton:hover {
            background-color: #ffefef;
            border: 1px solid #e38b8b;
        }
        QPushButton:pressed {
            background-color: #ffdede;
        }
    """

    window.buttons_row1 = ["run all", "run", "stop", "skip", "unskip", "invalid"]
    window.buttons_row2 = ["term", "csh", "log", "cmd", "trace up", "trace dn"]

    row1_layout.addWidget(window.combo)

    button_container = QWidget(window.top_panel)
    button_container.setAttribute(Qt.WA_TranslucentBackground, True)
    button_container.setStyleSheet("background: transparent; border: none;")
    button_layout = QHBoxLayout(button_container)
    button_layout.setContentsMargins(0, 0, 0, 0)
    button_layout.setSpacing(8)

    bt_runall = QPushButton("Run All")
    bt_runall.setStyleSheet(action_btn_style)
    bt_runall.clicked.connect(lambda: window.start("XMeta_run all"))
    button_layout.addWidget(bt_runall)

    bt_run = QPushButton("Run")
    bt_run.setStyleSheet(action_btn_style)
    bt_run.clicked.connect(lambda: window.start("XMeta_run"))
    button_layout.addWidget(bt_run)

    bt_stop = QPushButton("Stop")
    bt_stop.setStyleSheet(warning_btn_style)
    bt_stop.clicked.connect(lambda: window.start("XMeta_stop"))
    button_layout.addWidget(bt_stop)

    bt_skip = QPushButton("Skip")
    bt_skip.setStyleSheet(warning_btn_style)
    bt_skip.clicked.connect(lambda: window.start("XMeta_skip"))
    button_layout.addWidget(bt_skip)

    bt_unskip = QPushButton("Unskip")
    bt_unskip.setStyleSheet(btn_style)
    bt_unskip.clicked.connect(lambda: window.start("XMeta_unskip"))
    button_layout.addWidget(bt_unskip)

    bt_invalid = QPushButton("Invalid")
    bt_invalid.setStyleSheet(warning_btn_style)
    bt_invalid.clicked.connect(lambda: window.start("XMeta_invalid"))
    button_layout.addWidget(bt_invalid)

    button_container.adjustSize()
    window._top_button_container = button_container
    window._top_button_placeholder = QWidget()
    window._top_button_placeholder.setStyleSheet("background: transparent; border: none;")
    window._top_button_placeholder.setFixedWidth(button_container.sizeHint().width())
    row1_layout.addWidget(window._top_button_placeholder)

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
    window.tab_close_btn.setStyleSheet(
        """
            QPushButton {
                border: none;
                border-radius: 10px;
                color: #999999;
                font-weight: bold;
                background: transparent;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #ef5350;
                color: white;
            }
        """
    )

    tab_inner_layout.addWidget(window.tab_label)
    tab_inner_layout.addWidget(window.tab_close_btn)

    tab_layout.addWidget(window.tab_widget)
    tab_layout.addStretch()
    row1_layout.insertWidget(1, window.tab_bar, 1)
    QTimer.singleShot(0, window._position_top_action_buttons)

    window.tree = ColorTreeView()

    window.header = FilterHeaderView(Qt.Horizontal, window.tree, filter_column=1)
    window.tree.setHeader(window.header)
    window.header.filter_changed.connect(window._on_header_filter_changed)
    window.header.level_double_clicked.connect(window.toggle_tree_expansion)

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

    window._main_layout.addWidget(window.tree)

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

    window.status_watcher = QFileSystemWatcher(window)
    window.status_watcher.directoryChanged.connect(window.on_status_directory_changed)
    window.status_watcher.fileChanged.connect(window.on_status_file_changed)

    window.watched_status_dirs = set()
    window.setup_status_watcher()

    window.backup_timer = QTimer()
    window.backup_timer.timeout.connect(window.change_run)
    window.backup_timer.start(BACKUP_TIMER_INTERVAL_MS)

    window.debounce_timer = QTimer()
    window.debounce_timer.setSingleShot(True)
    window.debounce_timer.timeout.connect(window.change_run)

    window.expand_tree_default()
