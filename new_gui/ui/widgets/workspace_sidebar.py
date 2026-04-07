"""Codex-style stage/type sidebar for target categories."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class WorkspaceSidebar(QWidget):
    """Left stage/type navigation panel for target category display."""

    scope_changed = pyqtSignal(str)
    category_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workspaceSidebar")
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)
        self._active_scope = "stage"
        self._stage_categories = []
        self._type_categories = []
        self._selected_stage_category_id = ""
        self._selected_type_category_id = ""
        self._category_buttons = []
        self._button_group = None
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        root_layout.addWidget(self._build_tab_strip())

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setWidget(self._build_category_content())
        root_layout.addWidget(self._scroll_area, 1)

    def _build_tab_strip(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._primary_tab_btn = QPushButton("STAGE", container)
        self._primary_tab_btn.setObjectName("sidebarPrimaryTab")
        self._primary_tab_btn.setCheckable(True)
        self._primary_tab_btn.setChecked(True)
        self._primary_tab_btn.setCursor(Qt.PointingHandCursor)
        self._primary_tab_btn.setFixedHeight(34)
        self._primary_tab_btn.clicked.connect(self._activate_primary_tab)

        self._advanced_tab_btn = QPushButton("TYPE", container)
        self._advanced_tab_btn.setObjectName("sidebarAdvancedTab")
        self._advanced_tab_btn.setCheckable(True)
        self._advanced_tab_btn.setChecked(False)
        self._advanced_tab_btn.setCursor(Qt.PointingHandCursor)
        self._advanced_tab_btn.setFixedHeight(34)
        self._advanced_tab_btn.clicked.connect(self._activate_advanced_tab)

        layout.addWidget(self._primary_tab_btn, 1)
        layout.addWidget(self._advanced_tab_btn, 1)
        return container

    def _build_category_content(self) -> QWidget:
        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(6)
        self._category_container_layout = layout

        self._empty_label = QLabel("No category data found in bb.tcl", content)
        self._empty_label.setObjectName("sidebarEmptyLabel")
        self._empty_label.setWordWrap(True)
        self._empty_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._empty_label)
        layout.addStretch(1)
        return content

    def _activate_primary_tab(self) -> None:
        if self._active_scope == "stage":
            self._primary_tab_btn.setChecked(True)
            self._advanced_tab_btn.setChecked(False)
            return
        self._primary_tab_btn.setChecked(True)
        self._advanced_tab_btn.setChecked(False)
        self._active_scope = "stage"
        self._rebuild_category_rows()
        self.scope_changed.emit(self._active_scope)

    def _activate_advanced_tab(self) -> None:
        if self._active_scope == "type":
            self._advanced_tab_btn.setChecked(True)
            self._primary_tab_btn.setChecked(False)
            return
        self._advanced_tab_btn.setChecked(True)
        self._primary_tab_btn.setChecked(False)
        self._active_scope = "type"
        self._rebuild_category_rows()
        self.scope_changed.emit(self._active_scope)

    def set_stage_categories(self, categories) -> None:
        """Replace STAGE rows with category labels loaded from bb.tcl."""
        self._stage_categories = list(categories or [])
        stage_ids = {str(category.get("id") or "") for category in self._stage_categories}
        if self._selected_stage_category_id not in stage_ids:
            self._selected_stage_category_id = ""
        if self._active_scope == "stage":
            self._rebuild_category_rows()

    def set_type_categories(self, categories) -> None:
        """Replace TYPE rows. TYPE remains empty in the current version."""
        self._type_categories = list(categories or [])
        type_ids = {str(category.get("id") or "") for category in self._type_categories}
        if self._selected_type_category_id not in type_ids:
            self._selected_type_category_id = ""
        if self._active_scope == "type":
            self._rebuild_category_rows()

    def active_scope(self) -> str:
        """Return current sidebar scope name."""
        return self._active_scope

    def selected_category_id(self, scope: str = "stage") -> str:
        """Return selected category id for one scope."""
        normalized_scope = (scope or "stage").strip().lower()
        if normalized_scope == "type":
            return self._selected_type_category_id
        return self._selected_stage_category_id

    def selected_category_targets(self, scope: str = "stage") -> list:
        """Return selected category target list for one scope."""
        selected_id = self.selected_category_id(scope)
        if not selected_id:
            return []
        source = self._type_categories if (scope or "").strip().lower() == "type" else self._stage_categories
        for category in source:
            if str(category.get("id") or "") == selected_id:
                targets = category.get("targets") or []
                return list(targets) if isinstance(targets, (list, tuple, set)) else []
        return []

    def clear_category_selection(self) -> None:
        """Clear persisted category selection for both scopes."""
        self._selected_stage_category_id = ""
        self._selected_type_category_id = ""
        for button in self._category_buttons:
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
        if self._button_group is not None:
            self._button_group.setExclusive(False)
            for button in self._button_group.buttons():
                button.setChecked(False)
            self._button_group.setExclusive(True)

    def _current_categories(self):
        if self._active_scope == "type":
            return self._type_categories
        return self._stage_categories

    def _rebuild_category_rows(self) -> None:
        """Rebuild rows for the current STAGE/TYPE scope."""
        categories = self._current_categories()

        for button in self._category_buttons:
            button.deleteLater()
        self._category_buttons = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.buttonClicked.connect(self._on_category_button_clicked)

        if not hasattr(self, "_category_container_layout"):
            return

        while self._category_container_layout.count() > 0:
            item = self._category_container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not categories:
            empty_text = "No TYPE categories yet" if self._active_scope == "type" else "No STAGE data found in bb.tcl"
            self._empty_label = QLabel(empty_text, self)
            self._empty_label.setObjectName("sidebarEmptyLabel")
            self._empty_label.setWordWrap(True)
            self._category_container_layout.addWidget(self._empty_label)
            self._category_container_layout.addStretch(1)
            return

        selected_id = (
            self._selected_type_category_id
            if self._active_scope == "type"
            else self._selected_stage_category_id
        )

        for category in categories:
            label = str(category.get("label") or "").strip()
            category_id = str(category.get("id") or "").strip()

            button = QPushButton(label, self)
            button.setObjectName("sidebarCategoryRow")
            button.setCheckable(True)
            button.setChecked(category_id == selected_id)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(28)
            button.setProperty("category_id", category_id)
            self._category_container_layout.addWidget(button)
            self._category_buttons.append(button)
            self._button_group.addButton(button)

        self._category_container_layout.addStretch(1)

    def _on_category_button_clicked(self, button) -> None:
        """Emit one selection event for single-select category rows."""
        if button is None:
            return
        category_id = str(button.property("category_id") or "").strip()
        if self._active_scope == "type":
            self._selected_type_category_id = category_id
            self.category_changed.emit("type", category_id)
            return
        self._selected_stage_category_id = category_id
        self.category_changed.emit("stage", category_id)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #workspaceSidebar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2b2f34,
                    stop: 0.65 #252a2f,
                    stop: 1 #20252a
                );
                border-right: 1px solid #333841;
            }
            #sidebarPrimaryTab,
            #sidebarAdvancedTab {
                border: 1px solid transparent;
                border-bottom: 1px solid #5a616a;
                color: #000000;
                font-size: 11px;
                font-weight: 400;
                letter-spacing: 0.8px;
                padding: 0px;
            }
            #sidebarPrimaryTab:checked {
                background: #eef0f2;
                color: #000000;
                border: 1px solid #dfe3e8;
                border-bottom: 1px solid #dfe3e8;
                border-radius: 4px;
            }
            #sidebarAdvancedTab:checked {
                background: #eef0f2;
                color: #000000;
                border: 1px solid #dfe3e8;
                border-bottom: 1px solid #dfe3e8;
                border-radius: 4px;
            }
            #sidebarCategoryRow {
                border: none;
                border-radius: 8px;
                background: transparent;
                color: #000000;
                text-align: left;
                padding: 0 8px;
                font-size: 12px;
                font-weight: 400;
            }
            #sidebarCategoryRow:checked {
                background: #3a3f46;
                color: #f0f2f4;
            }
            #sidebarCategoryRow:hover {
                background: #343a40;
                color: #eef0f3;
            }
            #sidebarEmptyLabel {
                color: #aeb5be;
                font-size: 11px;
                font-weight: 400;
                padding: 6px 4px;
            }
            QScrollArea {
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            """
        )
