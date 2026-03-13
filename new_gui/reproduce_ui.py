import sys
import os
import re
import time
import warnings
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor

# Last Updated: 2026-03-05 19:00
warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from new_gui.services import action_flow
from new_gui.config.settings import (
    ANIMATION_DURATION_MS,
    BACKUP_TIMER_INTERVAL_MS,
    DEBOUNCE_DELAY_MS,
    FADE_IN_DURATION_MS,
    MAX_NOTIFICATIONS,
    NOTIFICATION_MARGIN_BOTTOM,
    NOTIFICATION_MARGIN_RIGHT,
    NOTIFICATION_SPACING,
    NOTIFICATION_TYPES,
    RE_ACTIVE_TARGETS,
    RE_ALL_RELATED,
    RE_DEPENDENCY_OUT,
    RE_LEVEL_LINE,
    RE_QUOTED_STRING,
    RE_TARGET_LEVEL,
    SHORTCUTS,
    STATUS_COLORS,
    STATUS_CONFIG,
    STYLES,
    THEMES,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    logger,
)
from new_gui.ui.dialogs.dependency_graph import DependencyGraphDialog
from new_gui.ui.dialogs.params_editor import ParamsEditorDialog
from new_gui.ui.dialogs.tune_dialogs import (
    CopyTuneDialog,
    CopyTuneSelectDialog,
    SelectTuneDialog,
)
from new_gui.services import run_repository
from new_gui.services import tune_actions
from new_gui.services import file_actions
from new_gui.services import run_views
from new_gui.services import search_flow
from new_gui.services import status_summary
from new_gui.services import tree_editing
from new_gui.services import view_tabs
from new_gui.services import view_modes
from new_gui.services import tree_rows
from new_gui.services import tree_structure
from new_gui.services import view_restore
from new_gui.services import view_state
from new_gui.ui.theme_runtime import ThemeManager
from new_gui.ui.widgets.delegates import BorderItemDelegate, TuneComboBoxDelegate
from new_gui.ui.widgets.filter_header import FilterHeaderView
from new_gui.ui.widgets.labels import ClickableLabel
from new_gui.ui.widgets.scrollbars import RoundedScrollBar
from new_gui.ui.widgets.status_bar import StatusBar


from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, Qt, QTimer, QObject,
                          QEvent, QModelIndex, QRect, pyqtSignal, QItemSelectionModel,
                          QPointF, QLineF, QFileSystemWatcher, QSize, QPoint,
                          QAbstractTableModel, QSortFilterProxyModel)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton, QCompleter,
                             QTreeView, QLineEdit, QHeaderView,
                             QGraphicsDropShadowEffect,
                             QSizePolicy, QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem,
                             QAbstractItemView, QStyleOptionComboBox,
                             QMenuBar, QAction, QDialog, QGraphicsScene, QGraphicsView,
                             QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
                             QGraphicsPolygonItem, QFileDialog, QCheckBox, QScrollArea,
                             QGroupBox, QMessageBox, QFrame, QShortcut, QShortcut,
                             QGraphicsRectItem, QGraphicsItem, QTableWidget, QTableWidgetItem,
                             QTableView, QItemDelegate, QInputDialog, QScrollBar,
                             QStyleOptionSlider)
from PyQt5.QtGui import (QStandardItemModel, QStandardItem, QColor, QBrush, QFont,
                         QFontMetrics, QPen, QPainter, QPolygonF,
                         QKeySequence, QIcon, QPixmap, QPainterPath)
import math


class TreeViewEventFilter(QObject):
    """Event filter for handling TreeView expand/collapse events"""
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
        """Toggle visibility of items for a given level"""
        if level not in self.level_items:
            return
            
        # Toggle expand state
        self.level_expanded[level] = not self.level_expanded.get(level, True)
        
        # Iterate all rows with the same level
        rows = self.level_items[level]
        if not rows:
            return
            
        # First item is always visible, others toggle based on expand state
        for i, row in enumerate(rows):
            if i == 0:  # First item
                continue
            self.tree_view.setRowHidden(row, QModelIndex(), not self.level_expanded[level])


class ColorTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Replace default scrollbars with rounded ones
        self._v_scrollbar = RoundedScrollBar(Qt.Vertical, self, show_step_buttons=True)
        self._h_scrollbar = RoundedScrollBar(Qt.Horizontal, self, show_step_buttons=True)
        self._v_scrollbar.setFixedWidth(16)
        self._h_scrollbar.setFixedHeight(16)
        self._v_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self._h_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self.setVerticalScrollBar(self._v_scrollbar)
        self.setHorizontalScrollBar(self._h_scrollbar)

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
    """Custom ComboBox with on-demand search mode and custom dropdown arrow"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(False) # Default to non-editable
        self.setMaxVisibleItems(10)
        self._arrow_color = QColor("#555555")
        self._arrow_color_hover = QColor("#333333")
        self._delegate = None  # Custom delegate for hiding current row
        self._popup_hidden_row = -1

        # Add search icon button
        self.search_btn = QPushButton(self)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedSize(18, 18)  # Slightly smaller to fit better
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 12px;
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

        self._popup_scrollbar = RoundedScrollBar(Qt.Vertical, self.view(), show_step_buttons=True)
        self._popup_scrollbar.setFixedWidth(16)
        self._popup_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self.view().setVerticalScrollBar(self._popup_scrollbar)
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view().setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setArrowColor(self, color):
        """Set the dropdown arrow color"""
        self._arrow_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw dropdown arrow"""
        super().paintEvent(event)

        # Draw custom dropdown arrow (double V-shaped, matching SVG style)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get the dropdown arrow rectangle
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        arrow_rect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        if arrow_rect.isValid():
            # Determine arrow color based on hover state
            if opt.state & QStyle.State_MouseOver:
                arrow_color = self._arrow_color_hover
            else:
                arrow_color = self._arrow_color

            # Draw double V-shaped arrow with rounded caps (matching SVG style)
            # SVG: M1 5L5 1L9 5 (up V) M9 11L5 15L1 11 (down V)
            pen = QPen(arrow_color)
            pen.setWidthF(1.5)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

            # Arrow dimensions (scaled to fit the arrow_rect)
            arrow_width = 6   # Total width of each V
            arrow_height = 3  # Height from tip to ends
            gap = 2           # Gap between the two V shapes

            center_x = arrow_rect.center().x()
            center_y = arrow_rect.center().y()

            # Upward V (∧) - above center
            up_v_tip = QPointF(center_x, center_y - gap - arrow_height)
            up_v_left = QPointF(center_x - arrow_width // 2, center_y - gap)
            up_v_right = QPointF(center_x + arrow_width // 2, center_y - gap)
            painter.drawLine(up_v_left, up_v_tip)
            painter.drawLine(up_v_tip, up_v_right)

            # Downward V (∨) - below center
            down_v_left = QPointF(center_x - arrow_width // 2, center_y + gap)
            down_v_tip = QPointF(center_x, center_y + gap + arrow_height)
            down_v_right = QPointF(center_x + arrow_width // 2, center_y + gap)
            painter.drawLine(down_v_left, down_v_tip)
            painter.drawLine(down_v_tip, down_v_right)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_search_button()

    def _position_search_button(self):
        """Position search button properly within the ComboBox"""
        # Get the dropdown arrow rectangle using style options
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        # Get the arrow sub-control rectangle
        arrow_rect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        # Calculate arrow width, with fallback to a reasonable default
        arrow_width = arrow_rect.width() if arrow_rect.width() > 0 else 20

        btn_size = self.search_btn.size()
        btn_width = btn_size.width()
        btn_height = btn_size.height()

        # Calculate button position:
        # Place it just to the left of the dropdown arrow
        # Ensure we have at least 2px margin from the arrow
        margin_from_arrow = 2
        x = self.width() - arrow_width - btn_width - margin_from_arrow

        # Ensure x is not negative (button would be outside left edge)
        # Also ensure button doesn't overlap with text area too much
        min_x = 5  # Minimum 5px from left edge
        x = max(min_x, x)

        # Center vertically
        y = (self.height() - btn_height) // 2

        # Ensure y is not negative
        y = max(1, y)

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
        # Only disable if currently editable (in search mode)
        if self.isEditable():
            self.setEditable(False)
        self.search_btn.show()
        # Reposition button after mode change
        self._position_search_button()

    def showPopup(self):
        # Hide current item from popup and position popup tightly below combobox
        current_idx = self.currentIndex()
        if self._popup_hidden_row >= 0:
            self.view().setRowHidden(self._popup_hidden_row, False)
        self._popup_hidden_row = current_idx
        if current_idx >= 0:
            self.view().setRowHidden(current_idx, True)

        super().showPopup()

        # Get the popup after showing
        popup = self.view().parentWidget()
        if popup:
            hidden_rows = 1 if current_idx >= 0 else 0
            visible_rows = max(1, min(self.count() - hidden_rows, self.maxVisibleItems()))
            row_height = self.view().sizeHintForRow(0)
            if row_height <= 0:
                row_height = 28
            frame_width = popup.frameWidth() if hasattr(popup, "frameWidth") else 0
            popup_width = self.width()
            popup_height = visible_rows * row_height + frame_width * 2
            popup.resize(popup_width, popup_height)

            # Position popup directly below combobox with no gap
            combo_bottom_left = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(combo_bottom_left)

    def hidePopup(self):
        # Restore the hidden popup row so future openings do not keep a gap
        if self._popup_hidden_row >= 0:
            self.view().setRowHidden(self._popup_hidden_row, False)
            self._popup_hidden_row = -1
            self.view().doItemsLayout()
            self.view().viewport().update()
        super().hidePopup()

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

class NotificationWidget(QFrame):
    """A single notification widget that shows at the corner of the screen"""

    clicked = pyqtSignal()

    def __init__(self, title, message, notification_type="info", parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.title = title
        self.message = message

        self._setup_ui()
        self._start_animation()

    def _setup_ui(self):
        """Setup the notification UI"""
        config = NOTIFICATION_TYPES.get(self.notification_type, NOTIFICATION_TYPES["info"])

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setFixedWidth(350)
        self.setCursor(Qt.PointingHandCursor)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Icon
        icon_label = QLabel(config["icon"])
        icon_label.setStyleSheet(f"""
            font-size: 24px;
            color: {config['color']};
        """)
        layout.addWidget(icon_label)

        # Text container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 13px;
            color: #333333;
        """)
        text_layout.addWidget(title_label)

        # Message
        message_label = QLabel(self.message)
        message_label.setStyleSheet("""
            font-size: 11px;
            color: #666666;
        """)
        message_label.setWordWrap(True)
        text_layout.addWidget(message_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 16px;
                color: #999999;
                background: transparent;
            }
            QPushButton:hover {
                color: #333333;
            }
        """)
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

        # Widget styling
        self.setStyleSheet(f"""
            NotificationWidget {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-left: 4px solid {config['color']};
                border-radius: 6px;
            }}
        """)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

    def _start_animation(self):
        """Start the entrance animation"""
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(ANIMATION_DURATION_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

    def fade_out(self):
        """Start fade out animation"""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(ANIMATION_DURATION_MS)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.finished.connect(self.deleteLater)
        self._fade_anim.start()

    def _on_close(self):
        """Handle close button click"""
        self.fade_out()

    def mousePressEvent(self, event):
        """Handle click on notification"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            self.fade_out()
        super().mousePressEvent(event)


# ========== Notification Manager ==========
class NotificationManager(QObject):
    """Manages notification widgets at the corner of the screen"""

    _instance = None

    def __new__(cls, parent=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return
        super().__init__(parent)
        self._initialized = True
        self._notifications = []
        self._parent = parent
        self._max_notifications = MAX_NOTIFICATIONS
        self._spacing = NOTIFICATION_SPACING
        self._margin_bottom = NOTIFICATION_MARGIN_BOTTOM
        self._margin_right = NOTIFICATION_MARGIN_RIGHT

    def show_notification(self, title, message, notification_type="info", duration=None):
        """Show a notification"""
        if not self._parent:
            return

        config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["info"])
        if duration is None:
            duration = config["duration"]

        # Create notification widget
        notification = NotificationWidget(title, message, notification_type, self._parent)
        notification.clicked.connect(lambda: self._remove_notification(notification))

        # Position it
        self._position_notification(notification)

        # Add to list
        self._notifications.append(notification)
        notification.show()

        # Auto-dismiss timer
        if duration > 0:
            QTimer.singleShot(duration, lambda: self._dismiss_notification(notification))

        return notification

    def _position_notification(self, notification):
        """Position a notification widget"""
        if not self._parent:
            return

        parent_rect = self._parent.rect()
        x = parent_rect.right() - notification.width() - self._margin_right
        y = parent_rect.bottom() - self._margin_bottom

        # Stack notifications
        for n in self._notifications:
            if n.isVisible():
                y -= n.height() + self._spacing

        # Move up if too many
        if len(self._notifications) >= self._max_notifications:
            oldest = self._notifications[0]
            self._dismiss_notification(oldest)

        notification.move(x, y)

    def _dismiss_notification(self, notification):
        """Dismiss a notification with animation"""
        if notification in self._notifications:
            notification.fade_out()
            self._notifications.remove(notification)
            self._reposition_all()

    def _remove_notification(self, notification):
        """Remove a notification from the list"""
        if notification in self._notifications:
            self._notifications.remove(notification)

    def _reposition_all(self):
        """Reposition all visible notifications"""
        if not self._parent:
            return

        parent_rect = self._parent.rect()
        y = parent_rect.bottom() - self._margin_bottom

        for notification in reversed(self._notifications):
            if notification.isVisible():
                x = parent_rect.right() - notification.width() - self._margin_right
                notification.move(x, y - notification.height())
                y -= notification.height() + self._spacing


# ========== Status Bar ==========
class MainWindow(QMainWindow):
    def __init__(self):
        # Initialize core variables FIRST
        self._init_core_variables()

        # Initialize theme manager
        self.theme_manager = ThemeManager()

        # Detect run base directory
        self._detect_run_base_dir()

        # Call parent constructor
        super().__init__()

        # Initialize window
        self._init_window()

        # Initialize UI components
        self._init_menu_bar()
        self._init_central_widget()
        self._init_top_panel()

        # Expand tree initially
        self.tree.expandAll()

    def _init_core_variables(self):
        """Initialize core instance variables."""
        self.level_expanded = {}
        self.combo_sel = None
        self.cached_targets_by_level = {}
        self.is_tree_expanded = True
        self.is_search_mode = False
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.colors = {k: v["color"] for k, v in STATUS_CONFIG.items()}
        self._tune_files_cache = {}
        self._bsub_params_cache = {}
        self._main_view_snapshot = None

    def _invalidate_tune_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate tune-file cache entries."""
        run_repository.invalidate_run_target_cache(
            self._tune_files_cache,
            run_dir,
            target_name,
        )

    def _invalidate_bsub_cache(self, run_dir: str = None, target_name: str = None) -> None:
        """Invalidate bsub-parameter cache entries."""
        run_repository.invalidate_run_target_cache(
            self._bsub_params_cache,
            run_dir,
            target_name,
        )

    def _invalidate_main_view_snapshot(self) -> None:
        """Drop the in-memory main-view snapshot."""
        self._main_view_snapshot = None

    def _capture_main_view_snapshot(self) -> None:
        """Capture the current main-view tree for fast restore."""
        current_run = self.combo.currentText()
        if not current_run or current_run == "No runs found":
            return
        self._main_view_snapshot = view_state.capture_main_view_snapshot(
            self.model,
            self.tree,
            current_run,
        )

    def _restore_main_view_snapshot(self) -> bool:
        """Restore the cached main-view snapshot if available."""
        return view_state.restore_main_view_snapshot(
            self.model,
            self.tree,
            self._main_view_snapshot,
            self.combo.currentText(),
            STATUS_COLORS,
            self.set_column_widths,
        )

    def _get_xmeta_background_color(self):
        """Return the configured XMETA background color, if any."""
        bg_color = os.environ.get("XMETA_BACKGROUND", "").strip()
        return bg_color or None

    def _detect_run_base_dir(self):
        """Detect the run base directory based on environment."""
        if os.path.exists("mock_runs"):
            self.run_base_dir = "mock_runs"
        elif os.path.exists(".target_dependency.csh"):
            self.run_base_dir = ".."
            logger.info(f"Detected run in current directory. Setting base to parent: {os.path.abspath(self.run_base_dir)}")
        else:
            self.run_base_dir = "."

    def _init_window(self):
        """Initialize window properties and animation."""
        self.setWindowTitle("XMeta Console")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.window_bg = self._get_xmeta_background_color() or "#f5f5f5"
        window_bg = self.window_bg

        # Fade-in animation for the window
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(FADE_IN_DURATION_MS)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.fade_anim.start()

        # Modern clean background
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {window_bg};
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_top_action_buttons()

    def _position_top_action_buttons(self):
        """Float the top action buttons independently from the main row layout."""
        if not hasattr(self, '_top_button_container') or not hasattr(self, 'top_panel'):
            return

        container = self._top_button_container
        container.adjustSize()
        right_margin = 16
        x_pos = self.top_panel.width() - right_margin - container.sizeHint().width()
        y_pos = 0
        container.move(max(0, x_pos), y_pos)
        container.raise_()

    def _init_menu_bar(self):
        """Initialize the menu bar."""
        self.menu_bar = self.menuBar()
        self._default_menu_bar_style = """
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                padding: 2px 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 14px;
                border-radius: 4px;
                color: #333333;
            }
            QMenuBar::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QMenuBar::item:pressed {
                background-color: #bbdefb;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 4px 12px;
            }
        """
        self.menu_bar.setStyleSheet(self._default_menu_bar_style)

        # Status Menu
        status_menu = self.menu_bar.addMenu("Status")
        show_all_status_action = QAction("Show All Status", self)
        show_all_status_action.triggered.connect(self.show_all_status)
        status_menu.addAction(show_all_status_action)

        # View Menu
        view_menu = self.menu_bar.addMenu("View")
        show_graph_action = QAction("Show Dependency Graph", self)
        show_graph_action.setShortcut(QKeySequence("Ctrl+G"))
        show_graph_action.triggered.connect(self.show_dependency_graph)
        view_menu.addAction(show_graph_action)

        # Theme submenu
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("Theme")
        light_theme_action = QAction("Light Theme", self)
        light_theme_action.triggered.connect(lambda: self.apply_theme("light"))
        theme_menu.addAction(light_theme_action)
        dark_theme_action = QAction("Dark Theme", self)
        dark_theme_action.triggered.connect(lambda: self.apply_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        high_contrast_action = QAction("High Contrast", self)
        high_contrast_action.triggered.connect(lambda: self.apply_theme("high_contrast"))
        theme_menu.addAction(high_contrast_action)

        # Tools Menu
        tools_menu = self.menu_bar.addMenu("Tools")
        user_params_action = QAction("📝 User Params", self)
        user_params_action.setShortcut(QKeySequence("Ctrl+P"))
        user_params_action.setToolTip("Edit user.params for current run")
        user_params_action.triggered.connect(self.open_user_params)
        tools_menu.addAction(user_params_action)
        tile_params_action = QAction("📋 Tile Params", self)
        tile_params_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        tile_params_action.setToolTip("View tile.params for current run")
        tile_params_action.triggered.connect(self.open_tile_params)
        tools_menu.addAction(tile_params_action)

        # Track if we are in "All Status" view mode
        self.is_all_status_view = False

    def _init_central_widget(self):
        """Initialize the central widget and main layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._main_layout = QVBoxLayout(central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._main_layout.setAlignment(Qt.AlignTop)

    def _init_top_panel(self):
        """Initialize the top control panel."""
        self.top_panel = QWidget()
        self.top_panel.setObjectName("topPanel")
        self.top_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._default_top_panel_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef)"
        self.top_panel.setStyleSheet("""
            #topPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-radius: 0px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.top_panel.setGraphicsEffect(shadow)

        top_layout = QVBoxLayout(self.top_panel)
        top_layout.setContentsMargins(16, 8, 16, 8)
        top_layout.setSpacing(6)

        # Row 1 of Top Panel
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)

        # Create combo box with bounded popup
        self.combo = BoundedComboBox()
        self.populate_run_combo()
        self.combo.setMinimumWidth(300)
        self.combo.currentIndexChanged.connect(self.on_run_changed)
        self.combo.setStyleSheet("""
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
        """)

        # Buttons - Modern clean style
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

        # Action button style (for primary actions like run)
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

        # Warning button style (for stop, skip, invalid)
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

        self.buttons_row1 = ["run all", "run", "stop", "skip", "unskip", "invalid"]
        self.buttons_row2 = ["term", "csh", "log", "cmd", "trace up", "trace dn"]

        row1_layout.addWidget(self.combo)

        button_container = QWidget(self.top_panel)
        button_container.setAttribute(Qt.WA_TranslucentBackground, True)
        button_container.setStyleSheet("background: transparent; border: none;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        # Create buttons and connect to commands
        bt_runall = QPushButton("Run All")
        bt_runall.setStyleSheet(action_btn_style)
        bt_runall.clicked.connect(lambda: self.start('XMeta_run all'))
        button_layout.addWidget(bt_runall)

        bt_run = QPushButton("Run")
        bt_run.setStyleSheet(action_btn_style)
        bt_run.clicked.connect(lambda: self.start('XMeta_run'))
        button_layout.addWidget(bt_run)

        bt_stop = QPushButton("Stop")
        bt_stop.setStyleSheet(warning_btn_style)
        bt_stop.clicked.connect(lambda: self.start('XMeta_stop'))
        button_layout.addWidget(bt_stop)

        bt_skip = QPushButton("Skip")
        bt_skip.setStyleSheet(warning_btn_style)
        bt_skip.clicked.connect(lambda: self.start('XMeta_skip'))
        button_layout.addWidget(bt_skip)

        bt_unskip = QPushButton("Unskip")
        bt_unskip.setStyleSheet(btn_style)
        bt_unskip.clicked.connect(lambda: self.start('XMeta_unskip'))
        button_layout.addWidget(bt_unskip)

        bt_invalid = QPushButton("Invalid")
        bt_invalid.setStyleSheet(warning_btn_style)
        bt_invalid.clicked.connect(lambda: self.start('XMeta_invalid'))
        button_layout.addWidget(bt_invalid)

        button_container.adjustSize()
        self._top_button_container = button_container
        self._top_button_placeholder = QWidget()
        self._top_button_placeholder.setStyleSheet("background: transparent; border: none;")
        self._top_button_placeholder.setFixedWidth(button_container.sizeHint().width())
        row1_layout.addWidget(self._top_button_placeholder)

        top_layout.addLayout(row1_layout)
        self._main_layout.addWidget(self.top_panel)

        # Tab Bar (Modern clean look)
        self.tab_bar = QWidget()
        self.tab_bar.setObjectName("tabBar")
        # Derive a slightly darker shade from the window background
        _tab_bg_color = QColor(self.window_bg).darker(120)
        _tab_bg_hex = _tab_bg_color.name()
        self._default_tab_bar_style = f"""
            #tabBar {{
                background-color: {_tab_bg_hex};
                border-bottom: 1px solid #d0d0d0;
            }}
        """
        self.tab_bar.setStyleSheet(self._default_tab_bar_style)
        tab_layout = QHBoxLayout(self.tab_bar)
        tab_layout.setContentsMargins(12, 2, 12, 2)
        tab_layout.setSpacing(2)

        # Custom Tab Widget (Container for label + close button)
        self.tab_widget = QWidget()
        self.tab_widget.setObjectName("tabWidget")
        # Use a slightly lighter shade than tab bar for the active tab
        _tab_widget_bg = QColor(self.window_bg).lighter(108)
        _tab_widget_bg_hex = _tab_widget_bg.name()
        self.tab_widget.setStyleSheet(f"""
            #tabWidget {{
                background-color: {_tab_widget_bg_hex};
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)
        tab_inner_layout = QHBoxLayout(self.tab_widget)
        tab_inner_layout.setContentsMargins(14, 4, 10, 4)
        tab_inner_layout.setSpacing(6)

        self.tab_label = ClickableLabel("") # Initial empty, will be set by update_ui_from_selection
        self.tab_label.doubleClicked.connect(self.toggle_tree_expansion)
        self.tab_label.setToolTip("Double-click to Expand/Collapse All")
        self.tab_label.setStyleSheet(view_tabs.MAIN_RUN_TAB_STYLE)

        self.tab_close_btn = QPushButton("×")
        self.tab_close_btn.setFixedSize(20, 20)
        self.tab_close_btn.setCursor(Qt.PointingHandCursor)
        self.tab_close_btn.setToolTip("Close Tab")
        self.tab_close_btn.clicked.connect(self.close_tree_view)
        self.tab_close_btn.setStyleSheet("""
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
        """)

        tab_inner_layout.addWidget(self.tab_label)
        tab_inner_layout.addWidget(self.tab_close_btn)

        tab_layout.addWidget(self.tab_widget)
        tab_layout.addStretch()
        row1_layout.insertWidget(1, self.tab_bar, 1)
        QTimer.singleShot(0, self._position_top_action_buttons)

        # Tree View
        self.tree = ColorTreeView()

        # Set custom header with embedded filter for target column
        self.header = FilterHeaderView(Qt.Horizontal, self.tree, filter_column=1)
        self.tree.setHeader(self.header)
        self.header.filter_changed.connect(self._on_header_filter_changed)
        self.header.level_double_clicked.connect(self.toggle_tree_expansion)

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
                background: rgba(255, 255, 255, 0.96);
                border: none;
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                border-radius: 10px;
                padding: 6px 4px 4px 4px;
            }
            QTreeView::item {
                height: 17px;
                padding: 5px 6px;
                border: none;
            }
            QTreeView:focus {
                outline: none;
            }
            QHeaderView::section {
                background: rgba(247,249,252,0.98);
                padding: 7px 12px;
                border: none;
                border-bottom: 1px solid rgba(148, 163, 184, 0.35);
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                font-weight: 600;
                color: #475569;
            }
            QTreeView::item:hover {
                background: transparent;
            }
            QTreeView::item:selected {
                background: transparent;
                color: #000000 !important;
                outline: none;
            }
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
        tree_rows.set_main_tree_headers(self.model)
        self.tree.setModel(self.model)
        
        # Simple column width setup
        self.set_column_widths()

        # Initialize TreeViewEventFilter
        self.tree_view_event_filter = TreeViewEventFilter(self.tree, self)
        self.tree.viewport().installEventFilter(self.tree_view_event_filter)

        # Set ComboBox delegate for tune column (column 3)
        self.tune_delegate = TuneComboBoxDelegate(self.tree)
        self.tree.setItemDelegateForColumn(3, self.tune_delegate)

        self._main_layout.addWidget(self.tree)

        # Set right-click context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Connect double-click signal for copy functionality in All Status view
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)

        # ========== Add Status Bar ==========
        self._status_bar = StatusBar(self)
        self._status_bar.status_filter_requested.connect(self.on_status_badge_double_clicked)
        self._main_layout.addWidget(self._status_bar)

        # ========== Initialize Notification Manager ==========
        self._notification_manager = NotificationManager(self)

        # Apply XMETA background after all container widgets exist.
        self._init_top_panel_background()

        # ========== Setup Keyboard Shortcuts ==========
        self._setup_keyboard_shortcuts()

        # Align the initial window width with the main-view column defaults.
        self._apply_initial_window_width()

        # Initial UI Update
        self.on_run_changed()

        # Setup file system watcher for efficient status monitoring (replaces polling timer)
        self.status_watcher = QFileSystemWatcher(self)
        self.status_watcher.directoryChanged.connect(self.on_status_directory_changed)
        self.status_watcher.fileChanged.connect(self.on_status_file_changed)

        # Track watched directories to avoid duplicates
        self.watched_status_dirs = set()

        # Setup initial watch on current run's status directory
        self.setup_status_watcher()

        # Backup timer with longer interval as fallback
        # This handles cases where file watcher might miss events
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.change_run)
        self.backup_timer.start(BACKUP_TIMER_INTERVAL_MS)

        # Debounce timer to batch rapid file changes
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.change_run)

        # Expand all
        self.tree.expandAll()

    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts"""
        # Search focus
        shortcut_search = QShortcut(QKeySequence(SHORTCUTS["search"]["key"]), self)
        shortcut_search.activated.connect(self._focus_search)
        shortcut_search.setContext(Qt.ApplicationShortcut)

        # Refresh
        shortcut_refresh = QShortcut(QKeySequence(SHORTCUTS["refresh"]["key"]), self)
        shortcut_refresh.activated.connect(self._refresh_view)
        shortcut_refresh.setContext(Qt.ApplicationShortcut)

        # Expand all
        shortcut_expand = QShortcut(QKeySequence(SHORTCUTS["expand_all"]["key"]), self)
        shortcut_expand.activated.connect(self.tree.expandAll)
        shortcut_expand.setContext(Qt.ApplicationShortcut)

        # Collapse all
        shortcut_collapse = QShortcut(QKeySequence(SHORTCUTS["collapse_all"]["key"]), self)
        shortcut_collapse.activated.connect(self.tree.collapseAll)
        shortcut_collapse.setContext(Qt.ApplicationShortcut)

        # Toggle theme
        shortcut_theme = QShortcut(QKeySequence(SHORTCUTS["toggle_theme"]["key"]), self)
        shortcut_theme.activated.connect(self._toggle_theme)
        shortcut_theme.setContext(Qt.ApplicationShortcut)

        # Show dependency graph
        shortcut_graph = QShortcut(QKeySequence(SHORTCUTS["show_graph"]["key"]), self)
        shortcut_graph.activated.connect(self.show_dependency_graph)
        shortcut_graph.setContext(Qt.ApplicationShortcut)

        # Copy target name
        shortcut_copy = QShortcut(QKeySequence(SHORTCUTS["copy_target"]["key"]), self)
        shortcut_copy.activated.connect(self._copy_selected_target)
        shortcut_copy.setContext(Qt.ApplicationShortcut)

        # Run selected
        shortcut_run = QShortcut(QKeySequence(SHORTCUTS["run_selected"]["key"]), self)
        shortcut_run.activated.connect(lambda: self.start('XMeta_run'))
        shortcut_run.setContext(Qt.ApplicationShortcut)

        # Trace up
        shortcut_trace_up = QShortcut(QKeySequence(SHORTCUTS["trace_up"]["key"]), self)
        shortcut_trace_up.activated.connect(lambda: self.retrace_tab('in'))
        shortcut_trace_up.setContext(Qt.ApplicationShortcut)

        # Trace down
        shortcut_trace_down = QShortcut(QKeySequence(SHORTCUTS["trace_down"]["key"]), self)
        shortcut_trace_down.activated.connect(lambda: self.retrace_tab('out'))
        shortcut_trace_down.setContext(Qt.ApplicationShortcut)

        # User params
        shortcut_user_params = QShortcut(QKeySequence(SHORTCUTS["user_params"]["key"]), self)
        shortcut_user_params.activated.connect(self.open_user_params)
        shortcut_user_params.setContext(Qt.ApplicationShortcut)

        # Tile params
        shortcut_tile_params = QShortcut(QKeySequence(SHORTCUTS["tile_params"]["key"]), self)
        shortcut_tile_params.activated.connect(self.open_tile_params)
        shortcut_tile_params.setContext(Qt.ApplicationShortcut)

    def _focus_search(self):
        """Focus the search input - shows the embedded filter in header"""
        if hasattr(self, 'quick_search_input'):
            self.quick_search_input.setFocus()
            self.quick_search_input.selectAll()
        elif hasattr(self, 'header'):
            self.header.show_filter()

    def _set_quick_search_text(self, text):
        """Update the persistent search field without triggering another filter pass."""
        if hasattr(self, 'quick_search_input'):
            was_blocked = self.quick_search_input.blockSignals(True)
            self.quick_search_input.setText(text)
            self.quick_search_input.blockSignals(was_blocked)

    def _set_header_filter_text_silent(self, text):
        """Update the header search state without emitting filter_changed again."""
        if not hasattr(self, 'header'):
            return

        self.header._filter_text = text
        if self.header.filter_edit:
            was_blocked = self.header.filter_edit.blockSignals(True)
            self.header.filter_edit.setText(text)
            self.header.filter_edit.blockSignals(was_blocked)

    def _on_top_search_changed(self, text):
        """Keep the header search state in sync with the visible search field."""
        self._set_header_filter_text_silent(text)
        self.filter_tree(text)

    def _on_header_filter_changed(self, text):
        """Mirror header search edits back to the visible search field."""
        self._set_quick_search_text(text)
        self.filter_tree(text)

    def _refresh_view(self):
        """Refresh the current view"""
        current_run = self.combo.currentText()
        if current_run and current_run != "No runs found":
            self._build_status_cache(current_run)
            self.populate_data()
            self.show_notification("Refresh", f"Refreshed view for {current_run}", "info")

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        new_theme = self.theme_manager.toggle_theme()
        self.apply_theme(new_theme)
        self.show_notification("Theme", f"Switched to {THEMES[new_theme]['name']} theme", "info")

    def _copy_selected_target(self):
        """Copy selected target name to clipboard"""
        targets = self._exit_search_mode_and_get_targets()
        if targets:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(targets))
            self.show_notification("Copied", f"Copied {len(targets)} target(s)", "success")

    def apply_theme(self, theme_name):
        """Apply a theme to the application"""
        self.theme_manager.set_theme(theme_name)
        theme = self.theme_manager.get_theme()
        bg_color = self._get_xmeta_background_color()
        window_bg = bg_color or theme['window_bg']

        # Determine scrollbar colors based on theme
        if theme_name == "dark":
            scrollbar_bg = "#2d2d2d"
            scrollbar_handle = "#555555"
            scrollbar_handle_hover = "#666666"
            scrollbar_handle_pressed = "#444444"
        else:
            scrollbar_bg = "#f5f5f5"
            scrollbar_handle = "#c0c0c0"
            scrollbar_handle_hover = "#a0a0a0"
            scrollbar_handle_pressed = "#808080"

        # Update custom scrollbar colors
        if hasattr(self.tree, '_v_scrollbar'):
            self.tree._v_scrollbar.setColors(
                scrollbar_handle, scrollbar_handle_hover, scrollbar_handle_pressed, scrollbar_bg
            )
        if hasattr(self.tree, '_h_scrollbar'):
            self.tree._h_scrollbar.setColors(
                scrollbar_handle, scrollbar_handle_hover, scrollbar_handle_pressed, scrollbar_bg
            )

        # Apply main window stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {window_bg};
            }}
            QTreeView {{
                background: {theme['tree_bg']};
                color: {theme['text_color']};
                border: none;
                border-radius: 10px;
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                padding: 6px 4px 4px 4px;
            }}
            QTreeView::item {{
                height: 17px;
                padding: 5px 6px;
                border: none;
            }}
            QTreeView::item:hover {{
                background: {theme['hover_bg']};
            }}
            QTreeView::item:selected {{
                background: {theme['selection_bg']};
                color: {theme['text_color']};
            }}
            QHeaderView::section {{
                background: {theme['panel_bg']};
                padding: 7px 12px;
                border: none;
                border-bottom: 1px solid {theme['border_color']};
                font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                font-size: 10pt;
                font-weight: 600;
                color: {theme['text_color']};
            }}
            QMenuBar {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border-bottom: 1px solid {theme['border_color']};
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {theme['menu_hover']};
                color: #1976d2;
            }}
            QMenu {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 8px 24px;
            }}
            QMenu::item:selected {{
                background-color: {theme['menu_hover']};
                color: #1976d2;
            }}
            QComboBox {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QLineEdit {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QPushButton {{
                background-color: {theme['menu_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme['menu_hover']};
            }}
            QLabel {{
                color: {theme['text_color']};
            }}
        """)

        # Update status bar
        if hasattr(self, '_status_bar'):
            self._status_bar.update_theme(theme_name)
        if bg_color:
            self._init_top_panel_background()

        # Show notification
        theme_info = THEMES.get(theme_name, THEMES["light"])
        self.show_notification("Theme", f"Applied {theme_info['name']} theme", "info")

    def show_notification(self, title, message, notification_type="info"):
        """Show a notification message"""
        if hasattr(self, '_notification_manager'):
            self._notification_manager.show_notification(title, message, notification_type)

    def update_status_bar(self):
        """Update the status bar with current statistics"""
        if not hasattr(self, '_status_bar'):
            return

        # Get current run
        current_run = self.combo.currentText()
        self._status_bar.update_run(current_run)

        # Always compute stats from the full run graph, not current filtered model.
        stats = self._compute_full_run_stats(current_run)

        self._status_bar.update_stats(stats)

        # Update connection status (always connected for file system)
        self._status_bar.update_connection(True)

    def _compute_full_run_stats(self, run_name):
        """Compute status statistics from the complete target set of a run."""
        if not run_name or run_name == "No runs found":
            return status_summary.build_empty_stats()

        targets_by_level = self.parse_dependency_file(run_name)
        return status_summary.compute_run_stats(
            targets_by_level,
            lambda target_name: self.get_target_status(run_name, target_name),
        )

    def close_tree_view(self):
        """Close the tree view (or clear active filtered view)."""
        mode = view_modes.get_active_view_mode(
            getattr(self, 'is_all_status_view', False),
            self.tab_label.text() if hasattr(self, 'tab_label') else "",
        )

        # If we are in All Status view, restore normal view
        if mode == "all_status":
            self.restore_normal_view()
            return

        # If a status in-place filter is active, rebuild main view.
        if mode == "status":
            self._set_filtered_main_view_tab_state()
            if not self._restore_main_view_snapshot():
                self.populate_data(force_rebuild=True)
            return

        # If a trace in-place filter is active, clear the filter by unhiding rows.
        if mode == "trace":
            view_state.clear_trace_filter(self.tree, self.model)
            self._set_filtered_main_view_tab_state()
            return

        # Otherwise hide the tree view (original behavior)
        if hasattr(self, 'tree'):
            self.tree.hide()
        if hasattr(self, 'tab_bar'):
            self.tab_bar.hide()

    def get_selected_targets(self):
        """Get currently selected targets from tree view."""
        return view_state.get_selected_targets(self.tree, self.model)

    def _get_current_search_text(self) -> str:
        """Return the current search text from the header filter state."""
        if hasattr(self, 'header'):
            return self.header.get_filter_text()
        return ""

    def _select_targets_in_tree(self, target_names):
        """Select targets in the tree by their names.

        Args:
            target_names: List of target names to select
        """
        view_state.select_targets_in_tree(self.tree, self.model, target_names)

    def _build_search_context(self, selected_targets=None) -> dict:
        """Capture the current search mode, text, and selected targets."""
        targets = self.get_selected_targets() if selected_targets is None else selected_targets
        return search_flow.build_search_context(
            self.is_search_mode,
            self._get_current_search_text(),
            targets,
        )

    def _rebuild_main_tree_now(self) -> None:
        """Rebuild the main tree immediately using the current run selection."""
        self.model.clear()
        self.populate_data()

    def _clear_search_ui_state(self) -> None:
        """Clear the visible and embedded search UI state without rebuilding."""
        if hasattr(self, 'header'):
            self._set_header_filter_text_silent("")
            self.header.hide_filter()
        self._set_quick_search_text("")
        self.is_search_mode = False

    def _get_selected_targets_keep_search(self):
        """Get selected targets while keeping search mode active.

        This method gets selected targets without exiting search mode.
        Used for operations that should maintain search state after execution.

        Returns:
            tuple: (selected_targets, search_context)
        """
        selected_targets = self.get_selected_targets()
        return selected_targets, self._build_search_context(selected_targets)

    def _refresh_after_action(self, search_context):
        """Refresh the view after an action, preserving search state if needed.

        Args:
            search_context: Captured search context from before the action
        """
        current_run = self.combo.currentText()
        search_flow.refresh_after_action(
            search_context,
            current_run,
            self._build_status_cache,
            self._rebuild_main_tree_now,
            self.filter_tree,
        )

    def _exit_search_mode_and_get_targets(self):
        """Exit search mode if active and return selected targets.

        This method handles the transition from search mode to normal mode:
        1. Saves selected targets from search results
        2. Clears search filter and restores full tree
        3. Re-selects the saved targets in the restored tree
        4. Returns the list of selected target names

        Returns:
            list: Selected target names
        """
        if self.is_search_mode:
            # Save currently selected targets from search results
            selected_targets = self.get_selected_targets()
            search_context = self._build_search_context(selected_targets)
            logger.info(f"Exiting search mode with {len(selected_targets)} selected targets")

            return search_flow.exit_search_mode(
                search_context,
                self._clear_search_ui_state,
                self._rebuild_main_tree_now,
                self._select_targets_in_tree,
            )
        else:
            return self.get_selected_targets()

    def _log_action_result(self, command: str, result: dict, include_returncode: bool = False) -> None:
        """Log the outcome of a shell action using the existing UI logging policy."""
        if result.get("stdout"):
            logger.info(result["stdout"])
        if result.get("stderr"):
            logger.error(result["stderr"])
        if result.get("timed_out"):
            logger.error(f"Command timed out: {command}")
        if result.get("error") is not None:
            logger.error(f"Error executing command: {result['error']}")
        if include_returncode and result.get("returncode") not in (None, 0):
            logger.error(f"Command exited with code {result['returncode']}")

    def start(self, action):
        """Execute flow action and refresh view (runs command in background thread)."""
        # Get selected targets while keeping search mode state
        selected_targets, search_context = self._get_selected_targets_keep_search()

        if not selected_targets:
            logger.warning(f"No targets selected for action: {action}")
            return

        # Get current run name
        current_run = self.combo.currentText()
        action_request = action_flow.build_action_request(
            self.run_base_dir,
            current_run,
            action,
            selected_targets,
        )
        logger.info(action_request["log_message"])

        # For skip/unskip, execute synchronously to ensure status files are updated before refresh
        if action_request["run_sync"]:
            result = action_flow.execute_shell_command(
                action_request["command"],
                action_request["timeout"],
            )
            self._log_action_result(action_request["command"], result)

            # Refresh while preserving search state
            self._refresh_after_action(search_context)
        else:
            # Execute other commands in background thread
            # Store search state for later use in refresh
            def run_command():
                result = action_flow.execute_shell_command(
                    action_request["command"],
                    action_request["timeout"],
                )
                self._log_action_result(
                    action_request["command"],
                    result,
                    include_returncode=True,
                )

            self._executor.submit(run_command)

        # Clear selection after operation
        self.tree.clearSelection()

    def filter_tree(self, text):
        """Filter tree items based on text input.
        If text is empty, restore full hierarchy.
        If text is present, show FLAT list of matching items (no parents).
        """
        logger.debug(f"filter_tree called with text='{text}'")

        # Update search mode flag
        if text:
            self.is_search_mode = True
        else:
            self.is_search_mode = False

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
        self._reset_main_tree_model()

        matching_groups = tree_structure.filter_level_groups_by_text(self.cached_targets_by_level, text)
        self._append_target_groups_to_model(matching_groups)

        for row in range(self.model.rowCount()):
            parent_item = self.model.item(row, 0)
            if parent_item and parent_item.hasChildren():
                self.tree.expand(parent_item.index())
                    
        self.tree.setUpdatesEnabled(True)

    def toggle_tree_expansion(self):
        """Toggle between Expand All and Collapse All"""
        if self.is_tree_expanded:
            self.tree.collapseAll()
        else:
            self.tree.expandAll()
        self.is_tree_expanded = not self.is_tree_expanded

    def _filter_tree_by_status_flat(self, status):
        """Show status-filtered targets using main-view tree hierarchy."""
        status_key = (status or "").strip().lower()
        if not status_key:
            return 0

        if not hasattr(self, 'cached_targets_by_level') or not self.cached_targets_by_level:
            current_run = self.combo.currentText()
            if current_run and current_run != "No runs found":
                self.cached_targets_by_level = self.parse_dependency_file(current_run)

        if not self.cached_targets_by_level:
            return 0

        self.tree.setUpdatesEnabled(False)
        self._reset_main_tree_model()

        current_run = self.combo.currentText()
        matched_groups = tree_structure.filter_level_groups_by_status(
            self.cached_targets_by_level,
            lambda target_name: self.get_target_status(current_run, target_name),
            status_key,
        )
        matched_count = self._append_target_groups_to_model(
            matched_groups,
            run_name=current_run,
            status_value=status_key,
        )

        self.tree.setUpdatesEnabled(True)
        self.tree.expandAll()
        return matched_count

    def _apply_status_filter(self, status, update_tab=True):
        """Apply in-place status filter to the target tree."""
        if not (hasattr(self, 'tab_label') and self.tab_label.text().startswith("Status: ")):
            self._capture_main_view_snapshot()

        matched_count = self._filter_tree_by_status_flat(status)
        if matched_count <= 0:
            self.show_notification("Status Filter", f"No targets with status: {status}", "info")
            return

        if update_tab and hasattr(self, 'tab_label'):
            self._apply_tab_state(view_tabs.get_status_tab_state(status))

    def on_status_badge_double_clicked(self, status):
        """Handle status badge double-click from the bottom status bar."""
        if self.is_all_status_view:
            self.show_notification("Status Filter", "Status badge filter is available in main target view only", "info")
            return
        self._apply_status_filter(status, update_tab=True)

    def scan_runs(self):
        """Scan the run base directory for valid run directories.
        A valid run directory contains a .target_dependency.csh file.
        """
        return run_repository.scan_runs(self.run_base_dir)

    def show_all_status(self):
        """Show status summary of all run directories in the TreeView.
        Displays: Run Directory, Latest Target, Status, Time Stamp
        """
        logger.debug("show_all_status called")
        
        # Set flag to indicate we are in "All Status" view
        self.is_all_status_view = True
        self._set_all_status_tab_state()
        
        # Scan all runs
        overview_rows = run_repository.collect_all_status_overview(self.run_base_dir)
        self._populate_all_status_overview(overview_rows)
        self._apply_all_status_column_widths()
        logger.debug(f"show_all_status completed, showing {len(overview_rows)} runs")

    def _apply_all_status_column_widths(self):
        """Use adaptive widths for the four-column all-status overview."""
        if not hasattr(self, 'tree') or not hasattr(self, 'model'):
            return
        if self.model.columnCount() < 4:
            return

        header = self.tree.header()
        if header is None:
            return

        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(2)
        self.tree.resizeColumnToContents(3)

        header_min_widths = self._get_header_min_widths()
        for col in range(4):
            min_width = header_min_widths.get(col, 0)
            if min_width > 0:
                self.tree.setColumnWidth(col, max(self.tree.columnWidth(col), min_width))

    def _get_header_min_widths(self):
        """Calculate per-column minimum widths to fully show header text."""
        if not hasattr(self, 'tree') or not hasattr(self, 'model'):
            return {}

        header = self.tree.header()
        if header is None:
            return {}

        header_font = header.font()
        font_metrics = QFontMetrics(header_font)
        min_widths = {}

        for col in range(self.model.columnCount()):
            header_text = self.model.headerData(col, Qt.Horizontal) or ""
            text_based_min = font_metrics.horizontalAdvance(str(header_text)) + 30
            style_based_min = header.sectionSizeFromContents(col).width() + 8
            min_widths[col] = max(text_based_min, style_based_min)

        return min_widths

    def _get_main_view_default_column_widths(self):
        """Return the default width plan for the main tree view."""
        font_metrics = self.tree.fontMetrics()
        status_values = ["finish", "running", "failed", "skip", "scheduled", "pending"]
        status_width = max(font_metrics.horizontalAdvance(status) for status in status_values) + 20

        time_format = "YYYY-MM-DD HH:MM:SS"
        time_width = font_metrics.horizontalAdvance(time_format) + 20

        return {
            0: 80,
            1: 400,
            2: status_width,
            3: 120,
            4: time_width,
            5: time_width,
            6: 100,
            7: 60,
            8: 80,
        }

    def _get_main_view_default_window_width(self):
        """Estimate the startup window width from the main-view column defaults."""
        column_widths = self._get_main_view_default_column_widths()
        tree_content_width = sum(column_widths.values())
        scrollbar_width = self.tree.verticalScrollBar().sizeHint().width()
        frame_width = self.tree.frameWidth() * 2
        return tree_content_width + scrollbar_width + frame_width

    def _apply_initial_window_width(self):
        """Resize the startup window to match the main-view default tree width."""
        desired_width = max(
            self._get_main_view_default_window_width(),
            self.minimumSizeHint().width(),
        )
        self.resize(desired_width, WINDOW_HEIGHT)

    def restore_normal_view(self):
        """Restore the normal single-run TreeView from All Status view."""
        if self.is_all_status_view:
            self._activate_selected_run_view(self.combo.currentText(), invalidate_snapshot=True)

    def on_tree_double_clicked(self, index):
        """Handle double-click on tree view"""
        # In All Status view, copy run name
        if self.is_all_status_view:
            run_name = tree_editing.get_all_status_run_name(self.model, index)
            if run_name:
                clipboard = QApplication.clipboard()
                clipboard.setText(run_name)
                logger.info(f"Copied run name to clipboard: {run_name}")
            return

        edit_context = tree_editing.build_bsub_edit_context(self.model, index)
        if not edit_context:
            return

        target = edit_context["target_name"]
        param_type = edit_context["param_type"]
        current_value = edit_context["current_value"]
        header = edit_context["header_text"]

        # Show input dialog
        new_value, ok = QInputDialog.getText(
            self,
            f"Edit {header}",
            f"Enter new {param_type} value for '{target}':",
            QLineEdit.Normal,
            current_value
        )

        if ok and new_value != current_value:
            validation_error = tree_editing.validate_bsub_value(param_type, new_value)
            if validation_error:
                QMessageBox.warning(self, "Invalid Input", validation_error)
                return

            # Save to csh file
            if self.save_bsub_param(self.combo_sel, target, param_type, new_value):
                # Update the model
                self.model.setData(index, new_value)
                self.show_notification("Saved", f"Updated {param_type} to {new_value} for {target}", "success")
            else:
                QMessageBox.warning(self, "Error", f"Failed to update {param_type} for {target}. Check if .csh file exists.")

    def build_dependency_graph(self, run_name):
        """
        Build dependency graph data from .target_dependency.csh file.

        Returns:
            dict with 'nodes', 'edges', and 'levels' for DependencyGraphDialog
        """
        graph_data = run_repository.build_dependency_graph(
            self.run_base_dir,
            run_name,
            getattr(self, "_status_cache", None),
        )
        logger.debug(
            f"Built graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges"
        )
        return graph_data

    def show_dependency_graph(self):
        """Show the dependency graph dialog for the current run."""
        current_run = self.combo.currentText()
        if not current_run or current_run == "No runs found":
            logger.warning("No run selected")
            return

        # Build graph data
        graph_data = self.build_dependency_graph(current_run)

        # Show dialog
        dialog = DependencyGraphDialog(graph_data, self.colors, self)
        dialog.exec_()

    def open_user_params(self):
        """Open user.params file for editing."""
        if not self.combo_sel or not os.path.exists(self.combo_sel):
            self.show_notification("Error", "No run selected or run directory not found", "error")
            return

        try:
            user_params_file, created = file_actions.ensure_user_params_file(self.combo_sel)
            if created:
                self.show_notification("Created", "Created new user.params file", "success")
        except Exception as e:
            self.show_notification("Error", f"Failed to create user.params: {e}", "error")
            return

        dialog = ParamsEditorDialog(user_params_file, "user", self)
        dialog.exec_()

    def open_tile_params(self):
        """Open tile.params file for viewing (read-only)."""
        if not self.combo_sel or not os.path.exists(self.combo_sel):
            self.show_notification("Error", "No run selected or run directory not found", "error")
            return

        tile_params_file = file_actions.get_tile_params_file(self.combo_sel)
        if not tile_params_file:
            self.show_notification("Not Found", f"tile.params file not found in current run", "warning")
            return

        dialog = ParamsEditorDialog(tile_params_file, "tile", self)
        dialog.exec_()

    def populate_run_combo(self):
        """Populate the combo box with available run directories."""
        runs = self.scan_runs()
        if runs:
            self.combo.addItems(runs)
            
            # Try to detect current run from working directory
            # If we are inside a run directory, the basename of cwd should match a run name
            current_cwd_name = os.path.basename(os.getcwd())
            
            logger.info(f"Current working directory basename: {current_cwd_name}")
            logger.info(f"Available runs: {runs}")
            
            if current_cwd_name in runs:
                index = self.combo.findText(current_cwd_name)
                if index >= 0:
                    self.combo.setCurrentIndex(index)
                    logger.info(f"Selected run: {current_cwd_name}")
            else:
                # Default to the first item if current cwd is not a valid run
                self.combo.setCurrentIndex(0)
                logger.info(f"Selected first run: {runs[0]}")
        else:
            # Fallback if no runs found
            self.combo.addItem("No runs found")
            self.combo.setEnabled(False)

    def parse_dependency_file(self, run_name):
        """Parse .target_dependency.csh file to extract target-level mappings.

        Returns:
            dict: Mapping of level number to list of target names
        """
        return run_repository.parse_dependency_file(self.run_base_dir, run_name)

    def on_run_changed(self):
        """When combo box selection changes, rebuild tree with new run data."""
        self._activate_selected_run_view(self.combo.currentText(), invalidate_snapshot=True)

    def _init_top_panel_background(self):
        """Apply XMETA background overrides to container widgets when configured."""
        try:
            bg_color = self._get_xmeta_background_color()

            if bg_color:
                theme = self.theme_manager.get_theme()

                if self.centralWidget() is not None:
                    self.centralWidget().setStyleSheet(f"background-color: {bg_color};")

                self.top_panel.setStyleSheet(f"#topPanel {{ background-color: {bg_color}; border: none; }}")
                if self.top_panel.graphicsEffect() is not None:
                    self.top_panel.setGraphicsEffect(None)

                self.menu_bar.setStyleSheet(f"""
                    QMenuBar {{
                        background-color: {bg_color};
                        border: none;
                        padding: 4px 8px;
                        font-size: 13px;
                        font-weight: bold;
                    }}
                    QMenuBar::item {{
                        background-color: transparent;
                        padding: 6px 14px;
                        border-radius: 4px;
                        color: #333333;
                    }}
                    QMenuBar::item:selected {{
                        background-color: #e3f2fd;
                        color: #1976d2;
                    }}
                    QMenuBar::item:pressed {{
                        background-color: #bbdefb;
                    }}
                    QMenu {{
                        background-color: #ffffff;
                        border: 1px solid #e0e0e0;
                        border-radius: 6px;
                        padding: 4px 0px;
                    }}
                    QMenu::item {{
                        padding: 8px 24px;
                        color: #333333;
                    }}
                    QMenu::item:selected {{
                        background-color: #e3f2fd;
                        color: #1976d2;
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background: #e0e0e0;
                        margin: 4px 12px;
                    }}
                """)

                if hasattr(self, 'tab_bar'):
                    self.tab_bar.setStyleSheet(f"""
                        #tabBar {{
                            background-color: {bg_color};
                            border: none;
                        }}
                    """)

                if hasattr(self, 'tab_widget'):
                    tab_widget_bg = QColor(bg_color).lighter(108).name()
                    self.tab_widget.setStyleSheet(f"""
                        #tabWidget {{
                            background-color: {tab_widget_bg};
                            border: none;
                            border-top-left-radius: 8px;
                            border-top-right-radius: 8px;
                        }}
                    """)

                if hasattr(self, 'tree'):
                    self.tree.setStyleSheet(f"""
                        QTreeView {{
                            background: rgba(255, 255, 255, 0.9);
                            border: none;
                            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                            font-size: 10pt;
                            border-radius: 10px;
                            padding: 6px 4px 4px 4px;
                        }}
                        QTreeView::item {{
                            height: 17px;
                            padding: 5px 6px;
                            border: none;
                        }}
                        QTreeView:focus {{
                            outline: none;
                        }}
                        QHeaderView::section {{
                            background: rgba(250,250,250,0.95);
                            padding: 7px 12px;
                            border: none;
                            border-bottom: 1px solid rgba(148, 163, 184, 0.35);
                            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
                            font-size: 10pt;
                            font-weight: 600;
                            color: {theme['text_color']};
                        }}
                        QTreeView::item:hover {{
                            background: transparent;
                        }}
                        QTreeView::item:selected {{
                            background: transparent;
                            color: #000000 !important;
                            outline: none;
                        }}
                        QTreeView::branch {{
                            background: transparent;
                            border: none;
                        }}
                        QTreeView::branch:has-siblings:!adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:has-siblings:adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                            background: transparent;
                        }}
                        QTreeView::branch:has-children:!has-siblings:closed {{
                            background: transparent;
                            image: none;
                        }}
                        QTreeView::branch:has-children:!has-siblings:open {{
                            background: transparent;
                            image: none;
                        }}
                        QTreeView::branch:has-children:has-siblings:closed {{
                            image: none;
                        }}
                        QTreeView::branch:has-children:has-siblings:open {{
                            image: none;
                        }}
                        QTreeView::branch:closed:has-children {{
                            border-image: none;
                        }}
                        QTreeView::branch:open:has-children {{
                            border-image: none;
                        }}
                        QTreeView::branch:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-siblings:!adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-siblings:adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:!has-children:!has-siblings:adjoins-item:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:has-children:!has-siblings:closed:selected,
                        QTreeView::branch:has-children:!has-siblings:open:selected {{
                            background: #C0C0BE !important;
                        }}
                        QTreeView::branch:hover {{
                            background: rgba(230,240,255,0.6) !important;
                        }}
                    """)

                if hasattr(self, '_status_bar'):
                    self._status_bar.setStyleSheet(f"""
                        StatusBar {{
                            background-color: {bg_color};
                            border-top: none;
                        }}
                        QLabel {{
                            color: {theme['text_color']};
                            font-size: 12px;
                        }}
                    """)

                logger.info(f"Applied XMETA background overrides: {bg_color}")
            else:
                self.top_panel.setStyleSheet(f"""
                    QWidget {{
                        background: {self._default_top_panel_bg};
                        border-radius: 0px;
                    }}
                """)
                self.menu_bar.setStyleSheet(self._default_menu_bar_style)
        except Exception as e:
            logger.warning(f"Failed to get XMETA_BACKGROUND: {e}")



    def get_target_status(self, run_name: str, target_name: str) -> str:
        """Get status of a target by checking status files in run_dir/status/.

        Args:
            run_name: Name of the run directory.
            target_name: Name of the target to check.

        Returns:
            Status string (finish, running, failed, skip, scheduled, pending, or empty).
        """
        return run_repository.get_target_status(
            self.run_base_dir,
            run_name,
            target_name,
            getattr(self, "_status_cache", None),
        )

    def _build_status_cache(self, run_name):
        """Build a cache of all target statuses for a run (batch I/O optimization)"""
        self._status_cache = run_repository.build_status_cache(self.run_base_dir, run_name)

    def get_target_times(self, run_name: str, target_name: str) -> tuple:
        """Get start and end time from cache.

        Args:
            run_name: Name of the run directory.
            target_name: Name of the target.

        Returns:
            Tuple of (start_time, end_time) as strings, or ("", "") if not found.
        """
        return run_repository.get_target_times(
            run_name,
            target_name,
            getattr(self, "_status_cache", None),
        )

    def _reset_main_tree_model(self):
        """Reset the main target tree model with standard headers and widths."""
        tree_rows.reset_main_tree_model(self.model, self.set_column_widths)

    def _build_target_row_items(self, level_text, target_name: str, status_value: str = None, run_name: str = None) -> list:
        """Build one standard main-tree row for a target."""
        current_run = run_name if run_name is not None else self.combo.currentText()
        row_status = self.get_target_status(current_run, target_name) if status_value is None else status_value
        tune_files = self.get_tune_files(self.combo_sel, target_name)
        start_time, end_time = self.get_target_times(current_run, target_name)
        queue, cores, memory = self.get_bsub_params(self.combo_sel, target_name)
        return tree_rows.build_target_row_items(
            level_text,
            target_name,
            row_status,
            tune_files,
            start_time,
            end_time,
            queue,
            cores,
            memory,
            STATUS_COLORS,
        )

    def _append_target_groups_to_model(self, level_groups, run_name: str = None, status_value: str = None) -> int:
        """Append grouped targets to the model using the standard main-tree structure."""
        appended_count = 0
        for level, targets in level_groups:
            if not targets:
                continue

            parent_row = self._build_target_row_items(str(level), targets[0], status_value=status_value, run_name=run_name)
            self.model.appendRow(parent_row)
            appended_count += 1

            parent_level_item = parent_row[0]
            for child_target in targets[1:]:
                child_row = self._build_target_row_items("", child_target, status_value=status_value, run_name=run_name)
                parent_level_item.appendRow(child_row)
                appended_count += 1
        return appended_count

    def _build_current_view_restore_plan(self, scroll_value: int) -> dict:
        """Describe the active filtered/tree mode so it can be replayed after rebuild."""
        header_filter_text = self.header.get_filter_text() if hasattr(self, 'header') else ""
        tab_label_text = self.tab_label.text() if hasattr(self, 'tab_label') else ""
        return view_restore.build_restore_plan(tab_label_text, header_filter_text, scroll_value)

    def _restore_view_from_plan(self, restore_plan: dict) -> str:
        """Replay a previously captured filtered/tree mode."""
        show_close_button = None
        if hasattr(self, 'tab_close_btn'):
            show_close_button = self.tab_close_btn.show

        return view_restore.apply_restore_plan(
            restore_plan,
            self.get_retrace_target,
            lambda targets_to_show: self.filter_tree_by_targets(set(targets_to_show)),
            self._apply_status_filter,
            self.filter_tree,
            self.tree.verticalScrollBar().setValue,
            show_close_button,
        )

    def _apply_tab_state(self, tab_state: dict) -> None:
        """Apply a tab label/button presentation state."""
        if hasattr(self, 'tab_label'):
            self.tab_label.setText(tab_state.get("text", ""))
            self.tab_label.setStyleSheet(tab_state.get("style", ""))
        if hasattr(self, 'tab_close_btn'):
            if tab_state.get("show_close_button"):
                self.tab_close_btn.show()
            else:
                self.tab_close_btn.hide()

    def _set_main_run_tab_state(self) -> None:
        """Apply the default tab presentation for the normal single-run view."""
        self._apply_tab_state(view_tabs.get_main_run_tab_state())

    def _set_filtered_main_view_tab_state(self) -> None:
        """Reset the in-place filtered tab back to the Main View appearance."""
        self._apply_tab_state(view_tabs.get_filtered_main_tab_state())

    def _set_all_status_tab_state(self) -> None:
        """Apply the tab presentation for the all-status overview."""
        self._apply_tab_state(view_tabs.get_all_status_tab_state())

    def _populate_all_status_overview(self, overview_rows) -> None:
        """Populate the tree model with the four-column all-status overview."""
        self.tree.setUpdatesEnabled(False)
        run_views.reset_all_status_model(self.model)
        for row in overview_rows:
            self.model.appendRow(run_views.build_all_status_row_items(row, STATUS_COLORS))
        self.tree.setUpdatesEnabled(True)

    def _activate_selected_run_view(self, current_run: str, invalidate_snapshot: bool = True) -> None:
        """Switch from overview/other run states back to the selected single-run view."""
        run_state = run_views.build_run_selection_state(current_run, self.run_base_dir)
        if not run_state:
            return

        if invalidate_snapshot:
            self._invalidate_main_view_snapshot()

        self.is_all_status_view = False
        self.combo_sel = run_state["combo_sel"]
        logger.info(f"Run changed to: {self.combo_sel}")

        self._set_main_run_tab_state()
        self._build_status_cache(run_state["run_name"])
        self.model.clear()
        self.populate_data()

        if hasattr(self, 'status_watcher'):
            self.setup_status_watcher()

        self.update_status_bar()

    def populate_data(self, force_rebuild=False):
        # Optimization: If model is already populated, just refresh status in-place
        # unless caller explicitly asks for a full rebuild.
        if self.model.rowCount() > 0 and not force_rebuild:
            current_run = self.combo.currentText()
            if not current_run: return

            self.tree.setUpdatesEnabled(False)

            def update_row(row_index, parent_item=None):
                row_items = tree_rows.get_row_items(self.model, row_index, parent_item)
                target_item = row_items[1] if len(row_items) > 1 else None
                target_name = target_item.text() if target_item else ""
                if not target_name:
                    return

                status = self.get_target_status(current_run, target_name)
                tree_rows.update_target_row_items(
                    row_items,
                    status,
                    row_items[4].text() if len(row_items) > 4 and row_items[4] else "",
                    row_items[5].text() if len(row_items) > 5 and row_items[5] else "",
                    STATUS_COLORS,
                )
            
            # Iterate Top Level
            for r in range(self.model.rowCount()):
                update_row(r)
                parent_item = self.model.item(r, 0)
                if parent_item and parent_item.hasChildren():
                    for child_r in range(parent_item.rowCount()):
                        update_row(child_r, parent_item)

            self.tree.setUpdatesEnabled(True)
            return

        # Save current scroll position
        current_scroll = self.tree.verticalScrollBar().value()

        self.tree.setUpdatesEnabled(False)
        self._reset_main_tree_model()
        
        # Get current run name
        current_run = self.combo.currentText()
        if not current_run:
            return
        
        # Parse dependency file to get targets and levels
        targets_by_level = self.parse_dependency_file(current_run)
        self.cached_targets_by_level = targets_by_level # Cache for search
        
        if not targets_by_level:
            logger.warning(f"No targets found for {current_run}")
            return

        # Populate tree with real status
        self._append_target_groups_to_model(
            tree_structure.get_level_target_groups(targets_by_level),
            run_name=current_run,
        )
        
        restore_plan = self._build_current_view_restore_plan(current_scroll)
        if restore_plan.get("mode") == "main":
            # Expand all only if no filter
            self.tree.expandAll()
            # Restore scroll position
            self.tree.verticalScrollBar().setValue(current_scroll)
        else:
            self._restore_view_from_plan(restore_plan)
            
        self.tree.setUpdatesEnabled(True)

    def setup_status_watcher(self):
        """Setup file system watcher for the current run's status directory."""
        if not self.combo_sel:
            return
        
        status_dir = os.path.join(self.combo_sel, "status")
        
        # Remove old watched directories
        if self.watched_status_dirs:
            old_dirs = list(self.watched_status_dirs)
            self.status_watcher.removePaths(old_dirs)
            self.watched_status_dirs.clear()
        
        # Add new status directory if it exists
        if os.path.exists(status_dir):
            self.status_watcher.addPath(status_dir)
            self.watched_status_dirs.add(status_dir)
            logger.debug(f"Now watching status directory: {status_dir}")
    
    def on_status_directory_changed(self, path):
        """Called when the status directory contents change (file added/removed)."""
        logger.debug(f"Status directory changed: {path}")

        # Use debounce timer to batch rapid changes
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(DEBOUNCE_DELAY_MS)

    def on_status_file_changed(self, path):
        """Called when a watched file is modified."""
        logger.debug(f"Status file changed: {path}")

        # Use debounce timer to batch rapid changes
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(DEBOUNCE_DELAY_MS)

    def change_run(self):
        """Refresh status timer callback - updates status/time for all visible targets"""
        if not hasattr(self, 'model') or not self.model or not self.combo_sel:
            return

        # Skip updates when in All Status view
        if self.is_all_status_view:
            return

        # Get current run name
        current_run = os.path.basename(self.combo_sel)

        # Rebuild status cache for efficient batch lookup
        self._build_status_cache(current_run)

        def update_row_status(row_idx, parent_item=None):
            """Update status and colors for a single row"""
            row_items = tree_rows.get_row_items(self.model, row_idx, parent_item)
            target_item = row_items[1] if len(row_items) > 1 else None
            if not target_item:
                return

            target = target_item.text()
            if not target:
                return

            # Get status and time from cache
            status = self.get_target_status(current_run, target)
            start_time, end_time = self.get_target_times(current_run, target)
            tree_rows.update_target_row_items(row_items, status, start_time, end_time, self.colors)

        # Update all top-level rows and their children
        for i in range(self.model.rowCount()):
            level_item = self.model.item(i, 0)
            if not level_item:
                continue

            # Update top-level row
            update_row_status(i, None)

            # Update children if any
            if level_item.hasChildren():
                for child_row in range(level_item.rowCount()):
                    update_row_status(child_row, level_item)

        # Update status bar with latest stats
        self.update_status_bar()

    def get_start_end_time(self, tgt_track_file: str) -> tuple:
        """Get start and end time from target tracker file.

        Args:
            tgt_track_file: Base path for tracker files (without .start/.finished suffix).

        Returns:
            Tuple of (start_time, end_time) as formatted strings.
        """
        return run_repository.get_start_end_time(tgt_track_file)

    # ========== File Viewers ==========

    def _open_file_with_editor(self, filepath: str, editor: str = 'gvim', use_popen: bool = False) -> None:
        """Open file with editor in background thread.

        Args:
            filepath: Path to the file to open.
            editor: Editor command to use (default: gvim).
            use_popen: If True, use Popen for background execution; otherwise use run with timeout.
        """
        self._executor.submit(file_actions.open_file_with_editor, filepath, editor, use_popen)

    def handle_csh(self):
        """Open shell file for selected target (runs in background thread)"""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        shell_file = file_actions.get_shell_file(self.combo_sel, target)

        if shell_file:
            self._open_file_with_editor(shell_file)
        else:
            logger.warning(f"Shell file not found for target: {target}")

    def handle_log(self):
        """Open log file for selected target (runs in background thread)"""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        log_file = file_actions.get_log_file(self.combo_sel, target)

        if log_file:
            self._open_file_with_editor(log_file, use_popen=True)
        else:
            logger.warning(f"Log file not found for target: {target}")

    def handle_cmd(self):
        """Open command file for selected target (runs in background thread)"""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        cmd_file = file_actions.get_cmd_file(self.combo_sel, target)

        if cmd_file:
            self._open_file_with_editor(cmd_file)
        else:
            logger.warning(f"Command file not found for target: {target}")

    # ========== Tune File Management ==========

    def get_tune_files(self, run_dir: str, target_name: str) -> list:
        """Get all tune files for a target.

        Tune file naming: {run_dir}/tune/{target}/{target}.{suffix}.tcl

        Args:
            run_dir: Path to the run directory.
            target_name: Name of the target.

        Returns:
            List of (suffix, full_path) tuples, sorted by suffix.
        """
        return run_repository.get_tune_files(
            run_dir,
            target_name,
            self._tune_files_cache,
        )

    def get_tune_display(self, run_dir, target_name):
        """Get tune display string for tree view.
        Returns comma-separated suffixes or empty string
        """
        tune_files = self.get_tune_files(run_dir, target_name)
        if not tune_files:
            return ""
        return ", ".join([suffix for suffix, _ in tune_files])

    def get_tune_candidates_from_cmd(self, run_dir: str, target_name: str) -> list:
        """Parse tunesource entries from cmds/<target>.cmd.

        Args:
            run_dir: Path to run directory.
            target_name: Name of selected target.

        Returns:
            List of (display_name, full_path) tuples for tune files that can be created.
        """
        return run_repository.get_tune_candidates_from_cmd(run_dir, target_name)

    def _refresh_tune_cells_for_target(self, target_name: str) -> None:
        """Refresh tune column text and UserRole data for one target in tree model."""
        if not self.combo_sel or not hasattr(self, "model") or self.model is None:
            return

        tune_files = self.get_tune_files(self.combo_sel, target_name)
        tune_display = ", ".join([suffix for suffix, _ in tune_files]) if tune_files else ""

        def update_cells(target_item, tune_item):
            if not target_item or not tune_item:
                return
            if target_item.text() != target_name:
                return
            tune_item.setText(tune_display)
            tune_item.setData(tune_files, Qt.UserRole)

        for row_idx in range(self.model.rowCount()):
            update_cells(self.model.item(row_idx, 1), self.model.item(row_idx, 3))
            level_item = self.model.item(row_idx, 0)
            if not level_item or not level_item.hasChildren():
                continue
            for child_row in range(level_item.rowCount()):
                update_cells(level_item.child(child_row, 1), level_item.child(child_row, 3))

    def create_tune(self):
        """Create a tune file from tunesource entries in cmds/<target>.cmd and open it."""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not self.combo_sel or len(selected_targets) != 1:
            QMessageBox.information(self, "Info", "Select exactly one target to create tune.")
            return

        target = selected_targets[0]
        candidates = self.get_tune_candidates_from_cmd(self.combo_sel, target)
        if not candidates:
            QMessageBox.information(
                self,
                "Info",
                f"No tunesource entries found in cmds/{target}.cmd",
            )
            return

        dialog = SelectTuneDialog(
            target,
            candidates,
            self,
            title_prefix="Create Tune",
            instruction_text="Select a tune file name to create:",
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        selected_tune = dialog.get_selected_tune()
        if not selected_tune:
            return

        tune_file = selected_tune[1]
        try:
            created = tune_actions.ensure_tune_file(tune_file)
            if created:
                self.show_notification(
                    "Tune",
                    f"Created tune file: {os.path.basename(tune_file)}",
                    "success",
                )
            else:
                self.show_notification(
                    "Tune",
                    f"Tune file already exists: {os.path.basename(tune_file)}",
                    "info",
                )

            self._invalidate_tune_cache(self.combo_sel, target)
            self._refresh_tune_cells_for_target(target)
            self._open_tune_file(tune_file)
        except Exception as e:
            logger.error(f"Failed to create tune file {tune_file}: {e}")
            QMessageBox.warning(
                self,
                "Warning",
                f"Failed to create tune file:\n{tune_file}\n\n{e}",
            )

    # ========== BSUB Parameter Methods ==========

    def get_bsub_params(self, run_dir: str, target_name: str) -> tuple:
        """Parse bsub parameters from {run_dir}/make_targets/{target}.csh.

        Args:
            run_dir: Path to the run directory.
            target_name: Name of the target.

        Returns:
            Tuple of (queue, cores, memory), each can be 'N/A' if not found.
        """
        return run_repository.get_bsub_params(
            run_dir,
            target_name,
            self._bsub_params_cache,
        )

    def save_bsub_param(self, run_dir, target_name, param_type, new_value):
        """Save a single bsub parameter to the csh file.
        Args:
            run_dir: Run directory path
            target_name: Target name
            param_type: 'queue', 'cores', or 'memory'
            new_value: New value to set
        Returns: True if successful, False otherwise
        """
        if run_repository.save_bsub_param(run_dir, target_name, param_type, new_value):
            self._invalidate_bsub_cache(run_dir, target_name)
            logger.info(f"Updated {param_type} to {new_value} for {target_name}")
            return True
        return False

    def handle_tune(self):
        """Open tune file for selected target with gvim"""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            return

        target = selected_targets[0]
        tune_files = self.get_tune_files(self.combo_sel, target)

        if not tune_files:
            QMessageBox.information(self, "Info", f"No tune file found for: {target}")
            return

        if len(tune_files) == 1:
            # Only one tune file, open directly
            tune_file = tune_files[0][1]
            self._open_tune_file(tune_file)
        else:
            # Multiple tune files, show selection dialog
            dialog = SelectTuneDialog(target, tune_files, self)
            if dialog.exec_() == QDialog.Accepted:
                selected = dialog.get_selected_tune()
                if selected:
                    self._open_tune_file(selected[1])

    def _open_tune_file(self, tune_file):
        """Open a tune file with gvim (runs in background thread)"""
        self._open_file_with_editor(tune_file)

    def copy_tune_to_runs(self):
        """Copy tune file to selected runs"""
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            return

        target = selected_targets[0]
        tune_files = self.get_tune_files(self.combo_sel, target)

        if not tune_files:
            QMessageBox.information(self, "Info", f"No tune file found for: {target}")
            return

        # Get available runs
        available_runs = run_repository.list_available_runs(
            self.run_base_dir if hasattr(self, "run_base_dir") else ""
        )

        if not available_runs:
            QMessageBox.warning(self, "Warning", "No other runs available")
            return

        current_run = os.path.basename(self.combo_sel) if os.path.isabs(self.combo_sel) else self.combo_sel

        # Show combined dialog for tune selection and run selection
        dialog = CopyTuneSelectDialog(current_run, target, tune_files, available_runs, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_runs = dialog.get_selected_runs()
            selected_tunes = dialog.get_selected_tune_suffixes()

            if not selected_runs or not selected_tunes:
                return

            result = tune_actions.copy_tune_files_to_runs(
                selected_tunes,
                selected_runs,
                self.run_base_dir if hasattr(self, "run_base_dir") else "",
                target,
            )
            total_success = result["total_success"]

            for run in selected_runs:
                run_dir = os.path.join(self.run_base_dir, run) if hasattr(self, "run_base_dir") else run
                self._invalidate_tune_cache(run_dir, target)

            # Build summary message
            tune_names = ", ".join([suffix for suffix, _ in selected_tunes])
            QMessageBox.information(self, "Copy Complete",
                f"Copied {len(selected_tunes)} tune file(s) ({tune_names})\nto {total_success}/{len(selected_runs)} runs")

    def open_terminal(self):
        """Open terminal in current run directory (runs in background thread)"""
        if not self.combo_sel:
            return

        self._executor.submit(file_actions.open_terminal, self.combo_sel)

    # ========== Context Menu Helpers ==========

    def _build_execute_menu(self, menu: QMenu) -> None:
        """Build the Execute submenu."""
        exec_menu = menu.addMenu("▶ Execute")

        run_all_action = exec_menu.addAction("▶ Run All")
        run_all_action.setToolTip("Run all targets (Ctrl+Shift+Enter)")
        run_all_action.triggered.connect(lambda: self.start('XMeta_run all'))

        run_action = exec_menu.addAction("▶ Run Selected")
        run_action.setToolTip("Run selected targets (Ctrl+Enter)")
        run_action.triggered.connect(lambda: self.start('XMeta_run'))

        stop_action = exec_menu.addAction("■ Stop")
        stop_action.setToolTip("Stop selected targets")
        stop_action.triggered.connect(lambda: self.start('XMeta_stop'))

        exec_menu.addSeparator()

        skip_action = exec_menu.addAction("○ Skip")
        skip_action.setToolTip("Skip selected targets")
        skip_action.triggered.connect(lambda: self.start('XMeta_skip'))

        unskip_action = exec_menu.addAction("● Unskip")
        unskip_action.setToolTip("Unskip selected targets")
        unskip_action.triggered.connect(lambda: self.start('XMeta_unskip'))

        invalid_action = exec_menu.addAction("✕ Invalid")
        invalid_action.setToolTip("Mark selected targets as invalid")
        invalid_action.triggered.connect(lambda: self.start('XMeta_invalid'))

    def _build_file_menu(self, menu: QMenu) -> None:
        """Build the Files submenu."""
        file_menu = menu.addMenu("📁 Files")

        terminal_action = file_menu.addAction("⌘ Terminal")
        terminal_action.setToolTip("Open terminal in run directory")
        terminal_action.triggered.connect(self.open_terminal)

        csh_action = file_menu.addAction("📄 csh")
        csh_action.setToolTip("Open shell file for selected target")
        csh_action.triggered.connect(self.handle_csh)

        log_action = file_menu.addAction("📋 Log")
        log_action.setToolTip("Open log file for selected target")
        log_action.triggered.connect(self.handle_log)

        cmd_action = file_menu.addAction("⚡ cmd")
        cmd_action.setToolTip("Open command file for selected target")
        cmd_action.triggered.connect(self.handle_cmd)

    def _build_tune_menu(self, menu: QMenu, selected_targets: list) -> None:
        """Build the Tune submenu."""
        tune_menu = menu.addMenu("🎵 Tune")
        single_target = len(selected_targets) == 1

        # Check if selected target has tune file
        if single_target and self.combo_sel:
            tune_display = self.get_tune_display(self.combo_sel, selected_targets[0])
            if tune_display:
                tune_action = tune_menu.addAction(f"📝 Open Tune ({tune_display})")
            else:
                tune_action = tune_menu.addAction("📝 Open Tune")
        else:
            tune_action = tune_menu.addAction("📝 Open Tune")
        tune_action.setToolTip("Open tune file for selected target")
        tune_action.triggered.connect(self.handle_tune)

        create_tune_action = tune_menu.addAction("➕ Create Tune")
        create_tune_action.setToolTip("Create tune file from cmds/<target>.cmd tunesource entries")
        create_tune_action.triggered.connect(self.create_tune)
        create_tune_action.setEnabled(single_target)

        copy_tune_action = tune_menu.addAction("📋 Copy Tune To...")
        copy_tune_action.setToolTip("Copy tune file to other runs")
        copy_tune_action.triggered.connect(self.copy_tune_to_runs)

    def _build_params_menu(self, menu: QMenu) -> None:
        """Build the Params submenu."""
        params_menu = menu.addMenu("⚙ Params")

        user_params_action = params_menu.addAction("📝 User Params")
        user_params_action.setToolTip("Edit user.params for current run")
        user_params_action.triggered.connect(self.open_user_params)

        tile_params_action = params_menu.addAction("📋 Tile Params")
        tile_params_action.setToolTip("View tile.params for current run")
        tile_params_action.triggered.connect(self.open_tile_params)

    def _build_trace_menu(self, menu: QMenu) -> None:
        """Build the Trace submenu."""
        trace_menu = menu.addMenu("🔗 Trace")

        trace_up_action = trace_menu.addAction("⬆ Trace Up (Ctrl+U)")
        trace_up_action.setToolTip("Trace upstream dependencies")
        trace_up_action.triggered.connect(lambda: self.retrace_tab('in'))

        trace_down_action = trace_menu.addAction("⬇ Trace Down (Ctrl+D)")
        trace_down_action.setToolTip("Trace downstream dependencies")
        trace_down_action.triggered.connect(lambda: self.retrace_tab('out'))

        trace_menu.addSeparator()

        graph_action = trace_menu.addAction("📊 Dependency Graph (Ctrl+G)")
        graph_action.setToolTip("Show full dependency graph")
        graph_action.triggered.connect(self.show_dependency_graph)

    def _build_copy_menu(self, menu: QMenu, single_target: bool, selected_targets: list) -> None:
        """Build the Copy submenu."""
        copy_menu = menu.addMenu("📋 Copy")

        copy_target_action = copy_menu.addAction("Copy Target Name (Ctrl+C)")
        copy_target_action.setToolTip("Copy selected target names to clipboard")
        copy_target_action.triggered.connect(self._copy_selected_target)

        if single_target and selected_targets:
            copy_path_action = copy_menu.addAction("Copy Run Path")
            copy_path_action.setToolTip("Copy the full path of the current run")
            copy_path_action.triggered.connect(lambda: self._copy_run_path())

    # ========== Right-click Menu ==========

    def show_context_menu(self, position):
        """Show context menu on right-click with icons and grouping."""
        index = self.tree.indexAt(position)
        if not index.isValid():
            return

        # Ensure the item is selected
        selection_model = self.tree.selectionModel()
        if not selection_model.isSelected(index):
            selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

        menu = QMenu()
        menu.setStyleSheet(STYLES['menu'])

        # Get selected targets for context
        selected_targets = self.get_selected_targets()
        single_target = len(selected_targets) == 1

        # Build menu sections
        self._build_execute_menu(menu)
        menu.addSeparator()
        self._build_file_menu(menu)
        menu.addSeparator()
        self._build_tune_menu(menu, selected_targets)
        menu.addSeparator()
        self._build_params_menu(menu)
        menu.addSeparator()
        self._build_trace_menu(menu)
        menu.addSeparator()
        self._build_copy_menu(menu, single_target, selected_targets)

        # Execute menu
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def _copy_run_path(self):
        """Copy the current run path to clipboard"""
        if self.combo_sel:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.combo_sel)
            self.show_notification("Copied", f"Copied path: {self.combo_sel}", "success")

    # ========== Trace Functionality ==========
    
    def get_retrace_target(self, target, inout):
        """Parse .target_dependency.csh to find related targets (upstream/downstream)"""
        return run_repository.get_retrace_targets(self.combo_sel, target, inout)

    def filter_tree_by_targets(self, targets_to_show):
        """Filter tree to show only specific targets"""
        logger.debug(f"Filtering tree for {len(targets_to_show)} targets")
        view_state.filter_tree_by_targets(self.tree, self.model, targets_to_show)

    def retrace_tab(self, inout):
        """Execute trace and filter view (In-Place)"""
        # Exit search mode if active and get selected targets
        selected_targets = self._exit_search_mode_and_get_targets()
        if not selected_targets or not self.combo_sel:
            logger.warning("No target selected for trace")
            return
        
        tar_sel = selected_targets[0]
        logger.info(f"Trace {inout} for target: {tar_sel}")
        
        # 1. Get related targets
        related_targets = self.get_retrace_target(tar_sel, inout)
        
        # Add the selected target itself to the list so it's visible
        if tar_sel not in related_targets:
            if inout == 'in':
                related_targets.append(tar_sel) # Add to end
            else:
                related_targets.insert(0, tar_sel) # Add to start
        
        if not related_targets:
            logger.info("No dependencies found.")
            return

        # 2. Filter the tree
        self.filter_tree_by_targets(set(related_targets))
        
        # 3. Update UI to show we are in Trace mode
        direction = "Up" if inout == 'in' else "Down"
        label_text = f"Trace {direction}: {tar_sel}"
        self._apply_tab_state(view_tabs.get_trace_tab_state(label_text))
        
        # 4. Ensure the selected target is visible and selected
        # (Optional: scroll to it)




    def set_column_widths(self):
        """Set column widths to user preferences"""
        header = self.tree.header()
        default_widths = self._get_main_view_default_column_widths()
        header_min_widths = self._get_header_min_widths()
        if header is not None:
            header.setStretchLastSection(False)
            for col in range(self.model.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Interactive)
            if self.model.columnCount() > 1:
                header.setSectionResizeMode(1, QHeaderView.Stretch)

        for column, width in default_widths.items():
            min_width = header_min_widths.get(column, 0)
            self.tree.setColumnWidth(column, max(width, min_width))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
