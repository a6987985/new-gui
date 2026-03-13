"""Custom tree-view classes used by the main GUI."""

from PyQt5.QtCore import QEvent, QModelIndex, QObject, QPoint, Qt
from PyQt5.QtGui import QColor, QPen, QPolygon
from PyQt5.QtWidgets import QTreeView

from new_gui.ui.widgets.scrollbars import RoundedScrollBar


class TreeViewEventFilter(QObject):
    """Event filter for handling TreeView expand/collapse events."""

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
                            if hasattr(self.parent, "combo_sel") and hasattr(self.parent, "level_expanded"):
                                run_dir = self.parent.combo_sel
                                if run_dir not in self.parent.level_expanded:
                                    self.parent.level_expanded[run_dir] = {}
                                self.parent.level_expanded[run_dir][level] = not is_expanded
                            return True

        return super().eventFilter(obj, event)

    def toggle_level_items(self, level):
        """Toggle visibility of items for a given level."""
        if level not in self.level_items:
            return

        self.level_expanded[level] = not self.level_expanded.get(level, True)
        rows = self.level_items[level]
        if not rows:
            return

        for index, row in enumerate(rows):
            if index == 0:
                continue
            self.tree_view.setRowHidden(row, QModelIndex(), not self.level_expanded[level])


class ColorTreeView(QTreeView):
    """Tree view with custom rounded scrollbars and branch drawing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._v_scrollbar = RoundedScrollBar(Qt.Vertical, self, show_step_buttons=True)
        self._h_scrollbar = RoundedScrollBar(Qt.Horizontal, self, show_step_buttons=True)
        self._v_scrollbar.setFixedWidth(16)
        self._h_scrollbar.setFixedHeight(16)
        self._v_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self._h_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self.setVerticalScrollBar(self._v_scrollbar)
        self.setHorizontalScrollBar(self._h_scrollbar)

    def drawBranches(self, painter, rect, index):
        is_selected = self.selectionModel().isSelected(index)
        is_current = (
            self.currentIndex().row() == index.row()
            and self.currentIndex().parent() == index.parent()
        )

        painter.save()

        if is_selected:
            painter.fillRect(rect, QColor("#C0C0BE"))
        else:
            brush = index.data(Qt.BackgroundRole)
            if brush:
                painter.fillRect(rect, brush)

        if index.model().hasChildren(index):
            pen = QPen(QColor("#000000"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(QColor("#333333"))

            center_x = rect.center().x()
            center_y = rect.center().y()
            arrow_size = 4

            if self.isExpanded(index):
                points = QPolygon(
                    [
                        QPoint(center_x - arrow_size, center_y - arrow_size // 2),
                        QPoint(center_x + arrow_size, center_y - arrow_size // 2),
                        QPoint(center_x, center_y + arrow_size // 2),
                    ]
                )
            else:
                points = QPolygon(
                    [
                        QPoint(center_x - arrow_size // 2, center_y - arrow_size),
                        QPoint(center_x + arrow_size // 2, center_y),
                        QPoint(center_x - arrow_size // 2, center_y + arrow_size),
                    ]
                )

            painter.drawPolygon(points)

        painter.restore()
