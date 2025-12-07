import sys
import os
import re
import subprocess
import time
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, Qt, QTimer, QObject, QEvent, QModelIndex, QRect, pyqtSignal, QItemSelectionModel
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton, QCompleter,
                             QTreeView, QLineEdit, QHeaderView, QStyleFactory,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                             QSizePolicy, QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QAbstractItemView, QStyleOptionComboBox,
                             QMenuBar, QAction)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont, QFontDatabase, QTextCursor, QPen



class BorderItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 1. Manually draw background from model (Status Colors)
        bg_brush = index.data(Qt.BackgroundRole)
        if bg_brush:
            painter.save()
            if isinstance(bg_brush, QBrush):
                painter.fillRect(option.rect, bg_brush)
            elif isinstance(bg_brush, QColor):
                painter.fillRect(option.rect, bg_brush)
            painter.restore()

        # 2. Manually draw Hover/Selection Background
        painter.save()
        bg_rect = QRect(option.rect)
        
        # If first column, extend rect to the left edge to cover branch/indentation
        if index.column() == 0:
            bg_rect.setLeft(0)
            
        if option.state & QStyle.State_Selected:
            painter.fillRect(bg_rect, QColor(0xC0, 0xC0, 0xBE))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(bg_rect, QColor(230, 240, 255, 150)) # Semi-transparent
        painter.restore()

        # 3. Let the style draw the content (text)
        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_MouseOver
        super().paint(painter, opt, index)
        
        # 4. Draw custom border on top
        painter.save()
        
        # Helper to draw row-style border
        def draw_row_border(color):
            painter.setPen(QPen(color, 1))
            painter.setBrush(Qt.NoBrush)
            r = QRect(option.rect)
            
            # If first column, extend to left edge to cover branch/indentation
            if index.column() == 0:
                r.setLeft(0)
            
            # Draw Top and Bottom lines for ALL cells
            painter.drawLine(r.left(), r.top(), r.right(), r.top())
            painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())
            
            # Draw Left line ONLY for the first column (at x=0)
            if index.column() == 0:
                painter.drawLine(r.left(), r.top(), r.left(), r.bottom())
                
            # Draw Right line ONLY for the last column
            model = index.model()
            if model and index.column() == model.columnCount(index.parent()) - 1:
                painter.drawLine(r.right(), r.top(), r.right(), r.bottom())

        if option.state & QStyle.State_MouseOver:
            draw_row_border(QColor(230, 240, 255))
            
        if option.state & QStyle.State_Selected:
            draw_row_border(QColor(0xC0, 0xC0, 0xBE))
            
        painter.restore()

class TreeViewEventFilter(QObject):
    """事件过滤器，处理 TreeView 的展开/折叠"""
    def __init__(self, tree_view, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.parent = parent
        self.level_expanded = {}
        self.level_items = {}

    def eventFilter(self, obj, event):
        if not self.tree_view or not obj:
            return False
            
        if obj == self.tree_view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                index = self.tree_view.indexAt(event.pos())
                if index.isValid():
                    column = self.tree_view.columnAt(event.x())
                    if column == 0:
                        model = self.tree_view.model()
                        if not model:
                            return False
                            
                        item = model.itemFromIndex(model.index(index.row(), 0))
                        if item and item.hasChildren():
                            is_expanded = self.tree_view.isExpanded(index)
                            if is_expanded:
                                self.tree_view.collapse(index)
                            else:
                                self.tree_view.expand(index)
                            level = item.text()
                            # Handle case where parent might not have combo_sel or level_expanded initialized
                            if hasattr(self.parent, 'combo_sel') and hasattr(self.parent, 'level_expanded'):
                                run_dir = self.parent.combo_sel
                                if run_dir not in self.parent.level_expanded:
                                    self.parent.level_expanded[run_dir] = {}
                                self.parent.level_expanded[run_dir][level] = not is_expanded
                            return True
                            
        return super().eventFilter(obj, event)

    def toggle_level_items(self, level):
        """切换level对应的items的显示/隐藏状态"""
        if level not in self.level_items:
            return
            
        # 切换展开状态
        self.level_expanded[level] = not self.level_expanded.get(level, True)
        
        # 遍历所有相同level的行
        rows = self.level_items[level]
        if not rows:
            return
            
        # 第一个项目始终显示，其他项目根据展开状态显示/隐藏
        for i, row in enumerate(rows):
            if i == 0:  # 第一个项目
                continue
            self.tree_view.setRowHidden(row, QModelIndex(), not self.level_expanded[level])

class ColorTreeView(QTreeView):
    def drawBranches(self, painter, rect, index):
        # Check if row is selected or current (focused)
        is_selected = self.selectionModel().isSelected(index)
        is_current = (self.currentIndex().row() == index.row() and 
                      self.currentIndex().parent() == index.parent())
        
        painter.save()
        
        # Fill background first
        if is_selected:
            painter.fillRect(rect, QColor("#C0C0BE"))
        else:
            brush = index.data(Qt.BackgroundRole)
            if brush:
                painter.fillRect(rect, brush)
        
        # Draw expand/collapse arrow for branches with children
        if index.model().hasChildren(index):
            from PyQt5.QtGui import QPen, QPolygon
            from PyQt5.QtCore import QPoint
            
            pen = QPen(QColor("#000000"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(QColor("#333333"))
            
            # Calculate arrow position (centered in rect)
            center_x = rect.center().x()
            center_y = rect.center().y()
            arrow_size = 4
            
            if self.isExpanded(index):
                # Down arrow (open/expanded)
                points = QPolygon([
                    QPoint(center_x - arrow_size, center_y - arrow_size//2),
                    QPoint(center_x + arrow_size, center_y - arrow_size//2),
                    QPoint(center_x, center_y + arrow_size//2)
                ])
            else:
                # Right arrow (closed/collapsed)
                points = QPolygon([
                    QPoint(center_x - arrow_size//2, center_y - arrow_size),
                    QPoint(center_x + arrow_size//2, center_y),
                    QPoint(center_x - arrow_size//2, center_y + arrow_size)
                ])
            
            painter.drawPolygon(points)
        
        painter.restore()

class BoundedComboBox(QComboBox):
    """Custom ComboBox with on-demand search mode"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(False) # Default to non-editable
        
        # Add search icon button
        self.search_btn = QPushButton(self)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedSize(20, 20)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #555;
            }
            QPushButton:hover {
                color: #000;
            }
        """)
        # Use a simple text "🔍" or icon if available. Using text for simplicity.
        self.search_btn.setText("🔍") 
        self.search_btn.clicked.connect(self.enable_search_mode)
        
        # Connect signal to exit search mode on selection
        self.currentIndexChanged.connect(self.disable_search_mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position search button to the left of the dropdown arrow
        # Standard arrow width is usually around 20px
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        arrow_width = self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self).width()
        
        btn_size = self.search_btn.size()
        x = self.width() - arrow_width - btn_size.width() - 5 # 5px padding
        y = (self.height() - btn_size.height()) // 2
        self.search_btn.move(x, y)

    def enable_search_mode(self):
        """Enable editing and focus the line edit"""
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        
        # Configure completer if not already done (though MainWindow does it too)
        # Configure completer
        if not self.completer() or self.completer().completionMode() != QCompleter.PopupCompletion:
            completer = QCompleter(self.model(), self)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            self.setCompleter(completer)
            
        self.lineEdit().setFocus()
        self.lineEdit().selectAll()
        
        # Hide search button while searching (optional, but keeps UI clean)
        self.search_btn.hide()

    def disable_search_mode(self):
        """Disable editing and restore search button"""
        self.setEditable(False)
        self.search_btn.show()

    def showPopup(self):
        super().showPopup()
        # Get the popup (the list view that drops down)
        popup = self.view().parentWidget()
        if popup:
            # Get popup's current geometry
            popup_geo = popup.geometry()
            
            # Get main window
            main_window = self.window()
            if main_window:
                # Get window's global position
                window_top = main_window.mapToGlobal(main_window.rect().topLeft()).y()
                # Add title bar height (approximately 30-40 pixels)
                title_bar_height = 40
                min_y = window_top + title_bar_height
                
                # If popup extends above the limit, reposition it
                if popup_geo.top() < min_y:
                    popup_geo.moveTop(min_y)
                    popup.setGeometry(popup_geo)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        # If we lose focus, exit search mode
        # But we need to be careful not to exit if we just clicked the completer popup
        # The focusOutEvent happens when focus goes to another widget.
        
        # If text is empty, restore previous
        if self.lineEdit() and not self.currentText().strip():
             index = self.currentIndex()
             if index >= 0:
                 self.setEditText(self.itemText(index))
        
        # Disable search mode (revert to read-only)
        # We use a timer to allow other events (like completer selection) to process first
        QTimer.singleShot(100, self.disable_search_mode)

class ClickableLabel(QLabel):
    doubleClicked = pyqtSignal()
    
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        # Initialize core variables FIRST
        self.tar_name = []
        self.level_expanded = {}
        self.combo_sel = None
        self.cached_targets_by_level = {} # Cache for search optimization
        self.is_tree_expanded = True  # Track expansion state
        
        # Status colors
        self.colors = {
            'finish': '#98FB98',    # PaleGreen
            'skip': '#FFDAB9',      # PeachPuff
            'running': '#FFFF00',   # Yellow
            'failed': '#FF9999',    # Light Red
            'scheduled': '#87CEEB', # SkyBlue
            'waiting': '#87CEEB',   # SkyBlue
            '': '#FFFFFF'           # White/No status
        }
        
        # Check if mock_runs exists, otherwise check if we are inside a run
        if os.path.exists("mock_runs"):
            self.run_base_dir = "mock_runs"
        elif os.path.exists(".target_dependency.csh"):
            # We are inside a run directory, so scan the parent directory
            self.run_base_dir = ".."
            print(f"Detected run in current directory. Setting base to parent: {os.path.abspath(self.run_base_dir)}")
        else:
            self.run_base_dir = "."
        super().__init__()
        self.setWindowTitle("Console of XMeta/develop-tile @ Meta_Sep05_1045_22091_GUI")
        self.resize(1200, 800)
        # Fade‑in animation for the window
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(800)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.fade_anim.start()
        # Set background image with glass‑morphism overlay

        # Apply a semi‑transparent overlay widget for glass effect
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(255,255,255,0.6); border-radius: 12px;")
        overlay.lower()  # keep behind central widgets
        # Apply gradient background to main window
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e0f7fa, stop:1 #80deea);
            }
        """)
        
        # Create Menu Bar
        self.menu_bar = self.menuBar()
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #cccccc;
                padding: 2px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 12px;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #e6f7ff;
            }
        """)
        
        # Status Menu
        status_menu = self.menu_bar.addMenu("Status")
        
        # Show All Status Action
        show_all_status_action = QAction("Show All Status", self)
        show_all_status_action.triggered.connect(self.show_all_status)
        status_menu.addAction(show_all_status_action)
        
        # Track if we are in "All Status" view mode
        self.is_all_status_view = False
        

        # Main Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignTop)

        # Top Control Panel
        top_panel = QWidget()
        top_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # Apply gradient background and rounded corners
        top_panel.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #a8e6cf, stop:1 #56ab2f);
            border-radius: 12px;
        """)
        # Add subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        top_panel.setGraphicsEffect(shadow)
        # Button hover transition (smooth)
        btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
                color: #222222;
                transition: background-color 0.2s ease;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
            }
            QPushButton:pressed {
                background-color: #cce5ff;
            }
        """
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(10, 10, 10, 10)
        
        # Row 1 of Top Panel
        row1_layout = QHBoxLayout()
        
        # Create combo box with bounded popup
        self.combo = BoundedComboBox()
        self.populate_run_combo()
        self.combo.setMinimumWidth(300)


        self.combo.currentIndexChanged.connect(self.on_run_changed)
        self.combo.setStyleSheet("""
            QComboBox {
                background-color: white; 
                border: 1px solid gray; 
                border-radius: 2px; 
                padding: 2px;
                color: black;
            }
            QComboBox QAbstractItemView {
                color: black;
                background-color: white;
            }
        """)
        
        # Filter
        filter_label = QLabel("Filter:")
        filter_label.setFont(QFont("Arial", 10, QFont.Bold))
        filter_label.setStyleSheet("color: black;")
        self.filter_input = QLineEdit()
        self.filter_input.setStyleSheet("background-color: white; border: 1px solid gray; border-radius: 2px; color: black;")
        self.filter_input.setFixedWidth(150)
        self.filter_input.textChanged.connect(self.filter_tree)
        
        
        # Buttons Group 1
        btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
                color: #222222;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """
        
        self.buttons_row1 = ["run all", "run", "stop", "skip", "unskip", "invalid"]
        self.buttons_row2 = ["term", "csh", "log", "cmd", "trace up", "trace dn"]
        
        row1_layout.addWidget(self.combo)
        row1_layout.addStretch()
        row1_layout.addWidget(filter_label)
        row1_layout.addWidget(self.filter_input)
        row1_layout.addSpacing(20)
        
        # Create buttons and connect to commands
        bt_runall = QPushButton("run all")
        bt_runall.setStyleSheet(btn_style)
        bt_runall.clicked.connect(lambda: self.start('XMeta_run all'))
        row1_layout.addWidget(bt_runall)
        
        bt_run = QPushButton("run")
        bt_run.setStyleSheet(btn_style)
        bt_run.clicked.connect(lambda: self.start('XMeta_run'))
        row1_layout.addWidget(bt_run)
        
        bt_stop = QPushButton("stop")
        bt_stop.setStyleSheet(btn_style)
        bt_stop.clicked.connect(lambda: self.start('XMeta_stop'))
        row1_layout.addWidget(bt_stop)
        
        bt_skip = QPushButton("skip")
        bt_skip.setStyleSheet(btn_style)
        bt_skip.clicked.connect(lambda: self.start('XMeta_skip'))
        row1_layout.addWidget(bt_skip)
        
        bt_unskip = QPushButton("unskip")
        bt_unskip.setStyleSheet(btn_style)
        bt_unskip.clicked.connect(lambda: self.start('XMeta_unskip'))
        row1_layout.addWidget(bt_unskip)
        
        bt_invalid = QPushButton("invalid")
        bt_invalid.setStyleSheet(btn_style)
        bt_invalid.clicked.connect(lambda: self.start('XMeta_invalid'))
        row1_layout.addWidget(bt_invalid)
            
        top_layout.addLayout(row1_layout)
        
        # Row 2 of Top Panel (Button handlers for files and trace)
        row2_layout = QHBoxLayout()
        row2_layout.addStretch()
        
        bt_term = QPushButton("term")
        bt_term.setStyleSheet(btn_style)
        bt_term.clicked.connect(self.Xterm)
        row2_layout.addWidget(bt_term)
        
        bt_csh = QPushButton("csh")
        bt_csh.setStyleSheet(btn_style)
        bt_csh.clicked.connect(self.handle_csh)
        row2_layout.addWidget(bt_csh)
        
        bt_log = QPushButton("log")
        bt_log.setStyleSheet(btn_style)
        bt_log.clicked.connect(self.handle_log)
        row2_layout.addWidget(bt_log)
        
        bt_cmd = QPushButton("cmd")
        bt_cmd.setStyleSheet(btn_style)
        bt_cmd.clicked.connect(self.handle_cmd)
        row2_layout.addWidget(bt_cmd)
        
        bt_trace_up = QPushButton("trace up")
        bt_trace_up.setStyleSheet(btn_style)
        bt_trace_up.clicked.connect(lambda: self.retrace_tab('in'))
        row2_layout.addWidget(bt_trace_up)
        
        bt_trace_dn = QPushButton("trace dn")
        bt_trace_dn.setStyleSheet(btn_style)
        bt_trace_dn.clicked.connect(lambda: self.retrace_tab('out'))
        row2_layout.addWidget(bt_trace_dn)
        
        
        top_layout.addLayout(row2_layout)
        main_layout.addWidget(top_panel)

        # Tab Bar (Mocking the tab look)
        self.tab_bar = QWidget()
        self.tab_bar.setStyleSheet("""
            background-color: #f9f9f9;
            border-bottom: 1px solid #dddddd;
            border-radius: 0 0 8px 8px;
        """)
        tab_layout = QHBoxLayout(self.tab_bar)
        tab_layout.setContentsMargins(5, 5, 5, 0)
        tab_layout.setSpacing(2)
        
        # Custom Tab Widget (Container for label + close button)
        self.tab_widget = QWidget()
        self.tab_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        tab_inner_layout = QHBoxLayout(self.tab_widget)
        tab_inner_layout.setContentsMargins(12, 6, 8, 6)
        tab_inner_layout.setSpacing(8)
        
        self.tab_label = ClickableLabel("") # Initial empty, will be set by update_ui_from_selection
        self.tab_label.doubleClicked.connect(self.toggle_tree_expansion)
        self.tab_label.setToolTip("Double-click to Expand/Collapse All")
        self.tab_label.setStyleSheet("border: none; font-weight: bold; color: #333; font-size: 13px;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close Tab")
        close_btn.clicked.connect(self.close_tree_view)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 9px;
                color: #888;
                font-weight: bold;
                background: transparent;
                font-size: 14px;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #ff4d4d;
                color: white;
            }
        """)
        
        tab_inner_layout.addWidget(self.tab_label)
        tab_inner_layout.addWidget(close_btn)
        
        tab_layout.addWidget(self.tab_widget)
        tab_layout.addStretch()
        main_layout.addWidget(self.tab_bar)

        # Tree View
        self.tree = ColorTreeView()
        
        # Set the custom delegate
        self.delegate = BorderItemDelegate(self.tree)
        self.tree.setItemDelegate(self.delegate)
        
        self.tree.setHeaderHidden(False)
        self.tree.setIndentation(20)
        self.tree.setAlternatingRowColors(False)
        self.tree.setAnimated(True) # Enable smooth expansion/collapse animation
        self.tree.setUniformRowHeights(True) # Optimize for uniform height items
        self.tree.setVerticalScrollMode(QTreeView.ScrollPerItem) # Smooth scrolling and animation
        self.tree.setSelectionMode(QTreeView.ExtendedSelection) # Enable multi-selection
        self.tree.setSelectionBehavior(QTreeView.SelectRows) # Ensure full row selection/hover
        self.tree.setStyleSheet("""
            QTreeView {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0,0,0,0.1);
                font-family: ".AppleSystemUIFont", "Helvetica Neue", "Arial", sans-serif;
                font-size: 14px;
                border-radius: 10px;
                padding: 5px;
            }
            QTreeView::item {
                height: 15px;
                padding: 6px 4px; /* Consistent padding */
                border: none;     /* No border in QSS to avoid jitter/coverage */
            }
            QTreeView:focus {
                outline: none;
            }
            QHeaderView::section {
                background: rgba(250,250,250,0.95);
                padding: 8px;
                border: 1px solid #e0e0e0;
                font-weight: 600;
                color: #444444;
            }
            QTreeView::item:hover {
                /* Background handled by delegate */
                background: transparent;
            }
            QTreeView::item:selected {
                /* Background handled by delegate */
                background: transparent;
                color: #000000 !important;
                outline: none;
            }
            /* Branch styling is no longer needed as delegate handles full row */
            QTreeView::branch {
                background: transparent;
                border: none;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                background: transparent;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                background: transparent;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                background: transparent;
            }
            QTreeView::branch:has-children:!has-siblings:closed {
                background: transparent;
                image: none;
            }
            QTreeView::branch:has-children:!has-siblings:open {
                background: transparent;
                image: none;
            }
            QTreeView::branch:has-children:has-siblings:closed {
                image: none;
            }
            QTreeView::branch:has-children:has-siblings:open {
                image: none;
            }
            QTreeView::branch:closed:has-children {
                border-image: none;
            }
            QTreeView::branch:open:has-children {
                border-image: none;
            }
            /* Ensure branch selection matches item selection */
            QTreeView::branch:selected {
                background: #C0C0BE !important;
            }
            QTreeView::branch:has-siblings:!adjoins-item:selected {
                background: #C0C0BE !important;
            }
            QTreeView::branch:has-siblings:adjoins-item:selected {
                background: #C0C0BE !important;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item:selected {
                background: #C0C0BE !important;
            }
            QTreeView::branch:has-children:!has-siblings:closed:selected,
            QTreeView::branch:has-children:!has-siblings:open:selected {
                background: #C0C0BE !important;
            }
            QTreeView::branch:hover {
                background: rgba(230,240,255,0.6) !important;
            }
        """)
        
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "start time", "end time"])
        self.tree.setModel(self.model)
        
        # Simple column width setup
        self.set_column_widths()

        # Initialize TreeViewEventFilter
        self.tree_view_event_filter = TreeViewEventFilter(self.tree, self)
        self.tree.viewport().installEventFilter(self.tree_view_event_filter)
        
        main_layout.addWidget(self.tree)
        
        # Set right-click context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Initial UI Update
        self.on_run_changed()
        
        # Start refresh timer (update status every 1 second)
        self.timer = QTimer()
        self.timer.timeout.connect(self.change_run)
        self.timer.start(1000)
        
        # Expand all
        self.tree.expandAll()

    def close_tree_view(self):
        """Close the tree view (or clear trace filter)"""
        # If we are in All Status view, restore normal view
        if hasattr(self, 'is_all_status_view') and self.is_all_status_view:
            self.restore_normal_view()
            return
        
        # If we are in trace mode (label starts with "Trace"), just clear the filter
        if hasattr(self, 'tab_label') and self.tab_label.text().startswith("Trace"):
            # Clear filter by showing all rows
            self.tree.setUpdatesEnabled(False)
            for row in range(self.model.rowCount()):
                self.tree.setRowHidden(row, QModelIndex(), False)
                item = self.model.item(row)
                if item:
                    self.show_all_children(item)
            self.tree.setUpdatesEnabled(True)
            
            # Reset label style and text
            current_run = self.combo.currentText()
            self.tab_label.setText(current_run)
            self.tab_label.setStyleSheet("border: none; font-weight: bold; color: #333; font-size: 13px;")
            return

        # Otherwise hide the tree view (original behavior)
        if hasattr(self, 'tree'):
            self.tree.hide()
        if hasattr(self, 'tab_bar'):
            self.tab_bar.hide()

    def get_selected_targets(self):
        """Get currently selected targets from tree view."""
        selected_indexes = self.tree.selectionModel().selectedIndexes()
        if not selected_indexes:
            return []
        
        targets = []
        seen_rows = set()
        
        for index in selected_indexes:
            # Only process target column (column 1)
            if index.column() != 1:
                continue
            
            # Avoid processing same row multiple times
            row_key = (index.row(), index.parent().row() if index.parent().isValid() else -1)
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            
            # Get target value
            if index.parent().isValid():
                # Child item
                target_index = self.model.index(index.row(), 1, index.parent())
            else:
                # Parent item
                target_index = self.model.index(index.row(), 1)
            
            target = self.model.data(target_index)
            if target:
                targets.append(target)
        
        return targets

    def start(self, action):
        """Execute flow action and refresh view."""
        import subprocess
        
        # Get selected targets
        selected_targets = self.get_selected_targets()
        if not selected_targets:
            print(f"No targets selected for action: {action}")
            return
        
        # Get current run name
        current_run = self.combo.currentText()
        run_dir = os.path.join(self.run_base_dir, current_run)
        
        # Build command
        if action == 'XMeta_run all':
            cmd = f"cd {run_dir} && {action}"
            print(f"{current_run}, {action}.")
        else:
            cmd = f"cd {run_dir} && {action} " + " ".join(selected_targets)
            print(f"{current_run}, {action} {' '.join(selected_targets)}.")
        
        # Execute command
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if stdout:
                print(stdout.decode())
            if stderr:
                print(stderr.decode())
        except Exception as e:
            print(f"Error executing command: {e}")
        
        # Refresh UI - reload tree to show updated status
        if action in ['XMeta_unskip', 'XMeta_skip']:
            # For skip/unskip, need to reload tree structure (now optimized in populate_data)
            print(f"DEBUG: Calling populate_data for action {action}")
            self.populate_data()
        else:
            pass
            
        # Clear selection after operation
        self.tree.clearSelection()

    def filter_tree(self, text):
        """Filter tree items based on text input.
        If text is empty, restore full hierarchy.
        If text is present, show FLAT list of matching items (no parents).
        """
        print(f"DEBUG: filter_tree called with text='{text}'")
        
        if not text:
            # Restore full hierarchy
            self.model.clear() # Force clear to trigger full rebuild in populate_data
            self.populate_data()
            return

        # Search in cached data
        if not hasattr(self, 'cached_targets_by_level') or not self.cached_targets_by_level:
             # Try to load if not cached (should be cached by populate_data)
             current_run = self.combo.currentText()
             if current_run and current_run != "No runs found":
                 self.cached_targets_by_level = self.parse_dependency_file(current_run)
        
        if not self.cached_targets_by_level:
            return

        self.tree.setUpdatesEnabled(False)
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "start time", "end time"])
        self.set_column_widths()
        
        # Helper to add a single row (returns the created items list)
        def create_row_items(level, target_name):
            # Get real status
            current_run = self.combo.currentText()
            status = self.get_target_status(current_run, target_name)
            
            # Create Row
            row_items = []
            
            # Level
            l_item = QStandardItem(str(level))
            l_item.setEditable(False)
            l_item.setForeground(QBrush(Qt.black))
            row_items.append(l_item)
            
            # Target
            t_item = QStandardItem(target_name)
            t_item.setEditable(False)
            t_item.setForeground(QBrush(Qt.black))
            row_items.append(t_item)
            
            # Status
            s_item = QStandardItem(status)
            s_item.setEditable(False)
            s_item.setForeground(QBrush(Qt.black))
            row_items.append(s_item)
            
            # Time
            tgt_track_file = os.path.join(self.combo_sel, 'logs/targettracker', target_name)
            start_time, end_time = self.get_start_end_time(tgt_track_file)
            
            st_item = QStandardItem(start_time)
            st_item.setEditable(False)
            st_item.setForeground(QBrush(Qt.black))
            row_items.append(st_item)
            
            et_item = QStandardItem(end_time)
            et_item.setEditable(False)
            et_item.setForeground(QBrush(Qt.black))
            row_items.append(et_item)
            
            # Apply background color
            STATUS_COLORS = {
                "finish": "#98FB98",    # PaleGreen
                "skip": "#FFDAB9",      # PeachPuff
                "running": "#FFFF00",   # Yellow
                "failed": "#FF9999",    # Light Red
                "scheduled": "#87CEEB", # SkyBlue
                "waiting": "#87CEEB",   # SkyBlue
                "": "#87CEEB"           # Default/No status
            }
            color_code = STATUS_COLORS.get(status.lower(), "#87CEEB")
            color = QColor(color_code)
            
            for it in row_items:
                it.setBackground(QBrush(color))
                
            return row_items

        # Iterate and find matches
        text_lower = text.lower()
        
        # Sort levels to maintain order
        sorted_levels = sorted(self.cached_targets_by_level.keys())
        
        for level in sorted_levels:
            targets = self.cached_targets_by_level[level]
            if not targets:
                continue
            
            # Find all matching targets in this level
            matching_targets = []
            for target in targets:
                if text_lower in target.lower():
                    matching_targets.append(target)
            
            if not matching_targets:
                continue
                
            # Create Parent (First matching target)
            parent_target = matching_targets[0]
            parent_row_items = create_row_items(level, parent_target)
            self.model.appendRow(parent_row_items)
            
            # Create Children (Subsequent matching targets)
            if len(matching_targets) > 1:
                parent_item = parent_row_items[0] # The level item acts as parent for the row
                for child_target in matching_targets[1:]:
                    # For child rows, we usually leave Level empty or same? 
                    # In main view, children have empty level. Let's follow that.
                    child_row_items = create_row_items("", child_target)
                    parent_item.appendRow(child_row_items)
                
                # Expand the parent to show children
                self.tree.expand(parent_item.index())
                    
        self.tree.setUpdatesEnabled(True)

    def toggle_tree_expansion(self):
        """Toggle between Expand All and Collapse All"""
        if self.is_tree_expanded:
            self.tree.collapseAll()
        else:
            self.tree.expandAll()
        self.is_tree_expanded = not self.is_tree_expanded

    def show_all_children(self, item):
        """Helper to recursively show all children"""
        if item.hasChildren():
            for i in range(item.rowCount()):
                child = item.child(i)
                parent_index = item.index()
                self.tree.setRowHidden(i, parent_index, False)
                self.show_all_children(child)

    def scan_runs(self):
        """Scan the run base directory for valid run directories.
        A valid run directory contains a .target_dependency.csh file.
        """
        runs = []
        if not os.path.exists(self.run_base_dir):
            return runs
        
        print(f"Scanning for runs in: {os.path.abspath(self.run_base_dir)}")
        try:
            for item in os.listdir(self.run_base_dir):
                item_path = os.path.join(self.run_base_dir, item)
                if os.path.isdir(item_path):
                    # Check if .target_dependency.csh exists
                    dependency_file = os.path.join(item_path, ".target_dependency.csh")
                    if os.path.exists(dependency_file):
                        runs.append(item)
                        print(f"Found run: {item}")
        except Exception as e:
            print(f"Error scanning runs: {e}")
        
        print(f"Total runs found: {len(runs)}")
        return sorted(runs)

    def show_all_status(self):
        """Show status summary of all run directories in the TreeView.
        Displays: Run Directory, Latest Target, Status, Time Stamp
        """
        print("DEBUG: show_all_status called")
        
        # Set flag to indicate we are in "All Status" view
        self.is_all_status_view = True
        
        # Update tab label to reflect current view
        if hasattr(self, 'tab_label'):
            self.tab_label.setText("All Status Overview")
            self.tab_label.setStyleSheet("border: none; font-weight: bold; color: #1976d2; font-size: 13px;")
        
        # Clear and reconfigure model for All Status view
        self.tree.setUpdatesEnabled(False)
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Run Directory", "Latest Target", "Status", "Time Stamp"])
        
        # Set column widths for this view
        self.tree.setColumnWidth(0, 350)  # Run Directory
        self.tree.setColumnWidth(1, 400)  # Latest Target
        self.tree.setColumnWidth(2, 100)  # Status
        self.tree.setColumnWidth(3, 180)  # Time Stamp
        
        # Status to Color Mapping
        STATUS_COLORS = {
            "finish": "#98FB98",    # PaleGreen
            "skip": "#FFDAB9",      # PeachPuff
            "running": "#FFFF00",   # Yellow
            "failed": "#FF9999",    # Light Red
            "scheduled": "#87CEEB", # SkyBlue
            "waiting": "#87CEEB",   # SkyBlue
            "": "#FFFFFF"           # White/No status
        }
        
        # Scan all runs
        runs = self.scan_runs()
        
        for run_name in runs:
            run_dir = os.path.join(self.run_base_dir, run_name)
            status_dir = os.path.join(run_dir, "status")
            
            latest_target = ""
            latest_status = ""
            latest_timestamp = ""
            latest_mtime = 0
            
            # Find the latest modified status file
            if os.path.exists(status_dir):
                try:
                    for status_file in os.listdir(status_dir):
                        file_path = os.path.join(status_dir, status_file)
                        if os.path.isfile(file_path):
                            mtime = os.path.getmtime(file_path)
                            if mtime > latest_mtime:
                                latest_mtime = mtime
                                
                                # Parse target name and status from filename
                                # Format: target_name.status (e.g., UpdateTunable.finish)
                                parts = status_file.rsplit('.', 1)
                                if len(parts) == 2:
                                    latest_target = parts[0]
                                    latest_status = parts[1]
                                else:
                                    latest_target = status_file
                                    latest_status = ""
                                
                                # Format timestamp
                                latest_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                except Exception as e:
                    print(f"Error scanning status for {run_name}: {e}")
            
            # Create row items
            row_items = []
            
            # Run Directory
            run_item = QStandardItem(run_name)
            run_item.setEditable(False)
            run_item.setForeground(QBrush(Qt.black))
            row_items.append(run_item)
            
            # Latest Target
            target_item = QStandardItem(latest_target)
            target_item.setEditable(False)
            target_item.setForeground(QBrush(Qt.black))
            row_items.append(target_item)
            
            # Status
            status_item = QStandardItem(latest_status)
            status_item.setEditable(False)
            status_item.setForeground(QBrush(Qt.black))
            row_items.append(status_item)
            
            # Time Stamp
            time_item = QStandardItem(latest_timestamp)
            time_item.setEditable(False)
            time_item.setForeground(QBrush(Qt.black))
            row_items.append(time_item)
            
            # Apply background color based on status
            color_code = STATUS_COLORS.get(latest_status.lower(), "#FFFFFF")
            color = QColor(color_code)
            for item in row_items:
                item.setBackground(QBrush(color))
            
            # Add row to model
            self.model.appendRow(row_items)
        
        self.tree.setUpdatesEnabled(True)
        print(f"DEBUG: show_all_status completed, showing {len(runs)} runs")

    def restore_normal_view(self):
        """Restore the normal single-run TreeView from All Status view."""
        if self.is_all_status_view:
            self.is_all_status_view = False
            # Trigger a refresh of the normal view
            self.on_run_changed()


    def populate_run_combo(self):
        """Populate the combo box with available run directories."""
        runs = self.scan_runs()
        if runs:
            self.combo.addItems(runs)
            
            # Try to detect current run from working directory
            # If we are inside a run directory, the basename of cwd should match a run name
            current_cwd_name = os.path.basename(os.getcwd())
            
            print(f"Current working directory basename: {current_cwd_name}")
            print(f"Available runs: {runs}")
            
            if current_cwd_name in runs:
                index = self.combo.findText(current_cwd_name)
                if index >= 0:
                    self.combo.setCurrentIndex(index)
                    print(f"Selected run: {current_cwd_name}")
            else:
                # Default to the first item if current cwd is not a valid run
                self.combo.setCurrentIndex(0)
                print(f"Selected first run: {runs[0]}")
        else:
            # Fallback if no runs found
            self.combo.addItem("No runs found")
            self.combo.setEnabled(False)

    def parse_dependency_file(self, run_name):
        """Parse .target_dependency.csh file to extract target-level mappings.
        
        Returns:
            dict: Mapping of level number to list of target names
        """
        dependency_file = os.path.join(self.run_base_dir, run_name, ".target_dependency.csh")
        targets_by_level = {}
        
        if not os.path.exists(dependency_file):
            print(f"Warning: Dependency file not found for {run_name}")
            return targets_by_level
        
        try:
            with open(dependency_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Parse lines like: set LEVEL_1 = "UpdateTunable ShGetData"
                    if line.startswith('set LEVEL_'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            # Extract level number
                            level_part = parts[0].strip()
                            level_num = int(level_part.split('_')[1])
                            
                            # Extract target names
                            targets_str = parts[1].strip().strip('"')
                            targets = targets_str.split()
                            
                            targets_by_level[level_num] = targets
        except Exception as e:
            print(f"Error parsing dependency file for {run_name}: {e}")
        
        return targets_by_level

    def on_run_changed(self):
        """When combo box selection changes, rebuild tree with new run data."""
        current_run = self.combo.currentText()
        if current_run == "No runs found":
            return
        
        # Reset All Status view flag when switching runs
        self.is_all_status_view = False
        
        # Set combo_sel to current run directory
        self.combo_sel = os.path.join(self.run_base_dir, current_run)
        print(f"Run changed to: {self.combo_sel}")
        
        # Rebuild tree from .target_dependency.csh
        # self.get_tree(self.combo_sel) # Removed to prevent incorrect UI generation
        
        if current_run:
            # Update tab label to reflect selected run
            if hasattr(self, 'tab_label'):
                self.tab_label.setText(current_run)
            
            # Force clear to trigger full rebuild in populate_data with correct UI
            self.model.clear()
            # Repopulate tree data with targets from the selected run
            self.populate_data()


        
    def get_target_status(self, run_name, target_name):
        """Get status of a target by checking status files in run_dir/status/"""
        run_dir = os.path.join(self.run_base_dir, run_name)
        status_dir = os.path.join(run_dir, "status")
        
        if not os.path.exists(status_dir):
            return "" # Default if no status dir
            
        # Check for status files: target_name.status
        # Priority: finish > failed > running > skip > scheduled
        # Or simply check what exists.
        # Based on user input, we might have multiple files (e.g. .finish and .skip).
        # We should probably check modification time, but for now let's check existence with priority.
        
        possible_statuses = ["finish", "failed", "running", "skip"]
        
        # Check if any status file exists
        found_statuses = []
        for status in possible_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            if os.path.exists(status_file):
                found_statuses.append(status)
        
        if not found_statuses:
            return ""
            
        # If multiple statuses found, we need a strategy.
        # For now, let's assume 'finish' overrides others, then 'failed', etc.
        # Or better: check modification time to see which is latest.
        latest_status = None
        latest_time = 0
        
        for status in found_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            mtime = os.path.getmtime(status_file)
            if mtime > latest_time:
                latest_time = mtime
                latest_status = status
                
        return latest_status if latest_status else ""

    def populate_data(self):
        # Status to Color Mapping
        STATUS_COLORS = {
            "finish": "#98FB98",    # PaleGreen
            "skip": "#FFDAB9",      # PeachPuff
            "running": "#FFFF00",   # Yellow
            "failed": "#FF9999",    # Light Red
            "scheduled": "#87CEEB", # SkyBlue
            "waiting": "#87CEEB",   # SkyBlue
            "": "#87CEEB"           # Default/No status
        }

        def get_color(status):
            return STATUS_COLORS.get(status.lower(), "#87CEEB") # Default to SkyBlue if unknown

        # Optimization: If model is already populated, just refresh status in-place
        if self.model.rowCount() > 0:
            current_run = self.combo.currentText()
            if not current_run: return

            self.tree.setUpdatesEnabled(False)
            
            def update_row(row_index, parent_index=QModelIndex()):
                # Get Target (Col 1)
                target_idx = self.model.index(row_index, 1, parent_index)
                target_name = self.model.data(target_idx)
                
                if not target_name:
                    return

                # Get Status
                status = self.get_target_status(current_run, target_name)
                color = QColor(get_color(status))
                
                # Update Status Item (Col 2)
                status_idx = self.model.index(row_index, 2, parent_index)
                self.model.setData(status_idx, status)
                
                # Update Background for all columns in this row
                for col in range(self.model.columnCount()):
                    idx = self.model.index(row_index, col, parent_index)
                    item = self.model.itemFromIndex(idx)
                    if item:
                        item.setBackground(QBrush(color))
            
            # Iterate Top Level
            for r in range(self.model.rowCount()):
                update_row(r)
                # Iterate Children
                parent_idx = self.model.index(r, 0)
                item = self.model.itemFromIndex(parent_idx)
                if item and item.hasChildren():
                    for child_r in range(item.rowCount()):
                        update_row(child_r, parent_idx)
            
            self.tree.setUpdatesEnabled(True)
            return

        # Save current scroll position
        current_scroll = self.tree.verticalScrollBar().value()
        
        self.tree.setUpdatesEnabled(False)
        # Clear existing data
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "start time", "end time"])
        self.set_column_widths()
        
        # Get current run name
        current_run = self.combo.currentText()
        if not current_run:
            return
        
        # Parse dependency file to get targets and levels
        targets_by_level = self.parse_dependency_file(current_run)
        self.cached_targets_by_level = targets_by_level # Cache for search
        
        if not targets_by_level:
            print(f"No targets found for {current_run}")
            return

        # Populate tree with real status
        for level, targets in sorted(targets_by_level.items()):
            if not targets:
                continue
                
            # First target is the Parent (Main Task)
            parent_target = targets[0]
            
            # Get real status
            p_status = self.get_target_status(current_run, parent_target)
            
            # Create Parent Row
            parent_row = []
            # Level
            l_item = QStandardItem(str(level))
            l_item.setEditable(False)
            l_item.setForeground(QBrush(Qt.black))
            parent_row.append(l_item)
            
            # Target
            t_item = QStandardItem(parent_target)
            t_item.setEditable(False)
            t_item.setForeground(QBrush(Qt.black))
            parent_row.append(t_item)
            
            # Status
            s_item = QStandardItem(p_status)
            s_item.setEditable(False)
            s_item.setForeground(QBrush(Qt.black))
            parent_row.append(s_item)
            
            # Time (mock for now, or could read from file mtime)
            start_time = ""
            end_time = ""
            
            st_item = QStandardItem(start_time)
            st_item.setEditable(False)
            st_item.setForeground(QBrush(Qt.black))
            parent_row.append(st_item)
            
            et_item = QStandardItem(end_time)
            et_item.setEditable(False)
            et_item.setForeground(QBrush(Qt.black))
            parent_row.append(et_item)
            
            # Apply background color to parent
            p_color = QColor(get_color(p_status))
            for it in parent_row:
                it.setBackground(QBrush(p_color))
            
            # Add Parent to Model
            self.model.appendRow(parent_row)
            
            # Handle Children (Subsequent targets in the list)
            children_targets = targets[1:]
            for child_target in children_targets:
                child_row = []
                
                # Level (Empty for child)
                child_row.append(QStandardItem(""))
                
                # Target
                c_t_item = QStandardItem(child_target)
                c_t_item.setEditable(False)
                c_t_item.setForeground(QBrush(Qt.black))
                child_row.append(c_t_item)
                
                # Get real status for child
                c_status = self.get_target_status(current_run, child_target)
                
                c_s_item = QStandardItem(c_status)
                c_s_item.setEditable(False)
                c_s_item.setForeground(QBrush(Qt.black))
                child_row.append(c_s_item)
                
                # Time
                child_row.append(QStandardItem(""))
                child_row.append(QStandardItem(""))
                
                # Apply background color to child
                c_color = QColor(get_color(c_status))
                for it in child_row:
                    it.setBackground(QBrush(c_color))
                
                # Add child to parent
                parent_row[0].appendRow(child_row)
        
        
        # Check if filter exists (Search Filter)
        has_search_filter = hasattr(self, 'filter_input') and self.filter_input.text()
        
        # Check if Trace Filter is active
        is_trace_mode = hasattr(self, 'tab_label') and self.tab_label.text().startswith("Trace")
        
        if not has_search_filter and not is_trace_mode:
            # Expand all only if no filter
            self.tree.expandAll()
            # Restore scroll position
            self.tree.verticalScrollBar().setValue(current_scroll)
        else:
            # Re-apply filter synchronously
            def restore_filter_and_scroll():
                if is_trace_mode:
                    # Re-apply trace filter
                    # Extract target name and direction from label: "Trace Up: <Target>"
                    label_text = self.tab_label.text()
                    parts = label_text.split(": ")
                    if len(parts) == 2:
                        direction_str = parts[0] # "Trace Up" or "Trace Down"
                        target_name = parts[1]
                        inout = 'in' if "Up" in direction_str else 'out'
                        
                        # Re-calculate dependencies
                        related_targets = self.get_retrace_target(target_name, inout)
                        if target_name not in related_targets:
                            if inout == 'in':
                                related_targets.append(target_name)
                            else:
                                related_targets.insert(0, target_name)
                        
                        # Apply filter
                        self.filter_tree_by_targets(set(related_targets))
                
                elif has_search_filter:
                    # Re-apply search filter
                    self.filter_tree(self.filter_input.text())
                
                # Restore scroll position
                self.tree.verticalScrollBar().setValue(current_scroll)
            
            # Execute immediately to prevent flicker
            restore_filter_and_scroll()
            
        self.tree.setUpdatesEnabled(True)

    def get_target_status(self, run_name, target_name):
        """Get status of a target by checking status files in run_dir/status/"""
        run_dir = os.path.join(self.run_base_dir, run_name)
        status_dir = os.path.join(run_dir, "status")
        
        if not os.path.exists(status_dir):
            return "" # Default if no status dir
            
        # Check for status files: target_name.status
        # Priority: finish > failed > running > skip > scheduled
        # Or simply check what exists.
        # Based on user input, we might have multiple files (e.g. .finish and .skip).
        # We should probably check modification time, but for now let's check existence with priority.
        
        possible_statuses = ["finish", "failed", "running", "skip"]
        
        # Check if any status file exists
        found_statuses = []
        for status in possible_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            if os.path.exists(status_file):
                found_statuses.append(status)
        
        if not found_statuses:
            return ""
            
        # If multiple statuses found, we need a strategy.
        # For now, let's assume 'finish' overrides others, then 'failed', etc.
        # Or better: check modification time to see which is latest.
        latest_status = None
        latest_time = 0
        
        for status in found_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            mtime = os.path.getmtime(status_file)
            if mtime > latest_time:
                latest_time = mtime
                latest_status = status
                
        return latest_status if latest_status else ""

    # ========== Core Monitor.py Methods ==========
    
    def get_tree(self, run_dir):
        """Build tree from .target_dependency.csh file (from monitor.py/tree_handlers.py)"""
        if not os.path.exists(os.path.join(run_dir, '.target_dependency.csh')):
            print(f"Warning: .target_dependency.csh not found in {run_dir}")
            return
        
        # Clear existing model
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "start time", "end time"])
        
        # Get targets
        self.get_target()
        
        l = []
        o = []
        
        # Get current run name from path
        current_run = os.path.basename(run_dir)
        
        # Read and parse .target_dependency.csh
        with open(os.path.join(run_dir, '.target_dependency.csh'), 'r') as f:
            a_file = f.read()
            for target in self.tar_name:
                level_name = f'TARGET_LEVEL_{target}'
                match_lv = re.search(r'set\s*(%s)\s*\=(\s.*)' % level_name, a_file)
                if not match_lv:
                    continue
                target_name = match_lv.group(2).strip()
                if re.match(r"^(['\"]).*\"$", target_name):
                    target_level = re.sub(r"^['\"]|['\"]$", '', target_name).split()

                tgt_track_file = os.path.join(run_dir, 'logs/targettracker', target)

                start_time, end_time = self.get_start_end_time(tgt_track_file)
                target_status = self.get_target_status(current_run, target)

                str_lv = ''.join(target_level)
                o.append(str_lv)
                d = [target_level, target, target_status, start_time, end_time]
                l.append(d)
        
        # Get all unique levels and sort
        all_lv = list(set(o))
        all_lv.sort(key=o.index)
        
        # Group data by level
        level_data = {}
        for data in l:
            lvl, tgt, st, ct, et = data
            str_data = ''.join(lvl)
            if str_data not in level_data:
                level_data[str_data] = []
            level_data[str_data].append((tgt, st, ct, et))
        
        # Create parent-child structure
        for level in all_lv:
            if level not in level_data:
                continue
            
            items = level_data[level]
            if not items:
                continue
            
            # Create parent node (first item)
            root_item = QStandardItem()
            root_item.setText(level)
            root_item.setEditable(False)
            
            # Create other columns for parent
            root_items = [root_item]
            first_item = items[0]
            text_color = QColor("#333333")
            for value in [first_item[0], first_item[1], first_item[2], first_item[3]]:
                item = QStandardItem()
                item.setText(value)
                item.setEditable(False)
                item.setForeground(QBrush(text_color))
                root_items.append(item)
            
            # Set parent node color (all columns)
            if first_item[1] in self.colors:
                color = QColor(self.colors[first_item[1]])
                for item in root_items:
                    item.setBackground(QBrush(color))
            
            # Add parent to model
            self.model.appendRow(root_items)
            
            # Add children if more than one item
            if len(items) > 1:
                for tgt, st, ct, et in items[1:]:
                    child_items = []
                    text_color = QColor("#333333")
                    # level column
                    level_item = QStandardItem()
                    level_item.setText(level)
                    level_item.setEditable(False)
                    level_item.setForeground(QBrush(text_color))
                    child_items.append(level_item)
                    
                    # Other columns
                    for value in [tgt, st, ct, et]:
                        item = QStandardItem()
                        item.setText(value)
                        item.setEditable(False)
                        item.setForeground(QBrush(text_color))
                        child_items.append(item)
                    
                    # Set child color (all columns)
                    if st in self.colors:
                        color = QColor(self.colors[st])
                        for item in child_items:
                            item.setBackground(QBrush(color))
                    
                    # Add child to parent
                    root_item.appendRow(child_items)
        
        
        # Check if filter exists
        has_filter = hasattr(self, 'filter_input') and self.filter_input.text()
        
        if not has_filter:
            # Expand all only if no filter
            self.tree.expandAll()
        else:
            # Re-apply filter if exists
            print(f"Re-applying filter: {self.filter_input.text()}")
            # Use a delay to ensure model is fully loaded and view is ready
            QTimer.singleShot(100, lambda: self.filter_tree(self.filter_input.text()))

    def get_target(self):
        """Parse ACTIVE_TARGETS from .target_dependency.csh"""
        if not self.combo_sel:
            return
        deps_file = os.path.join(self.combo_sel, '.target_dependency.csh')
        if not os.path.exists(deps_file):
            self.tar_name = []
            return
            
        with open(deps_file, 'r') as f:
            a_file = f.read()
            m = re.search(r'set\s*ACTIVE_TARGETS\s*\=(\s.*)', a_file)
            if m:
                target_name = m.group(1).strip()
                if re.match(r"^(['\"]).*\"$", target_name):
                    self.tar_name = re.sub(r"^['\"]|['\"]$", "", target_name).split()
                    return
        self.tar_name = []

    def change_run(self):
        """Refresh status timer callback - updates status/time for all visible targets"""
        if not hasattr(self, 'model') or not self.model or not self.combo_sel:
            return
        
        # Skip updates when in All Status view
        if self.is_all_status_view:
            return
            
        for i in range(self.model.rowCount()):
            level_item = self.model.item(i, 0)
            if not level_item:
                continue
                
            target_item = self.model.item(i, 1)
            status_item = self.model.item(i, 2)
            start_time_item = self.model.item(i, 3)
            end_time_item = self.model.item(i, 4)
            
            if not all([target_item, status_item, start_time_item, end_time_item]):
                continue
                
            target = target_item.text()
            tgt_track_file = os.path.join(self.combo_sel, 'logs/targettracker', target)
            
            # Get current run name
            current_run = os.path.basename(self.combo_sel)
            
            # Get status and time
            status = self.get_target_status(current_run, target)
            start_time, end_time = self.get_start_end_time(tgt_track_file)
            
            # Update status and time
            if status and status != status_item.text():
                status_item.setText(status)
                if status in self.colors:
                    color = QColor(self.colors[status])
                    status_item.setBackground(QBrush(color))
                
            if start_time != start_time_item.text():
                start_time_item.setText(start_time)
            if end_time != end_time_item.text():
                end_time_item.setText(end_time)
    
    def get_start_end_time(self, tgt_track_file):
        """Get start and end time from target tracker file"""
        start_time = ""
        end_time = ""
        if os.path.exists(tgt_track_file + '.start'):
            st_mtime = os.path.getmtime(tgt_track_file + '.start')+28800
            start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
        if os.path.exists(tgt_track_file + '.finished'):
            ft_mtime = os.path.getmtime(tgt_track_file + '.finished')+28800
            end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ft_mtime))
        return start_time, end_time

    # ========== File Viewers ==========
    
    def handle_csh(self):
        """Open shell file for selected target"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        shell_file = os.path.join(self.combo_sel, 'make_targets', f"{target}.csh")
        
        if os.path.exists(shell_file):
            try:
                subprocess.run(['gvim', shell_file], check=False)
            except Exception as e:
                print(f"Error opening csh: {e}")

    def handle_log(self):
        """Open log file for selected target"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        log_file = os.path.join(self.combo_sel, 'logs', f"{target}.log")
        log_file_gz = f"{log_file}.gz"
        
        try:
            if os.path.exists(log_file):
                subprocess.Popen(['gvim', log_file])
            elif os.path.exists(log_file_gz):
                subprocess.Popen(['gvim', log_file_gz])
        except Exception as e:
            print(f"Error opening log: {e}")

    def handle_cmd(self):
        """Open command file for selected target"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        cmd_file = os.path.join(self.combo_sel, 'cmds', f"{target}.cmd")
        
        if os.path.exists(cmd_file):
            try:
                subprocess.run(['gvim', cmd_file], check=False)
            except Exception as e:
                print(f"Error opening cmd: {e}")

    def Xterm(self):
        """Open terminal in current run directory"""
        if not self.combo_sel:
            return
        os.chdir(self.combo_sel)
        os.system('XMeta_term')

    # ========== Right-click Menu ==========
    
    def show_context_menu(self, position):
        """Show context menu on right-click"""
        index = self.tree.indexAt(position)
        if not index.isValid():
            return

        # Ensure the item is selected
        selection_model = self.tree.selectionModel()
        if not selection_model.isSelected(index):
            selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

        menu = QMenu()
        
        terminal_action = menu.addAction("Terminal")
        csh_action = menu.addAction("csh")
        log_action = menu.addAction("Log")
        cmd_action = menu.addAction("cmd")
        menu.addSeparator()
        trace_up_action = menu.addAction("Trace Up")
        trace_down_action = menu.addAction("Trace Down")
        
        action = menu.exec_(self.tree.viewport().mapToGlobal(position))
        
        if action == terminal_action:
            self.Xterm()
        elif action == csh_action:
            self.handle_csh()
        elif action == log_action:
            self.handle_log()
        elif action == cmd_action:
            self.handle_cmd()
        elif action == trace_up_action:
            self.retrace_tab('in')
        elif action == trace_down_action:
            self.retrace_tab('out')

    # ========== Trace Functionality ==========
    
    def get_retrace_target(self, target, inout):
        """Parse .target_dependency.csh to find related targets (upstream/downstream)"""
        retrace_targets = []
        if not self.combo_sel:
            return retrace_targets
            
        dep_file = os.path.join(self.combo_sel, '.target_dependency.csh')
        if not os.path.exists(dep_file):
            return retrace_targets

        try:
            with open(dep_file, 'r') as f:
                content = f.read()
                
                # Determine which variable to look for
                # in (Trace Up) -> ALL_RELATED_<target>
                # out (Trace Down) -> DEPENDENCY_OUT_<target>
                if inout == 'in':
                    search_key = f'ALL_RELATED_{target}'
                else:
                    search_key = f'DEPENDENCY_OUT_{target}'
                
                # Search for: set <search_key> = "target1 target2 ..."
                match = re.search(r'set\s*(%s)\s*\=(\s.*)' % search_key, content)
                if match:
                    targets_str = match.group(2).strip()
                    # Remove quotes if present
                    if re.match(r"^(['\"]).*\"$", targets_str):
                        targets_str = re.sub(r"^['\"]|['\"]$", '', targets_str)
                    
                    retrace_targets = targets_str.split()
        except Exception as e:
            print(f"Error parsing dependencies: {e}")
            
        return retrace_targets

    def filter_tree_by_targets(self, targets_to_show):
        """Filter tree to show only specific targets"""
        print(f"DEBUG: Filtering tree for {len(targets_to_show)} targets")
        
        # Helper to check visibility
        def check_visibility(item):
            # Check if this item is a target row (has parent) or a level row (no parent)
            if item.parent():
                # It's a target row (or child of one, but our structure is flat-ish)
                # In our model: Level -> Target (row 0) -> Child Target (row 0 child)
                # Actually our model is:
                # Root -> Level Item (col 0), Target Item (col 1) ...
                #      -> Child Row: Level (col 0), Target (col 1) ...
                
                # We need to check the target name in column 1
                target_col_idx = self.model.index(item.row(), 1, item.parent().index())
                target_name = self.model.data(target_col_idx)
                
                should_show = target_name in targets_to_show
                self.tree.setRowHidden(item.row(), item.parent().index(), not should_show)
                return should_show
            else:
                # It's a top-level row (Parent Target)
                target_col_idx = self.model.index(item.row(), 1)
                target_name = self.model.data(target_col_idx)
                
                # Check if this parent is in the list
                parent_match = target_name in targets_to_show
                
                # Check children
                child_match = False
                if item.hasChildren():
                    for i in range(item.rowCount()):
                        child = item.child(i)
                        # We need to check children recursively or just iterate
                        # Our structure is only 1 level deep for children
                        
                        # Get child target name
                        c_target_idx = self.model.index(i, 1, item.index())
                        c_target_name = self.model.data(c_target_idx)
                        
                        c_match = c_target_name in targets_to_show
                        self.tree.setRowHidden(i, item.index(), not c_match)
                        if c_match:
                            child_match = True
                
                should_show = parent_match or child_match
                self.tree.setRowHidden(item.row(), QModelIndex(), not should_show)
                
                # Expand if showing
                if should_show:
                    self.tree.expand(item.index())
                    
                return should_show

        self.tree.setUpdatesEnabled(False)
        # Iterate through top-level items
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            check_visibility(item)
        self.tree.setUpdatesEnabled(True)

    def retrace_tab(self, inout):
        """Execute trace and filter view (In-Place)"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            print("No target selected for trace")
            return
        
        tar_sel = selected_targets[0]
        print(f"Trace {inout} for target: {tar_sel}")
        
        # 1. Get related targets
        related_targets = self.get_retrace_target(tar_sel, inout)
        
        # Add the selected target itself to the list so it's visible
        if tar_sel not in related_targets:
            if inout == 'in':
                related_targets.append(tar_sel) # Add to end
            else:
                related_targets.insert(0, tar_sel) # Add to start
        
        if not related_targets:
            print("No dependencies found.")
            return

        # 2. Filter the tree
        self.filter_tree_by_targets(set(related_targets))
        
        # 3. Update UI to show we are in Trace mode
        direction = "Up" if inout == 'in' else "Down"
        label_text = f"Trace {direction}: {tar_sel}"
        self.tab_label.setText(label_text)
        self.tab_label.setStyleSheet("border: none; font-weight: bold; color: #d32f2f; font-size: 13px;") # Red color for trace mode
        
        # 4. Ensure the selected target is visible and selected
        # (Optional: scroll to it)




    def set_column_widths(self):
        """Set column widths to user preferences"""
        self.tree.setColumnWidth(0, 104) # level
        self.tree.setColumnWidth(1, 625) # target
        self.tree.setColumnWidth(2, 95)  # status
        self.tree.setColumnWidth(3, 173) # start time
        self.tree.setColumnWidth(4, 179) # end time

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
