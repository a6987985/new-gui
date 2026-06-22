"""Codex-style stage/type sidebar for target categories."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
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


def compute_sidebar_background_colors(base_color_value) -> tuple[str, str]:
    """Return sidebar background and border colors derived from one base color."""
    base_color = QColor(base_color_value)
    if not base_color.isValid():
        base_color = QColor("#f5f5f5")

    hue, saturation, lightness, alpha = base_color.getHsl()
    lightness_offset = int(255 * 0.05 + 0.5)
    boosted_lightness = min(255, lightness + lightness_offset)
    sidebar_background = QColor()
    sidebar_background.setHsl(hue, saturation, boosted_lightness, alpha)
    sidebar_border = sidebar_background.darker(110)
    return sidebar_background.name(), sidebar_border.name()


def compute_sidebar_tab_state_background(sidebar_background_color: str) -> str:
    """Return the tab hover/selected background from one sidebar background color."""
    return QColor(sidebar_background_color).lighter(110).name()


class WorkspaceSidebar(QWidget):
    """Left stage/type navigation panel for target category display."""

    scope_changed = pyqtSignal(str)
    category_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workspaceSidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(236)
        self.setMaximumWidth(300)
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
        root_layout.setContentsMargins(14, 12, 14, 14)
        root_layout.setSpacing(6)

        root_layout.addWidget(self._build_tab_strip())

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("sidebarCategoryScrollArea")
        self._scroll_area.setAttribute(Qt.WA_StyledBackground, True)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setWidget(self._build_category_content())
        self._scroll_area.viewport().setObjectName("sidebarCategoryViewport")
        self._scroll_area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        root_layout.addWidget(self._scroll_area, 1)

    def _build_tab_strip(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("sidebarTabStrip")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._primary_tab_btn = QPushButton("STAGE", container)
        self._primary_tab_btn.setObjectName("sidebarPrimaryTab")
        self._primary_tab_btn.setCheckable(True)
        self._primary_tab_btn.setChecked(True)
        self._primary_tab_btn.setCursor(Qt.PointingHandCursor)
        self._primary_tab_btn.setFixedHeight(44)
        self._primary_tab_btn.setFlat(True)
        self._primary_tab_btn.clicked.connect(self._activate_primary_tab)

        self._advanced_tab_btn = QPushButton("TYPE", container)
        self._advanced_tab_btn.setObjectName("sidebarAdvancedTab")
        self._advanced_tab_btn.setCheckable(True)
        self._advanced_tab_btn.setChecked(False)
        self._advanced_tab_btn.setCursor(Qt.PointingHandCursor)
        self._advanced_tab_btn.setFixedHeight(44)
        self._advanced_tab_btn.setFlat(True)
        self._advanced_tab_btn.clicked.connect(self._activate_advanced_tab)

        layout.addWidget(self._primary_tab_btn, 1)
        layout.addWidget(self._advanced_tab_btn, 1)
        return container

    def _build_category_content(self) -> QWidget:
        content = QWidget(self)
        content.setObjectName("sidebarCategoryContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        self._category_container_layout = layout

        self._empty_label = QLabel("No category data found in target_stage.list", content)
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
        """Replace STAGE rows with category labels loaded from target_stage.list."""
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

    def set_active_scope(self, scope: str, emit_signal: bool = False) -> bool:
        """Select the visible category scope through the widget-owned API."""
        normalized_scope = (scope or "stage").strip().lower()
        if normalized_scope not in {"stage", "type"}:
            normalized_scope = "stage"

        changed = self._active_scope != normalized_scope
        self._active_scope = normalized_scope
        self._primary_tab_btn.setChecked(normalized_scope == "stage")
        self._advanced_tab_btn.setChecked(normalized_scope == "type")
        if changed:
            self._rebuild_category_rows()
            if emit_signal:
                self.scope_changed.emit(self._active_scope)
        return changed

    def selected_category_id(self, scope: str = "stage") -> str:
        """Return selected category id for one scope."""
        normalized_scope = (scope or "stage").strip().lower()
        if normalized_scope == "type":
            return self._selected_type_category_id
        return self._selected_stage_category_id

    def select_category(self, scope: str, category_id: str, emit_signal: bool = False) -> bool:
        """Select one category row through the widget-owned API."""
        normalized_scope = (scope or "stage").strip().lower()
        if normalized_scope not in {"stage", "type"}:
            normalized_scope = "stage"
        normalized_id = (category_id or "").strip()

        self.set_active_scope(normalized_scope, emit_signal=False)
        if normalized_scope == "type":
            changed = self._selected_type_category_id != normalized_id
            self._selected_type_category_id = normalized_id
        else:
            changed = self._selected_stage_category_id != normalized_id
            self._selected_stage_category_id = normalized_id

        self._sync_category_button_selection(normalized_id)
        if emit_signal and changed:
            self.category_changed.emit(normalized_scope, normalized_id)
        return changed

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
        self._sync_category_button_selection("")
        if self._button_group is not None:
            self._button_group.setExclusive(False)
            for button in self._button_group.buttons():
                button.setChecked(False)
            self._button_group.setExclusive(True)

    def _sync_category_button_selection(self, category_id: str) -> None:
        """Reflect the selected category id in rendered category buttons."""
        normalized_id = (category_id or "").strip()
        for button in self._category_buttons:
            button.blockSignals(True)
            button.setChecked(str(button.property("category_id") or "").strip() == normalized_id)
            button.blockSignals(False)

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
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if not categories:
            empty_text = (
                "No TYPE categories yet"
                if self._active_scope == "type"
                else "No STAGE data found in target_stage.list"
            )
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
            if not label:
                continue

            button = QPushButton(label, self)
            button.setObjectName("sidebarCategoryRow")
            button.setCheckable(True)
            button.setChecked(category_id == selected_id)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(40)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        sidebar_bg, sidebar_border = self._resolve_sidebar_background_colors()
        tab_state_bg = compute_sidebar_tab_state_background(sidebar_bg)
        self.setStyleSheet(
            """
            #workspaceSidebar {{
                background: {sidebar_bg};
                border-right: 1px solid {sidebar_border};
                border-radius: 12px;
            }}
            #sidebarTabStrip {{
                background: transparent;
                border-bottom: 1px solid #d8e1ee;
            }}
            #sidebarPrimaryTab,
            #sidebarAdvancedTab {{
                border: none;
                background: transparent;
                color: #111827;
                font-size: 13px;
                font-weight: 500;
                padding: 0;
                border-radius: 8px;
            }}
            #sidebarPrimaryTab:hover,
            #sidebarAdvancedTab:hover {{
                color: #10192e;
                background: {tab_state_bg};
            }}
            #sidebarPrimaryTab:checked,
            #sidebarAdvancedTab:checked {{
                color: #131a2b;
                font-weight: 600;
                background: {tab_state_bg};
            }}
            #sidebarCategoryRow {{
                border: 1px solid transparent;
                border-radius: 12px;
                background: transparent;
                color: #111827;
                text-align: left;
                padding: 0 14px;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
                font-weight: 500;
            }}
            #sidebarCategoryRow:checked {{
                background: #eaf0fb;
                color: #0f172a;
                border-color: #d6e1f4;
                border-right: 4px solid #2f66b3;
            }}
            #sidebarCategoryRow:hover {{
                background: #f0f4fa;
                color: #111827;
                border-color: #e0e8f3;
            }}
            #sidebarCategoryRow:checked:hover {{
                background: #e6eefb;
                color: #0f172a;
            }}
            #sidebarEmptyLabel {{
                color: #1f2937;
                font-size: 12px;
                font-weight: 400;
                padding: 10px 8px;
            }}
            #sidebarCategoryScrollArea,
            #sidebarCategoryViewport,
            #sidebarCategoryContent {{
                background: {sidebar_bg};
                border: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QScrollArea > QWidget > QWidget {{
                background: {sidebar_bg};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            """.format(
                sidebar_bg=sidebar_bg,
                sidebar_border=sidebar_border,
                tab_state_bg=tab_state_bg,
            )
        )

    def _resolve_sidebar_background_colors(self) -> tuple[str, str]:
        """Return sidebar background and border colors from the active window background."""
        host_window = self.window()
        base_color = QColor(getattr(host_window, "window_bg", ""))
        if not base_color.isValid():
            base_color = self.palette().color(self.backgroundRole())
        return compute_sidebar_background_colors(base_color)

    def refresh_background_style(self) -> None:
        """Recompute and apply sidebar colors from the current host-window background."""
        self._apply_style()
