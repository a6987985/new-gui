import sys
import os
import re
import subprocess
import time
import warnings
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings("ignore", category=DeprecationWarning) # Suppress sipPyTypeDict warning

# Add parent directory to path to import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========== Logging Setup ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ========== Pre-compiled Regex Patterns ==========
RE_LEVEL_LINE = re.compile(r'^set\s+LEVEL_(\d+)\s*=\s*"([^"]*)"')
RE_ACTIVE_TARGETS = re.compile(r'set\s*ACTIVE_TARGETS\s*=\s*"([^"]*)"')
RE_TARGET_LEVEL = re.compile(r'set\s*(TARGET_LEVEL_\w+)\s*=\s*(.*)')
RE_QUOTED_STRING = re.compile(r"^['\"](.*)['\"]\s*$")
RE_DEPENDENCY_OUT = re.compile(r'set\s+DEPENDENCY_OUT_(\w+)\s*=\s*"([^"]*)"')
RE_ALL_RELATED = re.compile(r'set\s+ALL_RELATED_(\w+)\s*=\s*"([^"]*)"')

# ========== Status Colors Constant ==========
STATUS_COLORS = {
    "finish": "#98FB98",    # PaleGreen
    "skip": "#FFDAB9",      # PeachPuff
    "running": "#FFFF00",   # Yellow
    "failed": "#FF9999",    # Light Red
    "scheduled": "#4A90D9", # Deeper Blue
    "pending": "#87CEEB",   # SkyBlue
    "": "#87CEEB"           # Default/No status
}

from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, Qt, QTimer, QObject, QEvent, QModelIndex, QRect, pyqtSignal, QItemSelectionModel, QPointF, QLineF, QFileSystemWatcher
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton, QCompleter,
                             QTreeView, QLineEdit, QHeaderView, QStyleFactory,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                             QSizePolicy, QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QAbstractItemView, QStyleOptionComboBox,
                             QMenuBar, QAction, QDialog, QGraphicsScene, QGraphicsView,
                             QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
                             QGraphicsPolygonItem, QFileDialog, QCheckBox, QScrollArea,
                             QGroupBox, QMessageBox, QFrame)
from PyQt5.QtGui import (QStandardItemModel, QStandardItem, QColor, QBrush, QFont, 
                         QFontDatabase, QTextCursor, QPen, QPainter, QPolygonF)
import math



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


class TuneComboBoxDelegate(QStyledItemDelegate):
    """ComboBox delegate for tune column - displays tune files as dropdown"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree_view = parent
        self._popup_combo = None

    def createEditor(self, parent, option, index):
        """Create ComboBox editor"""
        combo = QComboBox(parent)
        combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 5px;
                background: white;
            }
            QComboBox:hover {
                border: 1px solid #4A90D9;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        combo.setAutoFillBackground(True)
        return combo

    def setEditorData(self, editor, index):
        """Populate ComboBox with tune file options"""
        editor.clear()
        # Get tune files list from item's UserRole
        tune_files = index.data(Qt.UserRole)
        if tune_files:
            for suffix, filepath in tune_files:
                editor.addItem(suffix, filepath)
        else:
            editor.addItem("(no tune)")

    def setModelData(self, editor, model, index):
        """Save selected tune file (not really needed for display-only)"""
        pass

    def updateEditorGeometry(self, editor, option, index):
        """Position the editor"""
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        """Custom paint to show ComboBox-like appearance"""
        # 1. Draw background from model (Status Colors)
        bg_brush = index.data(Qt.BackgroundRole)
        if bg_brush:
            painter.save()
            if isinstance(bg_brush, QBrush):
                painter.fillRect(option.rect, bg_brush)
            elif isinstance(bg_brush, QColor):
                painter.fillRect(option.rect, bg_brush)
            painter.restore()

        # 2. Draw Hover/Selection Background
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(0xC0, 0xC0, 0xBE))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor(230, 240, 255, 150))
        painter.restore()

        # 3. Get tune files and text
        tune_files = index.data(Qt.UserRole)
        text = index.data(Qt.DisplayRole) or ""

        # 4. Draw text
        painter.save()
        text_color = index.data(Qt.ForegroundRole)
        if text_color:
            painter.setPen(QPen(text_color.color() if isinstance(text_color, QBrush) else text_color))
        else:
            painter.setPen(QPen(Qt.black))

        text_rect = option.rect.adjusted(5, 0, -20, 0)  # Leave space for arrow
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()

        # 5. Draw dropdown arrow indicator
        painter.save()
        arrow_x = option.rect.right() - 15
        arrow_y = option.rect.center().y()
        painter.setPen(QPen(QColor("#666"), 1))
        # Draw simple down arrow
        painter.drawLine(arrow_x - 4, arrow_y - 2, arrow_x, arrow_y + 2)
        painter.drawLine(arrow_x, arrow_y + 2, arrow_x + 4, arrow_y - 2)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Handle mouse double-click to show popup"""
        if event.type() == QEvent.MouseButtonDblClick:
            from PyQt5.QtWidgets import QMenu

            # Create menu for dropdown
            menu = QMenu(self.tree_view)
            menu.setStyleSheet("""
                QMenu {
                    background: white;
                    border: 1px solid #ccc;
                    padding: 0px;
                }
                QMenu::item {
                    padding: 5px 20px;
                    color: black;
                    border: none;
                }
                QMenu::item:selected {
                    background-color: #4A90D9;
                    color: white;
                }
            """)

            # Populate menu
            tune_files = index.data(Qt.UserRole)
            actions = []
            if tune_files:
                for suffix, filepath in tune_files:
                    action = menu.addAction(suffix)
                    action.setData(filepath)
                    actions.append(action)
            else:
                action = menu.addAction("(no tune)")
                action.setEnabled(False)

            # Get the visual rect of the item and show menu below it
            visual_rect = self.tree_view.visualRect(index)
            popup_pos = self.tree_view.viewport().mapToGlobal(visual_rect.bottomLeft())

            # Handle selection
            def on_triggered(action):
                filepath = action.data()
                if filepath:
                    import subprocess
                    try:
                        subprocess.Popen(['gvim', filepath])
                    except Exception as e:
                        pass

            menu.triggered.connect(on_triggered)
            menu.exec_(popup_pos)
            return True
        return super().editorEvent(event, model, option, index)


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
        # Only disable if currently editable (in search mode)
        if self.isEditable():
            self.setEditable(False)
        self.search_btn.show()

    def showPopup(self):
        # Reorder items: put current selection at the top
        current_idx = self.currentIndex()
        current_text = self.currentText()

        if current_idx > 0 and self.count() > 1:
            # Block signals to prevent triggering currentIndexChanged
            self.blockSignals(True)

            # Collect all items
            items = [self.itemText(i) for i in range(self.count())]

            # Remove current item and insert at beginning
            if current_text in items:
                items.remove(current_text)
                items.insert(0, current_text)

            # Clear and re-add items
            self.clear()
            self.addItems(items)

            # Set current index back to 0 (now the first item)
            self.setCurrentIndex(0)

            self.blockSignals(False)

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


class DependencyGraphDialog(QDialog):
    """Dialog for displaying dependency graph visualization."""
    
    def __init__(self, graph_data, status_colors, parent=None):
        """
        Args:
            graph_data: dict with 'nodes' (list of (name, status)) and 'edges' (list of (source, target))
            status_colors: dict mapping status to color hex codes
        """
        super().__init__(parent)
        self.setWindowTitle("Dependency Graph")
        self.resize(1100, 750)
        self.graph_data = graph_data
        self.status_colors = status_colors
        self.node_items = {}  # Store node positions for edge drawing
        
        # Setup UI
        self.setup_ui()
        
        # Draw the graph
        self.draw_graph()
    
    def setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Graphics View
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.view)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
            }
        """
        
        zoom_in_btn = QPushButton("Zoom In (+)")
        zoom_in_btn.setStyleSheet(btn_style)
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("Zoom Out (-)")
        zoom_out_btn.setStyleSheet(btn_style)
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        fit_btn = QPushButton("Fit View")
        fit_btn.setStyleSheet(btn_style)
        fit_btn.clicked.connect(self.fit_view)
        toolbar.addWidget(fit_btn)
        
        export_btn = QPushButton("Export PNG")
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(self.export_png)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        
        # Legend
        legend_label = QLabel("Legend: ")
        legend_label.setStyleSheet("font-weight: bold; color: #333;")
        toolbar.addWidget(legend_label)
        
        for status, color in [("finish", "#98FB98"), ("running", "#FFFF00"), 
                               ("failed", "#FF9999"), ("skip", "#FFDAB9"), ("waiting", "#87CEEB")]:
            legend_item = QLabel(f"  {status}  ")
            legend_item.setStyleSheet(f"background-color: {color}; border: 1px solid #999; border-radius: 3px; padding: 2px 6px;")
            toolbar.addWidget(legend_item)
        
        layout.addLayout(toolbar)
    
    def draw_graph(self):
        """Draw the dependency graph using hierarchical layout."""
        nodes = self.graph_data.get('nodes', [])
        edges = self.graph_data.get('edges', [])
        levels = self.graph_data.get('levels', {})  # level -> [targets]
        
        if not nodes:
            # No data, show message
            text = QGraphicsTextItem("No dependency data found")
            text.setFont(QFont("Arial", 14))
            self.scene.addItem(text)
            return
        
        # Calculate positions using level-based layout
        # Each level gets a row, nodes in each level are spread horizontally
        node_positions = {}
        
        # Vertical spacing between levels
        level_height = 100
        # Horizontal spacing between nodes
        node_width = 180
        
        y_offset = 50
        max_x = 0
        
        # Sort levels
        sorted_levels = sorted(levels.keys())
        
        for level in sorted_levels:
            level_targets = levels[level]
            num_nodes = len(level_targets)
            
            # Calculate starting x to center the level
            total_width = num_nodes * node_width
            start_x = -total_width / 2 + node_width / 2
            
            for i, target in enumerate(level_targets):
                x = start_x + i * node_width
                y = y_offset
                node_positions[target] = (x, y)
                max_x = max(max_x, abs(x) + node_width)
            
            y_offset += level_height
        
        # Draw edges first (so they appear behind nodes)
        for source, target in edges:
            if source in node_positions and target in node_positions:
                x1, y1 = node_positions[source]
                x2, y2 = node_positions[target]
                self.draw_arrow(x1, y1 + 20, x2, y2 - 20)
        
        # Draw nodes
        for node_name, status in nodes:
            if node_name not in node_positions:
                continue
            x, y = node_positions[node_name]
            self.draw_node(node_name, status, x, y)
        
        # Fit view after drawing
        self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
    
    def draw_node(self, name, status, x, y):
        """Draw a single node at the specified position."""
        # Node dimensions
        width = 150
        height = 40
        
        # Get color based on status
        color_hex = self.status_colors.get(status.lower(), "#87CEEB")
        color = QColor(color_hex)
        
        # Draw rounded rectangle for node
        rect = self.scene.addRect(x - width/2, y - height/2, width, height,
                                   QPen(QColor("#333333"), 2),
                                   QBrush(color))
        rect.setToolTip(f"Target: {name}\nStatus: {status or 'pending'}")
        
        # Add text label
        text = QGraphicsTextItem(name)
        text.setFont(QFont("Arial", 9, QFont.Bold))
        text.setDefaultTextColor(QColor("#000000"))
        
        # Center text in node
        text_rect = text.boundingRect()
        text.setPos(x - text_rect.width()/2, y - text_rect.height()/2)
        self.scene.addItem(text)
        
        # Store position
        self.node_items[name] = (x, y)
    
    def draw_arrow(self, x1, y1, x2, y2):
        """Draw an arrow from (x1,y1) to (x2,y2)."""
        # Draw line
        line = QGraphicsLineItem(x1, y1, x2, y2)
        line.setPen(QPen(QColor("#666666"), 1.5))
        self.scene.addItem(line)
        
        # Calculate arrow head
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10
        
        # Arrow head points
        p1 = QPointF(x2 - arrow_size * math.cos(angle - math.pi/6),
                     y2 - arrow_size * math.sin(angle - math.pi/6))
        p2 = QPointF(x2 - arrow_size * math.cos(angle + math.pi/6),
                     y2 - arrow_size * math.sin(angle + math.pi/6))
        p3 = QPointF(x2, y2)
        
        # Draw arrow head
        arrow_head = QPolygonF([p1, p2, p3])
        arrow_item = QGraphicsPolygonItem(arrow_head)
        arrow_item.setBrush(QBrush(QColor("#666666")))
        arrow_item.setPen(QPen(QColor("#666666"), 1))
        self.scene.addItem(arrow_item)
    
    def zoom_in(self):
        """Zoom in the view."""
        self.view.scale(1.2, 1.2)
    
    def zoom_out(self):
        """Zoom out the view."""
        self.view.scale(0.8, 0.8)
    
    def fit_view(self):
        """Fit the entire graph in the view."""
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def export_png(self):
        """Export the graph to a PNG file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Graph", "dependency_graph.png", "PNG Files (*.png)"
        )
        if file_path:
            # Create image from scene
            from PyQt5.QtGui import QImage
            rect = self.scene.itemsBoundingRect()
            image = QImage(int(rect.width()) + 100, int(rect.height()) + 100, QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            self.scene.render(painter)
            painter.end()
            
            image.save(file_path)
            logger.info(f"Graph exported to: {file_path}")


class CopyTuneDialog(QDialog):
    """Dialog for copying tune file to multiple runs."""
    def __init__(self, source_run, target_name, available_runs, parent=None):
        super().__init__(parent)
        self.source_run = source_run
        self.target_name = target_name
        self.available_runs = available_runs
        self.selected_runs = []
        self.checkboxes = {}

        self.setWindowTitle(f"Copy Tune: {target_name}")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Source info
        source_label = QLabel(f"Source: {self.source_run}")
        source_label.setStyleSheet("font-weight: bold; color: #4A90D9;")
        layout.addWidget(source_label)

        # Instructions
        instruction_label = QLabel("Select runs to copy tune file to:")
        layout.addWidget(instruction_label)

        # Create scrollable area for run list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add checkboxes for each run (exclude source run)
        for run in sorted(self.available_runs):
            if run != self.source_run:
                cb = QCheckBox(run)
                self.checkboxes[run] = cb
                scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Select/Deselect buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        layout.addLayout(btn_layout)

        # OK/Cancel buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.accept)
        copy_btn.setStyleSheet("background-color: #4A90D9; color: white;")
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(copy_btn)
        layout.addLayout(btn_box)

    def select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def get_selected_runs(self):
        return [run for run, cb in self.checkboxes.items() if cb.isChecked()]


class SelectTuneDialog(QDialog):
    """Dialog for selecting a tune file from multiple options."""
    def __init__(self, target_name, tune_files, parent=None):
        super().__init__(parent)
        self.target_name = target_name
        self.tune_files = tune_files  # List of (suffix, full_path)
        self.selected_tune = None

        self.setWindowTitle(f"Select Tune: {target_name}")
        self.setMinimumWidth(350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instruction_label = QLabel("Select a tune file:")
        layout.addWidget(instruction_label)

        # Create buttons for each tune file
        self.tune_buttons = {}
        for suffix, filepath in self.tune_files:
            btn = QPushButton(suffix)
            btn.setStyleSheet("text-align: left; padding: 8px;")
            btn.clicked.connect(lambda checked, s=suffix, f=filepath: self.select_tune(s, f))
            layout.addWidget(btn)
            self.tune_buttons[suffix] = btn

        # Cancel button
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def select_tune(self, suffix, filepath):
        self.selected_tune = (suffix, filepath)
        self.accept()

    def get_selected_tune(self):
        return self.selected_tune


class CopyTuneSelectDialog(QDialog):
    """Dialog for selecting tune files and copying to multiple runs."""
    def __init__(self, source_run, target_name, tune_files, available_runs, parent=None):
        super().__init__(parent)
        self.source_run = source_run
        self.target_name = target_name
        self.tune_files = tune_files  # List of (suffix, full_path)
        self.available_runs = available_runs
        self.selected_tune_suffixes = []  # Changed to list for multiple selection
        self.selected_runs = []

        self.setWindowTitle(f"Copy Tune: {target_name}")
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Source info
        source_label = QLabel(f"Source: {self.source_run}")
        source_label.setStyleSheet("font-weight: bold; color: #4A90D9;")
        layout.addWidget(source_label)

        # Tune file selection - changed to checkboxes for multi-select
        tune_label = QLabel("Select tune files to copy:")
        layout.addWidget(tune_label)

        # Create tune file checkboxes
        self.tune_checkboxes = {}
        tune_widget = QWidget()
        tune_layout = QVBoxLayout(tune_widget)
        tune_layout.setContentsMargins(0, 0, 0, 0)

        for suffix, filepath in self.tune_files:
            cb = QCheckBox(suffix)
            cb.setChecked(True)  # Default to selected
            self.tune_checkboxes[suffix] = (cb, filepath)
            tune_layout.addWidget(cb)

        layout.addWidget(tune_widget)

        # Select/Deselect buttons for tune files
        tune_btn_layout = QHBoxLayout()
        tune_select_all_btn = QPushButton("Select All Tunes")
        tune_select_all_btn.clicked.connect(self.select_all_tunes)
        tune_deselect_all_btn = QPushButton("Deselect All Tunes")
        tune_deselect_all_btn.clicked.connect(self.deselect_all_tunes)
        tune_btn_layout.addWidget(tune_select_all_btn)
        tune_btn_layout.addWidget(tune_deselect_all_btn)
        layout.addLayout(tune_btn_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Run selection
        run_label = QLabel("Select runs to copy to:")
        layout.addWidget(run_label)

        # Create scrollable area for run list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.run_checkboxes = {}
        for run in sorted(self.available_runs):
            if run != self.source_run:
                cb = QCheckBox(run)
                self.run_checkboxes[run] = cb
                scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Select/Deselect buttons for runs
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All Runs")
        select_all_btn.clicked.connect(self.select_all_runs)
        deselect_all_btn = QPushButton("Deselect All Runs")
        deselect_all_btn.clicked.connect(self.deselect_all_runs)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        layout.addLayout(btn_layout)

        # OK/Cancel buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.accept)
        copy_btn.setStyleSheet("background-color: #4A90D9; color: white;")
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(copy_btn)
        layout.addLayout(btn_box)

    def select_all_tunes(self):
        for cb, _ in self.tune_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_tunes(self):
        for cb, _ in self.tune_checkboxes.values():
            cb.setChecked(False)

    def select_all_runs(self):
        for cb in self.run_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_runs(self):
        for cb in self.run_checkboxes.values():
            cb.setChecked(False)

    def get_selected_tune_suffixes(self):
        """Returns list of (suffix, filepath) tuples for selected tunes"""
        result = []
        for suffix, (cb, filepath) in self.tune_checkboxes.items():
            if cb.isChecked():
                result.append((suffix, filepath))
        return result

    def get_selected_runs(self):
        return [run for run, cb in self.run_checkboxes.items() if cb.isChecked()]



class MainWindow(QMainWindow):
    def __init__(self):
        # Initialize core variables FIRST
        self.tar_name = []
        self.level_expanded = {}
        self.combo_sel = None
        self.cached_targets_by_level = {} # Cache for search optimization
        self.is_tree_expanded = True  # Track expansion state

        # Thread pool for background file operations
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Status colors
        self.colors = {
            'finish': '#98FB98',    # PaleGreen
            'skip': '#FFDAB9',      # PeachPuff
            'running': '#FFFF00',   # Yellow
            'failed': '#FF9999',    # Light Red
            'scheduled': '#4A90D9', # Deeper Blue
            'pending': '#87CEEB',   # SkyBlue
            '': '#FFFFFF'           # White/No status
        }
        
        # Check if mock_runs exists, otherwise check if we are inside a run
        if os.path.exists("mock_runs"):
            self.run_base_dir = "mock_runs"
        elif os.path.exists(".target_dependency.csh"):
            # We are inside a run directory, so scan the parent directory
            self.run_base_dir = ".."
            logger.info(f"Detected run in current directory. Setting base to parent: {os.path.abspath(self.run_base_dir)}")
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
        
        # View Menu
        view_menu = self.menu_bar.addMenu("View")
        
        # Show Dependency Graph Action
        show_graph_action = QAction("Show Dependency Graph", self)
        show_graph_action.triggered.connect(self.show_dependency_graph)
        view_menu.addAction(show_graph_action)
        
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
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "tune", "start time", "end time"])
        self.tree.setModel(self.model)
        
        # Simple column width setup
        self.set_column_widths()

        # Initialize TreeViewEventFilter
        self.tree_view_event_filter = TreeViewEventFilter(self.tree, self)
        self.tree.viewport().installEventFilter(self.tree_view_event_filter)

        # Set ComboBox delegate for tune column (column 3)
        self.tune_delegate = TuneComboBoxDelegate(self.tree)
        self.tree.setItemDelegateForColumn(3, self.tune_delegate)

        main_layout.addWidget(self.tree)

        # Set right-click context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Connect double-click signal for copy functionality in All Status view
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)
        
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
        
        # Backup timer with longer interval (10 seconds) as fallback
        # This handles cases where file watcher might miss events
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.change_run)
        self.backup_timer.start(10000)  # 10 seconds
        
        # Debounce timer to batch rapid file changes
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.change_run)
        
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
        """Execute flow action and refresh view (runs command in background thread)."""
        # Get selected targets
        selected_targets = self.get_selected_targets()
        if not selected_targets:
            logger.warning(f"No targets selected for action: {action}")
            return

        # Get current run name
        current_run = self.combo.currentText()
        run_dir = os.path.join(self.run_base_dir, current_run)

        # Build command
        if action == 'XMeta_run all':
            cmd = f"cd {run_dir} && {action}"
            logger.info(f"{current_run}, {action}.")
        else:
            cmd = f"cd {run_dir} && {action} " + " ".join(selected_targets)
            logger.info(f"{current_run}, {action} {' '.join(selected_targets)}.")

        # For skip/unskip, execute synchronously to ensure status files are updated before refresh
        if action in ['XMeta_unskip', 'XMeta_skip']:
            try:
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(timeout=30)
                if stdout:
                    logger.info(stdout.decode())
                if stderr:
                    logger.error(stderr.decode())
            except subprocess.TimeoutExpired:
                process.kill()
                logger.error(f"Command timed out: {cmd}")
            except Exception as e:
                logger.error(f"Error executing command: {e}")

            # Rebuild cache and refresh UI after command completes
            self._build_status_cache(current_run)
            self.populate_data()
        else:
            # Execute other commands in background thread
            def run_command():
                try:
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
                    if stdout:
                        logger.info(stdout.decode())
                    if stderr:
                        logger.error(stderr.decode())
                    if process.returncode != 0:
                        logger.error(f"Command exited with code {process.returncode}")
                except subprocess.TimeoutExpired:
                    process.kill()
                    logger.error(f"Command timed out: {cmd}")
                except Exception as e:
                    logger.error(f"Error executing command: {e}")

            self._executor.submit(run_command)

        # Clear selection after operation
        self.tree.clearSelection()

    def filter_tree(self, text):
        """Filter tree items based on text input.
        If text is empty, restore full hierarchy.
        If text is present, show FLAT list of matching items (no parents).
        """
        logger.debug(f"filter_tree called with text='{text}'")
        
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
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "tune", "start time", "end time"])
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
        
        logger.info(f"Scanning for runs in: {os.path.abspath(self.run_base_dir)}")
        try:
            for item in os.listdir(self.run_base_dir):
                item_path = os.path.join(self.run_base_dir, item)
                if os.path.isdir(item_path):
                    # Check if .target_dependency.csh exists
                    dependency_file = os.path.join(item_path, ".target_dependency.csh")
                    if os.path.exists(dependency_file):
                        runs.append(item)
                        logger.info(f"Found run: {item}")
        except Exception as e:
            logger.error(f"Error scanning runs: {e}")
        
        logger.info(f"Total runs found: {len(runs)}")
        return sorted(runs)

    def show_all_status(self):
        """Show status summary of all run directories in the TreeView.
        Displays: Run Directory, Latest Target, Status, Time Stamp
        """
        logger.debug("show_all_status called")
        
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
        
        # Status to Color Mapping (use global constant)
        color_map = STATUS_COLORS
        
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
                    logger.error(f"Error scanning status for {run_name}: {e}")
            
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
        logger.debug(f"show_all_status completed, showing {len(runs)} runs")

    def restore_normal_view(self):
        """Restore the normal single-run TreeView from All Status view."""
        if self.is_all_status_view:
            self.is_all_status_view = False
            # Trigger a refresh of the normal view
            self.on_run_changed()

    def on_tree_double_clicked(self, index):
        """Handle double-click on tree view - copy run name in All Status view"""
        if not self.is_all_status_view:
            return

        # Get the run name from column 0 (Run Directory)
        run_name_index = self.model.index(index.row(), 0)
        run_name = self.model.data(run_name_index)

        if run_name:
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(run_name)
            logger.info(f"Copied run name to clipboard: {run_name}")

    def build_dependency_graph(self, run_name):
        """
        Build dependency graph data from .target_dependency.csh file.

        Returns:
            dict with 'nodes', 'edges', and 'levels' for DependencyGraphDialog
        """
        graph_data = {
            'nodes': [],      # List of (target_name, status)
            'edges': [],      # List of (source, target)
            'levels': {}      # level_num -> [targets]
        }

        dep_file = os.path.join(self.run_base_dir, run_name, '.target_dependency.csh')
        if not os.path.exists(dep_file):
            logger.warning(f"Dependency file not found for {run_name}")
            return graph_data

        try:
            # Parse targets by level
            targets_by_level = self.parse_dependency_file(run_name)
            graph_data['levels'] = targets_by_level

            # Collect all targets with their status
            all_targets = []
            for level, targets in targets_by_level.items():
                for target in targets:
                    all_targets.append(target)

            # Get status for each target and add to nodes
            for target in all_targets:
                status = self.get_target_status(run_name, target)
                graph_data['nodes'].append((target, status))

            # Parse dependency edges using pre-compiled regex
            with open(dep_file, 'r') as f:
                content = f.read()

            all_targets_set = set(all_targets)
            for match in RE_DEPENDENCY_OUT.finditer(content):
                source = match.group(1)
                if source in all_targets_set:
                    downstream_targets = match.group(2).strip().split()
                    for downstream in downstream_targets:
                        if downstream in all_targets_set:
                            graph_data['edges'].append((source, downstream))

            logger.debug(f"Built graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")

        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")

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
        dependency_file = os.path.join(self.run_base_dir, run_name, ".target_dependency.csh")
        targets_by_level = {}

        if not os.path.exists(dependency_file):
            logger.warning(f"Dependency file not found for {run_name}")
            return targets_by_level

        try:
            with open(dependency_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Parse lines like: set LEVEL_1 = "UpdateTunable ShGetData"
                    match = RE_LEVEL_LINE.match(line)
                    if match:
                        level_num = int(match.group(1))
                        targets = match.group(2).split()
                        targets_by_level[level_num] = targets
        except Exception as e:
            logger.error(f"Error parsing dependency file for {run_name}: {e}")

        return targets_by_level
        
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
        logger.info(f"Run changed to: {self.combo_sel}")

        if current_run:
            # Update tab label to reflect selected run
            if hasattr(self, 'tab_label'):
                self.tab_label.setText(current_run)

            # Build status cache BEFORE populating data (batch I/O optimization)
            self._build_status_cache(current_run)

            # Force clear to trigger full rebuild in populate_data with correct UI
            self.model.clear()
            # Repopulate tree data with targets from the selected run
            self.populate_data()

            # Update file system watcher to monitor new run's status directory
            if hasattr(self, 'status_watcher'):
                self.setup_status_watcher()


        
    def get_target_status(self, run_name, target_name):
        """Get status of a target by checking status files in run_dir/status/"""
        # Use cached status if available
        if hasattr(self, '_status_cache') and self._status_cache.get('run') == run_name:
            return self._status_cache.get('statuses', {}).get(target_name, "")

        run_dir = os.path.join(self.run_base_dir, run_name)
        status_dir = os.path.join(run_dir, "status")

        if not os.path.exists(status_dir):
            return "" # Default if no status dir

        # Check for status files: target_name.status
        possible_statuses = ["finish", "failed", "running", "skip", "scheduled", "pending"]

        # Check if any status file exists
        found_statuses = []
        for status in possible_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            if os.path.exists(status_file):
                found_statuses.append(status)

        if not found_statuses:
            return ""

        # If multiple statuses found, check modification time to see which is latest.
        latest_status = None
        latest_time = 0

        for status in found_statuses:
            status_file = os.path.join(status_dir, f"{target_name}.{status}")
            mtime = os.path.getmtime(status_file)
            if mtime > latest_time:
                latest_time = mtime
                latest_status = status

        return latest_status if latest_status else ""

    def _build_status_cache(self, run_name):
        """Build a cache of all target statuses for a run (batch I/O optimization)"""
        run_dir = os.path.join(self.run_base_dir, run_name)
        status_dir = os.path.join(run_dir, "status")
        tracker_dir = os.path.join(run_dir, "logs", "targettracker")

        statuses = {}
        times = {}  # target_name -> (start_time, end_time)

        # Build status cache
        if os.path.exists(status_dir):
            try:
                # Read all files in status directory at once
                status_files = os.listdir(status_dir)

                # Group by target name
                target_status_files = {}  # target_name -> [(status, mtime), ...]

                for filename in status_files:
                    filepath = os.path.join(status_dir, filename)
                    if not os.path.isfile(filepath):
                        continue

                    # Parse filename: target_name.status
                    parts = filename.rsplit('.', 1)
                    if len(parts) == 2:
                        target_name, status = parts
                        if target_name not in target_status_files:
                            target_status_files[target_name] = []
                        try:
                            mtime = os.path.getmtime(filepath)
                            target_status_files[target_name].append((status, mtime))
                        except OSError:
                            pass

                # For each target, find the latest status
                for target_name, status_list in target_status_files.items():
                    if status_list:
                        # Sort by mtime descending, get the latest
                        latest = max(status_list, key=lambda x: x[1])
                        statuses[target_name] = latest[0]

            except Exception as e:
                logger.error(f"Error building status cache: {e}")

        # Build time cache
        if os.path.exists(tracker_dir):
            try:
                tracker_files = os.listdir(tracker_dir)

                # Group by target name
                target_times = {}  # target_name -> {'start': mtime, 'finished': mtime}

                for filename in tracker_files:
                    filepath = os.path.join(tracker_dir, filename)
                    if not os.path.isfile(filepath):
                        continue

                    # Parse filename: target_name.start or target_name.finished
                    if filename.endswith('.start'):
                        target_name = filename[:-6]  # Remove '.start'
                        if target_name not in target_times:
                            target_times[target_name] = {}
                        try:
                            mtime = os.path.getmtime(filepath)
                            target_times[target_name]['start'] = mtime
                        except OSError:
                            pass
                    elif filename.endswith('.finished'):
                        target_name = filename[:-9]  # Remove '.finished'
                        if target_name not in target_times:
                            target_times[target_name] = {}
                        try:
                            mtime = os.path.getmtime(filepath)
                            target_times[target_name]['finished'] = mtime
                        except OSError:
                            pass

                # Format times
                for target_name, time_data in target_times.items():
                    start_time = ""
                    end_time = ""
                    if 'start' in time_data:
                        st_mtime = time_data['start'] + 28800
                        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(st_mtime))
                    if 'finished' in time_data:
                        ft_mtime = time_data['finished'] + 28800
                        end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ft_mtime))
                    times[target_name] = (start_time, end_time)

            except Exception as e:
                logger.error(f"Error building time cache: {e}")

        self._status_cache = {'run': run_name, 'statuses': statuses, 'times': times}

    def get_target_times(self, run_name, target_name):
        """Get start and end time from cache"""
        if hasattr(self, '_status_cache') and self._status_cache.get('run') == run_name:
            return self._status_cache.get('times', {}).get(target_name, ("", ""))
        return ("", "")

    def populate_data(self):
        # Use global STATUS_COLORS constant
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
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "tune", "start time", "end time"])
        self.set_column_widths()
        
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

            # Tune - get tune files and store in UserRole for ComboBox
            tune_files = self.get_tune_files(self.combo_sel, parent_target)
            tune_display = ", ".join([suffix for suffix, _ in tune_files]) if tune_files else ""
            tune_item = QStandardItem(tune_display)
            tune_item.setEditable(True)  # Must be editable for ComboBox delegate to work
            tune_item.setForeground(QBrush(Qt.black))
            tune_item.setData(tune_files, Qt.UserRole)  # Store full list for ComboBox
            parent_row.append(tune_item)

            # Time - get from cache
            start_time, end_time = self.get_target_times(current_run, parent_target)

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

                # Tune - get tune files and store in UserRole for ComboBox
                c_tune_files = self.get_tune_files(self.combo_sel, child_target)
                c_tune_display = ", ".join([suffix for suffix, _ in c_tune_files]) if c_tune_files else ""
                c_tune_item = QStandardItem(c_tune_display)
                c_tune_item.setEditable(True)  # Must be editable for ComboBox delegate to work
                c_tune_item.setForeground(QBrush(Qt.black))
                c_tune_item.setData(c_tune_files, Qt.UserRole)  # Store full list for ComboBox
                child_row.append(c_tune_item)

                # Time - get from cache
                c_start_time, c_end_time = self.get_target_times(current_run, child_target)

                c_st_item = QStandardItem(c_start_time)
                c_st_item.setEditable(False)
                c_st_item.setForeground(QBrush(Qt.black))
                child_row.append(c_st_item)

                c_et_item = QStandardItem(c_end_time)
                c_et_item.setEditable(False)
                c_et_item.setForeground(QBrush(Qt.black))
                child_row.append(c_et_item)
                
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

    # ========== Core Monitor.py Methods ==========
    
    def get_tree(self, run_dir):
        """Build tree from .target_dependency.csh file (from monitor.py/tree_handlers.py)"""
        if not os.path.exists(os.path.join(run_dir, '.target_dependency.csh')):
            logger.warning(f".target_dependency.csh not found in {run_dir}")
            return
        
        # Clear existing model
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["level", "target", "status", "tune", "start time", "end time"])
        
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
                tune_display = self.get_tune_display(run_dir, target)

                str_lv = ''.join(target_level)
                o.append(str_lv)
                d = [target_level, target, target_status, tune_display, start_time, end_time]
                l.append(d)
        
        # Get all unique levels and sort
        all_lv = list(set(o))
        all_lv.sort(key=o.index)
        
        # Group data by level
        level_data = {}
        for data in l:
            lvl, tgt, st, tune, ct, et = data
            str_data = ''.join(lvl)
            if str_data not in level_data:
                level_data[str_data] = []
            level_data[str_data].append((tgt, st, tune, ct, et))
        
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
            for value in [first_item[0], first_item[1], first_item[2], first_item[3], first_item[4]]:
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
                for tgt, st, tune, ct, et in items[1:]:
                    child_items = []
                    text_color = QColor("#333333")
                    # level column
                    level_item = QStandardItem()
                    level_item.setText(level)
                    level_item.setEditable(False)
                    level_item.setForeground(QBrush(text_color))
                    child_items.append(level_item)

                    # Other columns
                    for value in [tgt, st, tune, ct, et]:
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
            logger.debug(f"Re-applying filter: {self.filter_input.text()}")
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

        try:
            with open(deps_file, 'r') as f:
                content = f.read()
                match = RE_ACTIVE_TARGETS.search(content)
                if match:
                    self.tar_name = match.group(1).split()
                    return
        except Exception as e:
            logger.error(f"Error reading ACTIVE_TARGETS: {e}")
        self.tar_name = []

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
        
        # Use debounce timer to batch rapid changes (300ms delay)
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(300)
    
    def on_status_file_changed(self, path):
        """Called when a watched file is modified."""
        logger.debug(f"Status file changed: {path}")
        
        # Use debounce timer to batch rapid changes
        if not self.debounce_timer.isActive():
            self.debounce_timer.start(300)

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
            if parent_item:
                # Child row
                level_item = parent_item.child(row_idx, 0)
                target_item = parent_item.child(row_idx, 1)
                status_item = parent_item.child(row_idx, 2)
                tune_item = parent_item.child(row_idx, 3)
                start_time_item = parent_item.child(row_idx, 4)
                end_time_item = parent_item.child(row_idx, 5)
            else:
                # Top-level row
                level_item = self.model.item(row_idx, 0)
                target_item = self.model.item(row_idx, 1)
                status_item = self.model.item(row_idx, 2)
                tune_item = self.model.item(row_idx, 3)
                start_time_item = self.model.item(row_idx, 4)
                end_time_item = self.model.item(row_idx, 5)

            if not all([target_item, status_item]):
                return

            target = target_item.text()
            if not target:
                return

            # Get status and time from cache
            status = self.get_target_status(current_run, target)
            start_time, end_time = self.get_target_times(current_run, target)

            # Update status text
            if status != status_item.text():
                status_item.setText(status)

                # Update background color for ALL columns in this row
                color = QColor(self.colors.get(status, '#87CEEB'))
                row_items = [level_item, target_item, status_item, tune_item, start_time_item, end_time_item]
                for item in row_items:
                    if item:
                        item.setBackground(QBrush(color))

            # Update time
            if start_time_item and start_time != start_time_item.text():
                start_time_item.setText(start_time)
            if end_time_item and end_time != end_time_item.text():
                end_time_item.setText(end_time)

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
        """Open shell file for selected target (runs in background thread)"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        shell_file = os.path.join(self.combo_sel, 'make_targets', f"{target}.csh")

        if os.path.exists(shell_file):
            def open_file():
                try:
                    subprocess.run(['gvim', shell_file], check=True, timeout=5)
                except subprocess.TimeoutExpired:
                    pass  # gvim runs in background, timeout is expected
                except subprocess.CalledProcessError as e:
                    logger.error(f"gvim returned error code {e.returncode}")
                except FileNotFoundError:
                    logger.error("gvim not found in PATH")
                except Exception as e:
                    logger.error(f"Error opening csh: {e}")

            self._executor.submit(open_file)
        else:
            logger.warning(f"Shell file not found: {shell_file}")

    def handle_log(self):
        """Open log file for selected target (runs in background thread)"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        log_file = os.path.join(self.combo_sel, 'logs', f"{target}.log")
        log_file_gz = f"{log_file}.gz"

        def open_file():
            try:
                if os.path.exists(log_file):
                    subprocess.Popen(['gvim', log_file])
                elif os.path.exists(log_file_gz):
                    subprocess.Popen(['gvim', log_file_gz])
                else:
                    logger.warning(f"Log file not found: {log_file}")
            except FileNotFoundError:
                logger.error("gvim not found in PATH")
            except Exception as e:
                logger.error(f"Error opening log: {e}")

        self._executor.submit(open_file)

    def handle_cmd(self):
        """Open command file for selected target (runs in background thread)"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return
        target = selected_targets[0]
        cmd_file = os.path.join(self.combo_sel, 'cmds', f"{target}.cmd")

        if os.path.exists(cmd_file):
            def open_file():
                try:
                    subprocess.run(['gvim', cmd_file], check=True, timeout=5)
                except subprocess.TimeoutExpired:
                    pass  # gvim runs in background, timeout is expected
                except subprocess.CalledProcessError as e:
                    logger.error(f"gvim returned error code {e.returncode}")
                except FileNotFoundError:
                    logger.error("gvim not found in PATH")
                except Exception as e:
                    logger.error(f"Error opening cmd: {e}")

            self._executor.submit(open_file)
        else:
            logger.warning(f"Command file not found: {cmd_file}")

    # ========== Tune File Management ==========

    def get_tune_files(self, run_dir, target_name):
        """Get all tune files for a target.
        Tune file naming: {run_dir}/tune/{target}/{target}.{suffix}.tcl
        Returns: list of (suffix, full_path) tuples
        """
        import glob as glob_module
        tune_dir = os.path.join(run_dir, 'tune', target_name)
        if not os.path.exists(tune_dir):
            return []

        # Find all files matching pattern: {target}.{suffix}.tcl
        pattern = os.path.join(tune_dir, f"{target_name}.*.tcl")
        tune_files = []

        for filepath in glob_module.glob(pattern):
            filename = os.path.basename(filepath)
            # Extract suffix: {target}.{suffix}.tcl -> {suffix}
            parts = filename.split('.')
            if len(parts) >= 3:  # target.suffix.tcl
                suffix = '.'.join(parts[1:-1])  # Handle cases like pre.opt.tcl
                tune_files.append((suffix, filepath))

        return sorted(tune_files)

    def get_tune_display(self, run_dir, target_name):
        """Get tune display string for tree view.
        Returns comma-separated suffixes or empty string
        """
        tune_files = self.get_tune_files(run_dir, target_name)
        if not tune_files:
            return ""
        return ", ".join([suffix for suffix, _ in tune_files])

    def has_tune(self, run_dir, target_name):
        """Check if target has any tune file"""
        return len(self.get_tune_files(run_dir, target_name)) > 0

    def handle_tune(self):
        """Open tune file for selected target with gvim"""
        selected_targets = self.get_selected_targets()
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
        def open_file():
            try:
                subprocess.run(['gvim', tune_file], check=True, timeout=5)
            except subprocess.TimeoutExpired:
                pass  # gvim runs in background
            except subprocess.CalledProcessError as e:
                logger.error(f"gvim returned error code {e.returncode}")
            except FileNotFoundError:
                logger.error("gvim not found in PATH")
            except Exception as e:
                logger.error(f"Error opening tune: {e}")

        self._executor.submit(open_file)

    def copy_tune_to_runs(self):
        """Copy tune file to selected runs"""
        selected_targets = self.get_selected_targets()
        if not selected_targets or not self.combo_sel:
            return

        target = selected_targets[0]
        tune_files = self.get_tune_files(self.combo_sel, target)

        if not tune_files:
            QMessageBox.information(self, "Info", f"No tune file found for: {target}")
            return

        # Get available runs
        available_runs = []
        if hasattr(self, 'run_base_dir') and os.path.exists(self.run_base_dir):
            for item in os.listdir(self.run_base_dir):
                item_path = os.path.join(self.run_base_dir, item)
                dep_file = os.path.join(item_path, ".target_dependency.csh")
                if os.path.isdir(item_path) and os.path.exists(dep_file):
                    available_runs.append(item)

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

            # Copy selected tune files to selected runs
            total_success = 0
            total_attempts = len(selected_tunes) * len(selected_runs)

            for suffix, source_tune in selected_tunes:
                for run in selected_runs:
                    run_dir = os.path.join(self.run_base_dir, run) if hasattr(self, 'run_base_dir') else run
                    # Path: {run_dir}/tune/{target}/{target}.{suffix}.tcl
                    dest_dir = os.path.join(run_dir, 'tune', target)
                    dest_tune = os.path.join(dest_dir, f"{target}.{suffix}.tcl")

                    try:
                        # Create tune directory if not exists
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                        # Copy file (overwrite if exists)
                        shutil.copy2(source_tune, dest_tune)
                        logger.info(f"Copied tune to: {dest_tune}")
                        total_success += 1
                    except Exception as e:
                        logger.error(f"Failed to copy tune to {run}: {e}")

            # Build summary message
            tune_names = ", ".join([suffix for suffix, _ in selected_tunes])
            QMessageBox.information(self, "Copy Complete",
                f"Copied {len(selected_tunes)} tune file(s) ({tune_names})\nto {total_success}/{len(selected_runs)} runs")

    def Xterm(self):
        """Open terminal in current run directory (runs in background thread)"""
        if not self.combo_sel:
            return

        def open_terminal():
            try:
                original_dir = os.getcwd()
                os.chdir(self.combo_sel)
                subprocess.run(['XMeta_term'], check=False, timeout=5)
                os.chdir(original_dir)
            except subprocess.TimeoutExpired:
                pass  # Terminal runs in background
            except FileNotFoundError:
                logger.error("XMeta_term not found in PATH")
            except Exception as e:
                logger.error(f"Error opening terminal: {e}")

        self._executor.submit(open_terminal)

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
        tune_action = menu.addAction("Tune")
        copy_tune_action = menu.addAction("Copy Tune To...")
        menu.addSeparator()
        trace_up_action = menu.addAction("Trace Up")
        trace_down_action = menu.addAction("Trace Down")

        # Check if selected target has tune file and update menu text
        selected_targets = self.get_selected_targets()
        if selected_targets and self.combo_sel:
            tune_display = self.get_tune_display(self.combo_sel, selected_targets[0])
            if tune_display:
                tune_action.setText(f"Tune ({tune_display})")
            else:
                tune_action.setText("Tune")

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))

        if action == terminal_action:
            self.Xterm()
        elif action == csh_action:
            self.handle_csh()
        elif action == log_action:
            self.handle_log()
        elif action == cmd_action:
            self.handle_cmd()
        elif action == tune_action:
            self.handle_tune()
        elif action == copy_tune_action:
            self.copy_tune_to_runs()
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

                # Use pre-compiled regex patterns
                if inout == 'in':
                    pattern = re.compile(rf'set\s+ALL_RELATED_{re.escape(target)}\s*=\s*"([^"]*)"')
                else:
                    pattern = re.compile(rf'set\s+DEPENDENCY_OUT_{re.escape(target)}\s*=\s*"([^"]*)"')

                match = pattern.search(content)
                if match:
                    retrace_targets = match.group(1).split()
        except Exception as e:
            logger.error(f"Error parsing dependencies: {e}")

        return retrace_targets
            
        return retrace_targets

    def filter_tree_by_targets(self, targets_to_show):
        """Filter tree to show only specific targets"""
        logger.debug(f"Filtering tree for {len(targets_to_show)} targets")
        
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
        self.tab_label.setText(label_text)
        self.tab_label.setStyleSheet("border: none; font-weight: bold; color: #d32f2f; font-size: 13px;") # Red color for trace mode
        
        # 4. Ensure the selected target is visible and selected
        # (Optional: scroll to it)




    def set_column_widths(self):
        """Set column widths to user preferences"""
        self.tree.setColumnWidth(0, 80)  # level
        self.tree.setColumnWidth(1, 480) # target
        self.tree.setColumnWidth(2, 70)  # status
        self.tree.setColumnWidth(3, 150) # tune (show suffixes like "pre_opt, pre_output")
        self.tree.setColumnWidth(4, 140) # start time
        self.tree.setColumnWidth(5, 140) # end time

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load custom font (Inter) if available
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
