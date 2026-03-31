"""Top-button layout, measurement, and floating-row rebuild helpers."""

from PyQt5.QtCore import QPoint, QSize, QTimer, Qt
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from new_gui.ui.icon_factory import build_panel_stack_icon
from new_gui.ui.top_button_styles import build_neutral_top_button_style
from new_gui.ui.builders.top_button_specs import (
    DEFAULT_TOP_BUTTON_IDS,
    ROW1_BUTTON_SPACING,
    ROW2_COMPACT_SPACING,
    ROW2_NEUTRAL_PADDING_CANDIDATES,
    TOP_BUTTON_DEFINITIONS,
    TOP_BUTTON_MENU_ROW_Y_OFFSET,
    TOP_BUTTON_PANEL_ROW_Y_OFFSET,
    TOP_BUTTON_STYLE_SHEETS,
    normalize_visible_top_buttons,
)


def rebuild_top_action_buttons(window) -> None:
    """Rebuild the floating top-button container from the current visibility state."""
    visible_button_ids = normalize_visible_top_buttons(
        getattr(window, "_visible_top_buttons", DEFAULT_TOP_BUTTON_IDS)
    )

    existing_container = getattr(window, "_top_button_container", None)
    if existing_container is not None:
        existing_container.deleteLater()

    button_container = QWidget(window)
    button_container.setAttribute(Qt.WA_TranslucentBackground, True)
    button_container.setStyleSheet("background: transparent; border: none;")

    container_layout = QVBoxLayout(button_container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(8)

    visible_definitions = [
        definition for definition in TOP_BUTTON_DEFINITIONS if definition["id"] in visible_button_ids
    ]
    row1_definitions = [definition for definition in visible_definitions if definition["preferred_row"] == 1]
    row2_definitions = [definition for definition in visible_definitions if definition["preferred_row"] == 2]

    row1_widget = None
    row2_widget = None
    row1_width = 0

    if row1_definitions:
        row1_widget = _build_top_button_row_widget(window, row1_definitions, row_role="row1")
        container_layout.addWidget(row1_widget)
        row1_width = row1_widget.sizeHint().width()
    if row2_definitions:
        row2_widget = _build_top_button_row_widget(
            window,
            row2_definitions,
            row_role="row2",
            target_width=row1_width or None,
        )
        container_layout.addWidget(row2_widget)

    button_container.adjustSize()
    window._top_button_container = button_container
    window.buttons_row1 = [definition["label"].lower() for definition in row1_definitions]
    window.buttons_row2 = [definition["label"].lower() for definition in row2_definitions]
    window._top_button_row_count = container_layout.count()

    placeholder = getattr(window, "_top_button_placeholder", None)
    if placeholder is not None:
        reserved_width = max(
            row1_widget.sizeHint().width() if row1_widget is not None else 0,
            row2_widget.sizeHint().width() if row2_widget is not None else 0,
        )
        if reserved_width > 0:
            placeholder.setFixedWidth(reserved_width)
            placeholder.setFixedHeight(0)
        else:
            placeholder.setFixedSize(0, 0)

    button_container.setVisible(bool(visible_definitions))
    _update_top_panel_button_spacing(window, extra_bottom=0)
    if hasattr(window, "top_panel"):
        window.top_panel.updateGeometry()
        window.top_panel.adjustSize()

    QTimer.singleShot(0, window._position_top_action_buttons)


def _measure_button_width_from_style(label: str, style_sheet: str) -> int:
    """Return the polished size hint width for one styled top action button."""
    button = QPushButton(label)
    button.setStyleSheet(style_sheet)
    button.ensurePolished()
    return button.sizeHint().width()


def _measure_button_height_from_style(label: str, style_sheet: str) -> int:
    """Return the polished size hint height for one styled top action button."""
    button = QPushButton(label)
    button.setStyleSheet(style_sheet)
    button.ensurePolished()
    return button.sizeHint().height()


def _measure_button_width(label: str, style_key: str) -> int:
    """Return the polished size hint width for one predefined style."""
    return _measure_button_width_from_style(label, TOP_BUTTON_STYLE_SHEETS[style_key])


def _measure_button_height(label: str, style_key: str) -> int:
    """Return the polished size hint height for one predefined style."""
    return _measure_button_height_from_style(label, TOP_BUTTON_STYLE_SHEETS[style_key])


def _fit_button_widths_to_target(base_widths, min_widths, target_width: int, spacing: int):
    """Shrink widths just enough to fit the requested row width."""
    fitted_widths = dict(base_widths or {})
    if not fitted_widths or not target_width:
        return fitted_widths

    total_width = sum(fitted_widths.values()) + spacing * max(0, len(fitted_widths) - 1)
    overflow = total_width - target_width
    if overflow <= 0:
        return fitted_widths

    width_order = sorted(
        fitted_widths.keys(),
        key=lambda button_id: (
            fitted_widths[button_id] - min_widths.get(button_id, fitted_widths[button_id]),
            fitted_widths[button_id],
        ),
        reverse=True,
    )

    while overflow > 0:
        changed = False
        for button_id in width_order:
            minimum_width = min_widths.get(button_id, fitted_widths[button_id])
            if fitted_widths[button_id] <= minimum_width:
                continue
            fitted_widths[button_id] -= 1
            overflow -= 1
            changed = True
            if overflow <= 0:
                break
        if not changed:
            break

    return fitted_widths


def _build_row2_neutral_style(horizontal_padding: int) -> str:
    """Return the row2 button style with adjustable horizontal padding."""
    return build_neutral_top_button_style(horizontal_padding=horizontal_padding)


def _build_top_icon_toggle_style() -> str:
    """Return the stylesheet used by the top-left icon-only toggle button."""
    return """
        QPushButton {
            background-color: #181818;
            border: 1px solid #2b2b2b;
            border-radius: 6px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: #363636;
            border: 1px solid #727272;
        }
        QPushButton:pressed {
            background-color: #303030;
        }
        QPushButton:checked {
            background-color: #222222;
            border: 1px solid #4a4a4a;
        }
        QPushButton:checked:hover {
            background-color: #3a3a3a;
            border: 1px solid #7a7a7a;
        }
    """


def _build_visual_experiment_button(window) -> QPushButton:
    """Return a left-side icon toggle button for the terminal panel."""
    button = QPushButton("")
    button.setCheckable(True)
    button.setChecked(False)
    button.setCursor(Qt.PointingHandCursor)
    button.setFixedSize(34, 34)
    button.setIcon(build_panel_stack_icon(size=18))
    button.setIconSize(QSize(18, 18))
    button.setStyleSheet(_build_top_icon_toggle_style())
    button.setToolTip("Toggle terminal panel")
    button.toggled.connect(lambda checked: window.toggle_terminal_output_panel())
    window._top_panel_terminal_toggle_button = button
    return button


def _get_fixed_top_button_height() -> int:
    """Return one shared button height for both top-button rows."""
    measured_heights = []

    for definition in TOP_BUTTON_DEFINITIONS:
        style_key = definition["style"]
        if style_key in TOP_BUTTON_STYLE_SHEETS:
            measured_heights.append(_measure_button_height(definition["label"], style_key))

    for style_key in ("secondary_compact", "secondary_tight"):
        measured_heights.extend(
            _measure_button_height(definition["label"], style_key)
            for definition in TOP_BUTTON_DEFINITIONS
            if definition["preferred_row"] == 2
        )

    return max(measured_heights or [29])


def _get_fixed_row2_layout(target_width: int = None):
    """Return the stable row2 layout metrics based on the full row2 button set."""
    full_row2_definitions = [
        definition for definition in TOP_BUTTON_DEFINITIONS if definition["preferred_row"] == 2
    ]
    if not full_row2_definitions:
        return {
            "style_sheet": _build_row2_neutral_style(12),
            "spacing": ROW2_COMPACT_SPACING,
            "button_widths": {},
        }

    spacing = ROW2_COMPACT_SPACING
    chosen_style_sheet = _build_row2_neutral_style(ROW2_NEUTRAL_PADDING_CANDIDATES[0])
    base_widths = {}

    for candidate_padding in ROW2_NEUTRAL_PADDING_CANDIDATES:
        candidate_style_sheet = _build_row2_neutral_style(candidate_padding)
        candidate_widths = {
            definition["id"]: _measure_button_width_from_style(
                definition["label"],
                candidate_style_sheet,
            )
            for definition in full_row2_definitions
        }
        candidate_total_width = sum(candidate_widths.values()) + spacing * max(0, len(candidate_widths) - 1)
        chosen_style_sheet = candidate_style_sheet
        base_widths = candidate_widths
        if not target_width or candidate_total_width <= target_width:
            break

    min_widths = {
        definition["id"]: _measure_button_width(definition["label"], "secondary_tight")
        for definition in full_row2_definitions
    }

    if target_width:
        candidate_total_width = sum(base_widths.values()) + spacing * max(0, len(base_widths) - 1)
        if candidate_total_width <= target_width:
            return {
                "style_sheet": chosen_style_sheet,
                "spacing": spacing,
                "button_widths": dict(base_widths),
            }

        return {
            "style_sheet": chosen_style_sheet,
            "spacing": spacing,
            "button_widths": _fit_button_widths_to_target(
                base_widths,
                min_widths,
                target_width,
                spacing,
            ),
        }

    return {
        "style_sheet": chosen_style_sheet,
        "spacing": spacing,
        "button_widths": dict(base_widths),
    }


def _build_top_button_row_widget(window, row_definitions, row_role: str, target_width: int = None):
    """Build a single row of visible top action buttons."""
    row_widget = QWidget()
    row_widget.setAttribute(Qt.WA_TranslucentBackground, True)
    row_widget.setStyleSheet("background: transparent; border: none;")
    row_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(ROW1_BUTTON_SPACING if row_role == "row1" else ROW2_COMPACT_SPACING)
    row2_layout = _get_fixed_row2_layout(target_width) if row_role == "row2" else None
    fixed_button_height = _get_fixed_top_button_height()
    if row2_layout is not None:
        row_layout.setSpacing(row2_layout["spacing"])

    if row_role == "row1":
        row_layout.addWidget(_build_visual_experiment_button(window))

    for definition in row_definitions:
        button = QPushButton(definition["label"])
        style_key = definition["style"]
        if row_role == "row2" and style_key == "neutral":
            button.setStyleSheet(row2_layout["style_sheet"])
        else:
            button.setStyleSheet(TOP_BUTTON_STYLE_SHEETS[style_key])
        button.setFixedHeight(fixed_button_height)
        if row2_layout is not None:
            button.setFixedWidth(
                row2_layout["button_widths"].get(definition["id"], button.sizeHint().width())
            )
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button.clicked.connect(lambda _, callback=definition["callback"]: callback(window))
        row_layout.addWidget(button)

    row_widget.adjustSize()
    return row_widget


def _update_top_panel_button_spacing(window, extra_bottom: int) -> None:
    """Reserve vertical room for a second floating button row without stretching row1."""
    if not hasattr(window, "top_panel") or window.top_panel.layout() is None:
        return
    left, top, right, bottom = getattr(window, "_top_panel_base_margins", (16, 8, 16, 8))
    window.top_panel.layout().setContentsMargins(left, top, right, bottom + max(0, extra_bottom))


def get_top_button_anchor_y(window) -> int:
    """Return the top Y position for the floating top-button container."""
    top_panel_top = window.top_panel.mapTo(window, QPoint(0, 0)).y() if hasattr(window, "top_panel") else 0
    menu_top = window.menu_bar.geometry().top() if hasattr(window, "menu_bar") else 0

    has_row1 = bool(getattr(window, "buttons_row1", []))
    has_row2 = bool(getattr(window, "buttons_row2", []))
    if has_row1 and has_row2:
        return menu_top + TOP_BUTTON_MENU_ROW_Y_OFFSET
    return top_panel_top + TOP_BUTTON_PANEL_ROW_Y_OFFSET
