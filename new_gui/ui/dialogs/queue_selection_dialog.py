"""Dialog for selecting one queue from the current available choices."""

from typing import Callable, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from new_gui.ui.queue_selection_styles import build_queue_selection_dialog_style


class QueueSelectionDialog(QDialog):
    """Choose one queue for the active target from the discovered queue list."""

    def __init__(
        self,
        target_name: str,
        current_queue: str,
        discovery_result: Dict[str, object],
        refresh_callback: Callable[[], Dict[str, object]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._target_name = target_name
        self._current_queue = str(current_queue or "").strip()
        self._refresh_callback = refresh_callback
        self._button_group = QButtonGroup(self)
        self._queue_buttons: Dict[str, QRadioButton] = {}
        self._list_layout: Optional[QVBoxLayout] = None
        self._hint_label: Optional[QLabel] = None
        self._setup_ui()
        self._apply_discovery_result(discovery_result)

    def selected_queue(self) -> str:
        """Return the currently selected queue value."""
        checked = self._button_group.checkedButton()
        if checked is None:
            return ""
        return str(checked.property("queue_name") or "").strip()

    def _setup_ui(self) -> None:
        """Build the dialog widgets."""
        self.setWindowTitle("Select Queue")
        self.setModal(True)
        self.resize(420, 340)
        self.setStyleSheet(build_queue_selection_dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_label = QLabel("Queue Selection")
        title_label.setObjectName("queueSelectionTitle")
        layout.addWidget(title_label)

        meta_label = QLabel(f"Choose one queue for target '{self._target_name}'.")
        meta_label.setObjectName("queueSelectionMeta")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        self._hint_label = QLabel("")
        self._hint_label.setObjectName("queueSelectionHint")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        list_frame = QFrame()
        list_frame.setObjectName("queueSelectionListFrame")
        frame_layout = QVBoxLayout(list_frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(6)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        self._list_layout = QVBoxLayout(scroll_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        frame_layout.addWidget(scroll_area)
        layout.addWidget(list_frame, 1)

        actions_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("queueSelectionActionButton")
        refresh_button.clicked.connect(self._refresh_queues)
        actions_layout.addWidget(refresh_button)
        actions_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("queueSelectionActionButton")
        cancel_button.clicked.connect(self.reject)
        actions_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply")
        apply_button.setObjectName("queueSelectionPrimaryButton")
        apply_button.clicked.connect(self.accept)
        actions_layout.addWidget(apply_button)
        layout.addLayout(actions_layout)

    def _clear_buttons(self) -> None:
        """Remove all currently displayed queue choices."""
        if self._list_layout is None:
            return

        self._button_group = QButtonGroup(self)
        self._queue_buttons.clear()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                child_layout.deleteLater()
        self._list_layout.addStretch()

    def _apply_discovery_result(self, discovery_result: Dict[str, object]) -> None:
        """Rebuild the queue choice list from one discovery result."""
        queues = [str(item).strip() for item in discovery_result.get("queues", []) if str(item).strip()]
        source = str(discovery_result.get("source") or "").strip()
        message = str(discovery_result.get("message") or "").strip()

        self._clear_buttons()
        if self._hint_label is not None:
            if source == "lsf":
                self._hint_label.setText(message or "Queues discovered from live LSF.")
            else:
                self._hint_label.setText(message or "Showing fallback queue choices from this project.")

        if self._list_layout is None:
            return

        if not queues:
            empty_label = QLabel("No queue choices are available.")
            empty_label.setObjectName("queueSelectionHint")
            empty_label.setAlignment(Qt.AlignCenter)
            self._list_layout.insertWidget(0, empty_label)
            return

        preferred_queue = self._current_queue if self._current_queue in queues else queues[0]
        for queue_name in queues:
            button = QRadioButton(queue_name)
            button.setProperty("queue_name", queue_name)
            self._button_group.addButton(button)
            self._queue_buttons[queue_name] = button
            self._list_layout.insertWidget(self._list_layout.count() - 1, button)
            if queue_name == preferred_queue:
                button.setChecked(True)

    def _refresh_queues(self) -> None:
        """Refresh queue choices through the provided callback."""
        if self._refresh_callback is None:
            return
        self._apply_discovery_result(self._refresh_callback())
