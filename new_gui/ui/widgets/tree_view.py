"""Custom tree-view classes used by the main GUI."""

from PyQt5.QtCore import QEvent, QModelIndex, QObject, QPoint, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygon
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
        if self.tree_view is not None:
            self.tree_view.destroyed.connect(self._on_tree_view_destroyed)
        if self.parent is not None:
            self.parent.destroyed.connect(self._on_parent_destroyed)

    def _on_tree_view_destroyed(self, *_args):
        """Drop the Python reference once the tree view C++ object is gone."""
        self.tree_view = None

    def _on_parent_destroyed(self, *_args):
        """Drop the Python reference once the parent C++ object is gone."""
        self.parent = None

    def _get_live_tree_view(self):
        """Return the tree view only while its C++ object is still alive."""
        if self.tree_view is None:
            return None
        try:
            self.tree_view.viewport()
        except RuntimeError:
            self.tree_view = None
            return None
        return self.tree_view

    def eventFilter(self, obj, event):
        tree_view = self._get_live_tree_view()
        if tree_view is None or not obj:
            return False

        if obj == tree_view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                index = tree_view.indexAt(event.pos())
                if index.isValid():
                    column = tree_view.columnAt(event.x())
                    if column == 0:
                        model = tree_view.model()
                        if not model:
                            return False

                        item = model.itemFromIndex(index.sibling(index.row(), 0))
                        if item and item.hasChildren():
                            is_expanded = tree_view.isExpanded(index)
                            if is_expanded:
                                tree_view.collapse(index)
                            else:
                                tree_view.expand(index)
                            level = item.text()
                            if (
                                level
                                and not index.parent().isValid()
                                and self.parent is not None
                                and hasattr(self.parent, "combo_sel")
                                and hasattr(self.parent, "level_expanded")
                            ):
                                run_dir = self.parent.combo_sel
                                if run_dir not in self.parent.level_expanded:
                                    self.parent.level_expanded[run_dir] = {}
                                self.parent.level_expanded[run_dir][level] = not is_expanded
                            return True

        return super().eventFilter(obj, event)

    def toggle_level_items(self, level):
        """Toggle visibility of items for a given level."""
        tree_view = self._get_live_tree_view()
        if tree_view is None:
            return
        if level not in self.level_items:
            return

        self.level_expanded[level] = not self.level_expanded.get(level, True)
        rows = self.level_items[level]
        if not rows:
            return

        for index, row in enumerate(rows):
            if index == 0:
                continue
            tree_view.setRowHidden(row, QModelIndex(), not self.level_expanded[level])


class ColorTreeView(QTreeView):
    """Tree view with custom rounded scrollbars and branch drawing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row_index = QModelIndex()
        self._v_scrollbar = RoundedScrollBar(Qt.Vertical, self, show_step_buttons=True)
        self._h_scrollbar = RoundedScrollBar(Qt.Horizontal, self, show_step_buttons=True)
        self._v_scrollbar.setFixedWidth(16)
        self._h_scrollbar.setFixedHeight(16)
        self._v_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self._h_scrollbar.setColors("#b5b5b5", "#9f9f9f", "#8b8b8b", "#f3f3f3")
        self.setVerticalScrollBar(self._v_scrollbar)
        self.setHorizontalScrollBar(self._h_scrollbar)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def _row_index_key(self, index):
        """Return a stable row identity for hover comparisons."""
        if not index.isValid():
            return None
        return (index.row(), index.parent())

    def mouseMoveEvent(self, event):
        hovered_index = self.indexAt(event.pos())
        if hovered_index.isValid():
            hovered_index = hovered_index.sibling(hovered_index.row(), 0)
        if self._row_index_key(hovered_index) != self._row_index_key(self._hovered_row_index):
            self._hovered_row_index = hovered_index
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hovered_row_index.isValid():
            self._hovered_row_index = QModelIndex()
            self.viewport().update()
        super().leaveEvent(event)

    def _resolve_row_background_brush(self, index):
        """Return the stable row background brush for one visible branch area."""
        brush = index.data(Qt.BackgroundRole)
        if not brush:
            return None

        if isinstance(brush, QBrush):
            return brush
        if isinstance(brush, QColor):
            return QBrush(brush)
        return brush

    def drawBranches(self, painter, rect, index):
        selection_model = self.selectionModel()
        is_selected = selection_model.isSelected(index) if selection_model else False
        is_hovered = self._row_index_key(index) == self._row_index_key(self._hovered_row_index)
        brush = self._resolve_row_background_brush(index)

        painter.save()

        if is_selected:
            painter.fillRect(rect, QColor("#C0C0BE"))
        elif is_hovered:
            if brush:
                painter.fillRect(rect, brush)
            painter.fillRect(rect, QColor(230, 240, 255, 150))
        else:
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
