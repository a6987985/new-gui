import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from new_gui.presentation.views.widgets.workspace_sidebar import (
    WorkspaceSidebar,
    compute_sidebar_background_colors,
    compute_sidebar_tab_state_background,
)
from new_gui.model.services import sidebar_view


class WorkspaceSidebarColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_xmeta_like_blue_background_gets_lighter_by_5_percent_lightness(self) -> None:
        sidebar_bg, sidebar_border = compute_sidebar_background_colors("#7ea3b9")

        self.assertEqual("#8fb0c3", sidebar_bg)
        self.assertEqual("#82a0b1", sidebar_border)

    def test_sidebar_tab_state_background_gets_lighter_by_10_percent(self) -> None:
        self.assertEqual("#9dc2d6", compute_sidebar_tab_state_background("#8fb0c3"))

    def test_sidebar_renders_its_own_background_behind_category_rows(self) -> None:
        window = QMainWindow()
        window.window_bg = "#84a7bc"

        central = QWidget()
        central.setStyleSheet("background-color: #84a7bc;")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = WorkspaceSidebar(window)
        sidebar.setFixedWidth(140)
        sidebar.set_stage_categories([{"id": "1", "label": "A", "targets": []}])
        layout.addWidget(sidebar)

        filler = QWidget()
        filler.setStyleSheet("background-color: #112233;")
        layout.addWidget(filler, 1)

        window.setCentralWidget(central)
        window.resize(320, 240)
        window.show()
        self._app.processEvents()

        pixmap = QPixmap(window.size())
        window.render(pixmap)
        image = pixmap.toImage()

        expected_sidebar_bg, _ = compute_sidebar_background_colors(window.window_bg)
        self.assertEqual(expected_sidebar_bg, QColor(image.pixel(20, 120)).name())
        self.assertEqual("#112233", QColor(image.pixel(220, 120)).name())

    def test_sidebar_renders_rounded_outer_corners(self) -> None:
        window = QMainWindow()
        window.window_bg = "#84a7bc"

        central = QWidget()
        central.setStyleSheet("background-color: #84a7bc;")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = WorkspaceSidebar(window)
        sidebar.setFixedWidth(140)
        sidebar.set_stage_categories([{"id": "1", "label": "A", "targets": []}])
        layout.addWidget(sidebar)

        filler = QWidget()
        filler.setStyleSheet("background-color: #112233;")
        layout.addWidget(filler, 1)

        window.setCentralWidget(central)
        window.resize(320, 240)
        window.show()
        self._app.processEvents()

        pixmap = QPixmap(window.size())
        window.render(pixmap)
        image = pixmap.toImage()

        expected_sidebar_bg, _ = compute_sidebar_background_colors(window.window_bg)
        expected_tab_state_bg = compute_sidebar_tab_state_background(expected_sidebar_bg)
        self.assertEqual("#84a7bc", QColor(image.pixel(1, 1)).name())
        self.assertEqual(expected_tab_state_bg, QColor(image.pixel(20, 20)).name())
        self.assertEqual(expected_sidebar_bg, QColor(image.pixel(20, 120)).name())

    def test_sidebar_tabs_have_no_horizontal_gap(self) -> None:
        window = QMainWindow()
        sidebar = WorkspaceSidebar(window)
        sidebar.resize(220, 260)
        window.setCentralWidget(sidebar)
        window.show()
        self._app.processEvents()

        stage_x, _, stage_w, _ = sidebar._primary_tab_btn.geometry().getRect()
        type_x, _, _, _ = sidebar._advanced_tab_btn.geometry().getRect()
        self.assertEqual(stage_x + stage_w, type_x)

    def test_selected_tab_has_no_blue_underline(self) -> None:
        window = QMainWindow()
        window.window_bg = "#84a7bc"

        central = QWidget()
        central.setStyleSheet("background-color: #84a7bc;")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = WorkspaceSidebar(window)
        sidebar.setFixedWidth(220)
        sidebar.set_stage_categories([{"id": "1", "label": "A", "targets": []}])
        layout.addWidget(sidebar)

        filler = QWidget()
        filler.setStyleSheet("background-color: #112233;")
        layout.addWidget(filler, 1)

        window.setCentralWidget(central)
        window.resize(420, 260)
        window.show()
        self._app.processEvents()

        pixmap = QPixmap(window.size())
        window.render(pixmap)
        image = pixmap.toImage()

        expected_sidebar_bg, _ = compute_sidebar_background_colors(window.window_bg)
        expected_tab_state_bg = compute_sidebar_tab_state_background(expected_sidebar_bg)
        self.assertEqual(expected_tab_state_bg, QColor(image.pixel(40, 54)).name())

    def test_public_api_selects_category_without_emitting_by_default(self) -> None:
        sidebar = WorkspaceSidebar()
        emitted = []
        sidebar.scope_changed.connect(lambda scope: emitted.append(("scope", scope)))
        sidebar.category_changed.connect(
            lambda scope, category_id: emitted.append(("category", scope, category_id))
        )
        sidebar.set_stage_categories([{"id": "stage_a", "label": "Stage A", "targets": ["alpha"]}])
        sidebar.set_type_categories([{"id": "type_a", "label": "Type A", "targets": ["beta"]}])

        self.assertTrue(sidebar.set_active_scope("type"))
        self.assertTrue(sidebar.select_category("type", "type_a"))

        self.assertEqual("type", sidebar.active_scope())
        self.assertEqual("type_a", sidebar.selected_category_id("type"))
        self.assertEqual([], emitted)

    def test_restore_category_view_uses_sidebar_public_api(self) -> None:
        class PublicOnlySidebar:
            def __init__(self):
                self.scope = "stage"
                self.selected = ""

            def active_scope(self):
                return self.scope

            def set_active_scope(self, scope):
                self.scope = scope
                return True

            def select_category(self, scope, category_id):
                self.scope = scope
                self.selected = category_id
                return True

            def selected_category_targets(self, _scope):
                return ["alpha"]

        window = type("Window", (), {})()
        window.left_sidebar = PublicOnlySidebar()
        window.combo_sel = None
        window.is_all_status_view = False
        window._stage_categories = [{"id": "stage_a", "label": "Stage A", "targets": ["alpha"]}]
        window._type_categories = []
        window.get_active_category_target_set = lambda: {"alpha"}
        applied_tab = []
        window._apply_tab_state = lambda tab_state: applied_tab.append(tab_state)

        self.assertTrue(sidebar_view.restore_category_view(window, "stage", "stage_a"))
        self.assertEqual("stage", window.left_sidebar.scope)
        self.assertEqual("stage_a", window.left_sidebar.selected)
        self.assertTrue(applied_tab)


if __name__ == "__main__":
    unittest.main()
