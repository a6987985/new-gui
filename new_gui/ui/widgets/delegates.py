from PyQt5.QtCore import QEvent, QRect, Qt
from PyQt5.QtGui import QColor, QBrush, QPen
from PyQt5.QtWidgets import QComboBox, QStyle, QStyleOptionViewItem, QStyledItemDelegate

from new_gui.config.settings import STATUS_CONFIG
from new_gui.services import file_actions
from new_gui.services import tree_rows
from new_gui.ui.delegate_styles import build_tune_combo_editor_style
from new_gui.ui.menu_styles import build_popup_menu_style
from new_gui.ui.theme_runtime import StatusAnimator


class BorderItemDelegate(QStyledItemDelegate):
    """Custom delegate for drawing row borders and status icons"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animator = StatusAnimator()

    def paint(self, painter, option, index):
        # 1. Manually draw background from model (Status Colors)
        bg_brush = index.data(Qt.BackgroundRole)
        original_color = None

        if bg_brush:
            painter.save()
            if isinstance(bg_brush, QBrush):
                original_color = bg_brush.color()
                # Check if this item has animation
                status_text = ""
                if index.column() == 2:  # Status column
                    status_text = index.data(Qt.DisplayRole) or ""

                status_config = STATUS_CONFIG.get(status_text.lower() if status_text else "", {})
                animation_type = status_config.get("animation")

                if animation_type == "pulse":
                    # Apply pulse animation for running status
                    animated_color = self._animator.get_animated_color(original_color, animation_type)
                    painter.fillRect(option.rect, QBrush(animated_color))
                else:
                    painter.fillRect(option.rect, bg_brush)
            elif isinstance(bg_brush, QColor):
                original_color = bg_brush
                painter.fillRect(option.rect, bg_brush)
            painter.restore()

        # 2. Manually draw Hover/Selection Background
        painter.save()
        bg_rect = QRect(option.rect)

        # Check if this item is in hover or selected state
        is_hover = option.state & QStyle.State_MouseOver
        is_selected = option.state & QStyle.State_Selected

        if is_selected:
            painter.fillRect(bg_rect, QColor(0xC0, 0xC0, 0xBE))
        elif is_hover:
            painter.fillRect(bg_rect, QColor(230, 240, 255, 150)) # Semi-transparent
        painter.restore()

        # 3. Let the style draw the content (text)
        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_MouseOver

        # Keep hover stable: only selected rows use bold text.
        if is_selected:
            font = opt.font
            font.setBold(True)
            opt.font = font

        super().paint(painter, opt, index)

        # 5. Draw custom border on top
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
        combo.setStyleSheet(build_tune_combo_editor_style())
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

        text_rect = option.rect.adjusted(5, 0, -5, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Handle mouse double-click to show popup"""
        if event.type() == QEvent.MouseButtonDblClick:
            from PyQt5.QtWidgets import QMenu

            target_item = model.itemFromIndex(model.index(index.row(), 1, index.parent()))
            if not tree_rows.get_row_target_name(target_item):
                return False

            # Create menu for dropdown
            menu = QMenu(self.tree_view)
            menu.setStyleSheet(
                build_popup_menu_style(
                    selected_background="#4A90D9",
                    selected_text_color="#ffffff",
                )
            )

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
                    file_actions.open_file_with_editor(filepath, use_popen=True)

            menu.triggered.connect(on_triggered)
            menu.exec_(popup_pos)
            return True
        return super().editorEvent(event, model, option, index)
