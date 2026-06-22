import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QApplication

from new_gui.presentation.presenters import output_controller
from new_gui.presentation.views.widgets.bottom_output_panel import BottomOutputPanel
from new_gui.presentation.views.widgets.embedded_terminal import EmbeddedTerminalWidget


class FakeOutputSplitter:
    """Minimal splitter double for bottom-output sizing tests."""

    def __init__(self, sizes=None, height=900):
        self._sizes = list(sizes or [640, 260])
        self._height = height

    def height(self):
        """Return the available content splitter height."""
        return self._height

    def sizes(self):
        """Return the current splitter sizes."""
        return list(self._sizes)

    def setSizes(self, sizes):
        """Capture the requested splitter sizes."""
        self._sizes = list(sizes)


class FakeBottomOutputPanel:
    """Minimal bottom-output panel double for presenter tests."""

    def __init__(self):
        self.visible = True
        self.raised = False
        self.fill_states = []

    def show(self):
        """Mark the panel visible."""
        self.visible = True

    def hide(self):
        """Mark the panel hidden."""
        self.visible = False

    def raise_(self):
        """Record that the panel was raised."""
        self.raised = True

    def isVisible(self):
        """Return whether the panel is visible."""
        return self.visible

    def set_terminal_content_filled(self, enabled):
        """Capture terminal fill-state updates from the presenter."""
        self.fill_states.append(bool(enabled))


class EmbeddedTerminalGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_embedded_child_geometry_keeps_bottom_safe_padding(self) -> None:
        terminal = EmbeddedTerminalWidget()
        terminal._process = type(
            "RunningProcess",
            (),
            {"state": lambda self: QProcess.Running},
        )()
        terminal._embedded_child_win_id = 42
        terminal._terminal_host.resize(240, 120)

        resize_calls = []

        with mock.patch(
            "new_gui.presentation.views.widgets.embedded_terminal."
            "terminal_embed_backend.resize_x11_window",
            side_effect=lambda *args: resize_calls.append(args),
        ):
            terminal._sync_embedded_window_geometry()

        self.assertEqual([(42, 1, 1, 238, 112)], resize_calls)

    def test_xterm_initial_rows_use_safe_child_geometry(self) -> None:
        terminal = EmbeddedTerminalWidget()
        terminal._current_run_dir = "/tmp"
        terminal._background_color = "#ffffff"
        terminal._foreground_color = "#111827"
        terminal._terminal_host.resize(240, 120)

        estimate_calls = []

        with mock.patch(
            "new_gui.presentation.views.widgets.embedded_terminal."
            "terminal_embed_backend.estimate_terminal_geometry",
            side_effect=lambda width, height, point_size=11: estimate_calls.append(
                (width, height, point_size)
            )
            or (80, 24),
        ):
            with mock.patch(
                "new_gui.presentation.views.widgets.embedded_terminal."
                "terminal_embed_backend.build_xterm_arguments",
                return_value=[],
            ):
                terminal._build_xterm_arguments()

        self.assertEqual([(238, 112, 11)], estimate_calls)


class BottomOutputPanelTerminalFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_terminal_fill_button_emits_requested_state(self) -> None:
        panel = BottomOutputPanel()
        states = []
        panel.terminal_content_fill_changed.connect(states.append)

        button = panel.findChild(type(panel._terminal_follow_run_button), "terminalContentFillButton")
        self.assertIsNotNone(button)

        button.click()
        self.assertEqual([True], states)
        self.assertTrue(panel.is_terminal_content_filled())

        button.click()
        self.assertEqual([True, False], states)
        self.assertFalse(panel.is_terminal_content_filled())

    def test_terminal_fill_presenter_restores_previous_bottom_height(self) -> None:
        splitter = FakeOutputSplitter(sizes=[640, 260], height=900)
        panel = FakeBottomOutputPanel()
        window = SimpleNamespace(
            _content_splitter=splitter,
            _bottom_output_panel=panel,
            _bottom_output_last_height=260,
            height=lambda: 900,
        )

        output_controller.set_terminal_output_content_filled(window, True)

        self.assertEqual([1, 899], splitter.sizes())
        self.assertEqual(260, window._bottom_output_last_height)
        self.assertTrue(window._terminal_output_content_filled)
        self.assertEqual([True], panel.fill_states)

        output_controller.set_terminal_output_content_filled(window, False)

        self.assertEqual([640, 260], splitter.sizes())
        self.assertEqual(260, window._bottom_output_last_height)
        self.assertFalse(window._terminal_output_content_filled)
        self.assertEqual([True, False], panel.fill_states)


if __name__ == "__main__":
    unittest.main()
