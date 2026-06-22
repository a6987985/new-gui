import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from new_gui.main import MainWindow
from new_gui.presentation.views.builders import window_builder


class LinuxRenderingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_window_fade_animation_is_disabled_on_linux(self) -> None:
        self.assertFalse(window_builder.should_enable_window_fade_animation("Linux"))

    def test_window_fade_animation_remains_enabled_on_non_linux(self) -> None:
        self.assertTrue(window_builder.should_enable_window_fade_animation("Darwin"))

    def test_main_tree_does_not_use_qtreeview_expand_collapse_animation(self) -> None:
        window = MainWindow()
        window.show()
        self._app.processEvents()
        self.assertFalse(window.tree.isAnimated())


if __name__ == "__main__":
    unittest.main()
