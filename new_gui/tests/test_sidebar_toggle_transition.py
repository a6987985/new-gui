import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QApplication

from new_gui.main import MainWindow


class SidebarToggleTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _populate_dense_tree(self, window: MainWindow) -> None:
        model = window.model
        model.removeRows(0, model.rowCount())
        model.setHorizontalHeaderLabels(
            ["Level", "Target", "Status", "Tune", "Start", "End", "CPU", "Mem", "Host"]
        )
        for level in range(18):
            parent_items = [QStandardItem(f"Level {level}")] + [QStandardItem("") for _ in range(8)]
            model.appendRow(parent_items)
            parent = parent_items[0]
            for row in range(45):
                child_items = [
                    QStandardItem(""),
                    QStandardItem(f"target_{level}_{row}"),
                    QStandardItem("running"),
                ] + [QStandardItem("") for _ in range(6)]
                parent.appendRow(child_items)
        window.expand_tree_all()
        self._app.processEvents()

    def test_hiding_sidebar_switches_immediately_without_transition_artifacts(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._populate_dense_tree(window)

        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        self.assertEqual(0, window.left_sidebar.width())
        self.assertIsNone(getattr(window, "_left_sidebar_width_animation", None))
        self.assertIsNone(getattr(window, "_left_sidebar_transition_overlay", None))
        self.assertIsNone(getattr(window, "_content_transition_overlay", None))

    def test_showing_sidebar_switches_immediately_without_transition_artifacts(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._populate_dense_tree(window)

        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        window.set_left_sidebar_visible(True)
        self._app.processEvents()

        self.assertEqual(window._left_sidebar_default_width, window.left_sidebar.width())
        self.assertIsNone(getattr(window, "_left_sidebar_width_animation", None))
        self.assertIsNone(getattr(window, "_left_sidebar_transition_overlay", None))
        self.assertIsNone(getattr(window, "_content_transition_overlay", None))

    def test_showing_sidebar_sets_final_width_before_showing_widget(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._populate_dense_tree(window)

        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        widths_at_show = []
        original_show = window.left_sidebar.show

        def record_show():
            widths_at_show.append(window.left_sidebar.width())
            original_show()

        window.left_sidebar.show = record_show
        window.set_left_sidebar_visible(True)
        self._app.processEvents()

        self.assertEqual([window._left_sidebar_default_width], widths_at_show)

    def test_hiding_sidebar_hides_widget_before_zeroing_width(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._populate_dense_tree(window)

        widths_at_hide = []
        original_hide = window.left_sidebar.hide

        def record_hide():
            widths_at_hide.append(window.left_sidebar.width())
            original_hide()

        window.left_sidebar.hide = record_hide
        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        self.assertEqual([window._left_sidebar_default_width], widths_at_hide)
        self.assertEqual(0, window.left_sidebar.width())

    def test_showing_sidebar_uses_final_viewport_width_for_tree_refit(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self._populate_dense_tree(window)

        window.set_left_sidebar_visible(False)
        self._app.processEvents()

        target_widths = []
        original_apply_width = window._apply_adaptive_target_column_width

        def record_target_width():
            target_widths.append(getattr(window, "_layout_target_viewport_width", None))
            original_apply_width()

        window._apply_adaptive_target_column_width = record_target_width
        window.set_left_sidebar_visible(True)
        self._app.processEvents()

        expected_width = (
            window._content_row.width()
            - window._left_sidebar_default_width
            - window._tree_view_container.layout().contentsMargins().right()
        )
        self.assertIn(expected_width, target_widths)


if __name__ == "__main__":
    unittest.main()
