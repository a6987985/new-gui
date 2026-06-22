"""Small icon builders for lightweight in-app action buttons."""

from __future__ import annotations

import re

from PyQt5.QtCore import QByteArray, QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF

try:
    from PyQt5.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover - fallback only used when QtSvg is unavailable.
    QSvgRenderer = None


_LINK_02_SVG_TEMPLATE = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M10 13C10.6667 13.6667 11.5556 14 12.6667 14H15C17.7614 14 20 11.7614 20 9C20 6.23858 17.7614 4 15 4H12.6667C9.90524 4 7.66667 6.23858 7.66667 9"
        stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M14 11C13.3333 10.3333 12.4444 10 11.3333 10H9C6.23858 10 4 12.2386 4 15C4 17.7614 6.23858 20 9 20H11.3333C14.0948 20 16.3333 17.7614 16.3333 15"
        stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

_STACK_PANEL_SVG_TEMPLATE = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="4.5" y="4.5" width="15" height="15" rx="1.5" stroke="{stroke}" stroke-width="1.8"/>
  <path d="M5.5 13.2H18.5" stroke="{stroke}" stroke-width="1.8" stroke-linecap="round"/>
  {bottom_fill}
</svg>
"""

_SIDE_PANEL_SVG_TEMPLATE = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="4.5" y="4.5" width="15" height="15" rx="1.5" stroke="{stroke}" stroke-width="1.8"/>
  <path d="M10.8 5.3V18.7" stroke="{stroke}" stroke-width="1.8" stroke-linecap="round"/>
  {left_fill}
</svg>
"""

_SEARCH_SVG_TEMPLATE = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10.5" cy="10.5" r="4.8" stroke="{color}" stroke-width="1.8"/>
  <path d="M14.2 14.2L18.6 18.6" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
</svg>
"""

_TERMINAL_FILL_SVG_TEMPLATES = {
    "expand": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M13.5 10.5L18.2 5.8" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M14.8 5.8H18.2V9.2" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M10.5 13.5L5.8 18.2" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M5.8 14.8V18.2H9.2" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
    "restore": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M18.2 5.8L13.5 10.5" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M13.5 7.1V10.5H16.9" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M5.8 18.2L10.5 13.5" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M7.1 13.5H10.5V16.9" stroke="{color}" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
}

_STATUS_ICON_SVG_TEMPLATES = {
    "circle-check": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
  <path d="M8.9 12.1L11.2 14.4L15.5 10.1" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
    "circle-play": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
  <path d="M10.1 9.4L14.6 12L10.1 14.6V9.4Z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>
</svg>
""",
    "circle-x": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
  <path d="M9.4 9.4L14.6 14.6M14.6 9.4L9.4 14.6" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
</svg>
""",
    "circle-minus": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
  <path d="M8.7 12H15.3" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
</svg>
""",
    "clock-3": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
  <path d="M12 8.2V12H15.4" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
    "circle-dashed": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8" stroke-dasharray="2.2 3"/>
</svg>
""",
}

_SIDEBAR_CATEGORY_ICON_SVG_TEMPLATES = {
    "grid-panel": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="4.8" y="4.8" width="14.4" height="14.4" rx="2.2" stroke="{color}" stroke-width="1.7"/>
  <path d="M12 5.8V18.2M5.8 12H18.2" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
</svg>
""",
    "layout-grid": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="4.8" y="4.8" width="5.4" height="5.4" rx="1.1" stroke="{color}" stroke-width="1.7"/>
  <rect x="13.8" y="4.8" width="5.4" height="5.4" rx="1.1" stroke="{color}" stroke-width="1.7"/>
  <rect x="4.8" y="13.8" width="5.4" height="5.4" rx="1.1" stroke="{color}" stroke-width="1.7"/>
  <rect x="13.8" y="13.8" width="5.4" height="5.4" rx="1.1" stroke="{color}" stroke-width="1.7"/>
</svg>
""",
    "target": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10.5" cy="10.5" r="5.2" stroke="{color}" stroke-width="1.7"/>
  <path d="M10.5 7.8V13.2M7.8 10.5H13.2" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M14.2 14.2L18.5 18.5" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
</svg>
""",
    "trend-scan": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4.8 15.9L8.5 12.2L11.2 14.5L15.4 9.1" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="17.6" cy="16.3" r="3.0" stroke="{color}" stroke-width="1.7"/>
  <path d="M19.8 18.5L21.2 19.9" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
</svg>
""",
    "route-split": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 4.8V10.2M12 10.2L7.2 15M12 10.2L16.8 15M7.2 15V19.2M16.8 15V19.2" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M10.3 6.5L12 4.8L13.7 6.5M5.7 17.5L7.2 19.2L8.7 17.5M15.3 17.5L16.8 19.2L18.3 17.5" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
    "spark-route": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M7 17L13.1 10.9" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M12.5 7.2L16.8 11.5" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M15.7 6.1V3.9M15.7 6.1H13.5M15.7 6.1H17.9" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M6.1 12.3V10.5M6.1 12.3H4.3M6.1 12.3H7.9" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M15.6 11.4L18.7 14.5" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
</svg>
""",
    "branch-route": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="6.4" cy="7.2" r="1.4" stroke="{color}" stroke-width="1.7"/>
  <circle cx="6.4" cy="16.8" r="1.4" stroke="{color}" stroke-width="1.7"/>
  <circle cx="12.3" cy="12" r="1.4" stroke="{color}" stroke-width="1.7"/>
  <path d="M7.8 7.2H10C11.3 7.2 12.3 8.2 12.3 9.5V12M7.8 16.8H10C11.3 16.8 12.3 15.8 12.3 14.5V12M13.7 12H19.1" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M17.3 10.2L19.1 12L17.3 13.8" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
}


def build_terminal_follow_run_icon(size: int = 16) -> QIcon:
    """Return a two-state link icon used by the terminal follow-run toggle."""
    icon = QIcon()
    icon.addPixmap(_render_link_icon_pixmap("#7b8794", size), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_render_link_icon_pixmap("#1f6fb2", size), QIcon.Normal, QIcon.On)
    icon.addPixmap(_render_link_icon_pixmap("#7b8794", size), QIcon.Active, QIcon.Off)
    icon.addPixmap(_render_link_icon_pixmap("#1f6fb2", size), QIcon.Active, QIcon.On)
    return icon


def build_terminal_content_fill_icon(size: int = 16) -> QIcon:
    """Return the black-and-white terminal content-fill toggle icon."""
    icon = QIcon()
    off_pixmap = _render_terminal_fill_icon_pixmap("expand", "#111827", size)
    off_active_pixmap = _render_terminal_fill_icon_pixmap("expand", "#000000", size)
    on_pixmap = _render_terminal_fill_icon_pixmap("restore", "#ffffff", size)
    icon.addPixmap(off_pixmap, QIcon.Normal, QIcon.Off)
    icon.addPixmap(off_active_pixmap, QIcon.Active, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Normal, QIcon.On)
    icon.addPixmap(on_pixmap, QIcon.Active, QIcon.On)
    icon.addPixmap(on_pixmap, QIcon.Selected, QIcon.On)
    return icon


def build_panel_stack_icon(size: int = 16) -> QIcon:
    """Return a two-state panel icon for the top-button visual experiment."""
    icon = QIcon()
    off_pixmap = _render_stack_panel_icon_pixmap(False, size)
    on_pixmap = _render_stack_panel_icon_pixmap(True, size)
    icon.addPixmap(off_pixmap, QIcon.Normal, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Normal, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Active, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Active, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Selected, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Selected, QIcon.On)
    return icon


def build_side_panel_icon(size: int = 16) -> QIcon:
    """Return a two-state side-panel icon for left-bar placeholder toggle."""
    icon = QIcon()
    off_pixmap = _render_side_panel_icon_pixmap(False, size)
    on_pixmap = _render_side_panel_icon_pixmap(True, size)
    icon.addPixmap(off_pixmap, QIcon.Normal, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Normal, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Active, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Active, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Selected, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Selected, QIcon.On)
    return icon


def build_search_icon(size: int = 14) -> QIcon:
    """Return a compact two-state magnifier icon for the run selector."""
    icon = QIcon()
    icon.addPixmap(_render_search_icon_pixmap("#6B7280", size), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_render_search_icon_pixmap("#374151", size), QIcon.Active, QIcon.Off)
    icon.addPixmap(_render_search_icon_pixmap("#1F2937", size), QIcon.Selected, QIcon.Off)
    return icon


def build_sidebar_category_icon(category_text: str, size: int = 18) -> QIcon:
    """Return a two-state icon tailored for one sidebar category label."""
    icon = QIcon()
    icon_name = _resolve_sidebar_category_icon_name(category_text)
    off_pixmap = _render_sidebar_category_icon_pixmap(icon_name, "#5E6E84", size, category_text)
    on_pixmap = _render_sidebar_category_icon_pixmap(icon_name, "#2C5FAA", size, category_text)
    icon.addPixmap(off_pixmap, QIcon.Normal, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Normal, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Active, QIcon.Off)
    icon.addPixmap(on_pixmap, QIcon.Active, QIcon.On)
    icon.addPixmap(on_pixmap, QIcon.Selected, QIcon.On)
    icon.addPixmap(off_pixmap, QIcon.Selected, QIcon.Off)
    return icon


def build_status_icon_pixmap(icon_name: str, color: str, size: int = 14) -> QPixmap:
    """Return one Lucide-style status icon pixmap for badges and graph views."""
    normalized_icon_name = (icon_name or "").strip().lower()
    if not normalized_icon_name:
        return QPixmap()

    if QSvgRenderer is not None and normalized_icon_name in _STATUS_ICON_SVG_TEMPLATES:
        svg = _STATUS_ICON_SVG_TEMPLATES[normalized_icon_name].format(color=color).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    return _render_status_icon_pixmap_fallback(normalized_icon_name, color, size)


def _render_link_icon_pixmap(color: str, size: int) -> QPixmap:
    """Render one link-style icon pixmap from inline SVG or a simple fallback."""
    if QSvgRenderer is not None:
        svg = _LINK_02_SVG_TEMPLATE.format(color=color).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    # Fallback: draw a simple linked-chain glyph using arcs.
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    half = size / 2.0
    painter.drawArc(int(size * 0.08), int(size * 0.18), int(half), int(size * 0.46), 35 * 16, 290 * 16)
    painter.drawArc(int(size * 0.42), int(size * 0.36), int(half), int(size * 0.46), 215 * 16, 290 * 16)
    painter.end()
    return pixmap


def _render_terminal_fill_icon_pixmap(icon_name: str, color: str, size: int) -> QPixmap:
    """Render one terminal fill-state icon pixmap from SVG or painter fallback."""
    if QSvgRenderer is not None:
        svg = _TERMINAL_FILL_SVG_TEMPLATES[icon_name].format(
            color=color
        ).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    if icon_name == "restore":
        painter.drawLine(
            int(size * 0.78), int(size * 0.22), int(size * 0.56), int(size * 0.44)
        )
        painter.drawLine(
            int(size * 0.56), int(size * 0.30), int(size * 0.56), int(size * 0.44)
        )
        painter.drawLine(
            int(size * 0.70), int(size * 0.44), int(size * 0.56), int(size * 0.44)
        )
        painter.drawLine(
            int(size * 0.22), int(size * 0.78), int(size * 0.44), int(size * 0.56)
        )
        painter.drawLine(
            int(size * 0.30), int(size * 0.56), int(size * 0.44), int(size * 0.56)
        )
        painter.drawLine(
            int(size * 0.44), int(size * 0.70), int(size * 0.44), int(size * 0.56)
        )
    else:
        painter.drawLine(
            int(size * 0.56), int(size * 0.44), int(size * 0.78), int(size * 0.22)
        )
        painter.drawLine(
            int(size * 0.64), int(size * 0.22), int(size * 0.78), int(size * 0.22)
        )
        painter.drawLine(
            int(size * 0.78), int(size * 0.36), int(size * 0.78), int(size * 0.22)
        )
        painter.drawLine(
            int(size * 0.44), int(size * 0.56), int(size * 0.22), int(size * 0.78)
        )
        painter.drawLine(
            int(size * 0.22), int(size * 0.64), int(size * 0.22), int(size * 0.78)
        )
        painter.drawLine(
            int(size * 0.36), int(size * 0.78), int(size * 0.22), int(size * 0.78)
        )
    painter.end()
    return pixmap


def _render_stack_panel_icon_pixmap(
    selected: bool,
    size: int,
    stroke: str = "#314154",
    fill: str = "#314154",
) -> QPixmap:
    """Render the panel-stack icon matching the requested selected state."""
    bottom_fill = ""
    if selected:
        bottom_fill = f'<rect x="5.4" y="13.9" width="13.2" height="4.7" rx="0.8" fill="{fill}"/>'

    if QSvgRenderer is not None:
        svg = _STACK_PANEL_SVG_TEMPLATE.format(
            stroke=stroke,
            bottom_fill=bottom_fill,
        ).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(stroke), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(int(size * 0.19), int(size * 0.19), int(size * 0.62), int(size * 0.62), 2, 2)
    painter.drawLine(int(size * 0.24), int(size * 0.55), int(size * 0.78), int(size * 0.55))
    if selected:
        painter.fillRect(int(size * 0.24), int(size * 0.58), int(size * 0.53), int(size * 0.18), QColor(fill))
    painter.end()
    return pixmap


def _render_side_panel_icon_pixmap(
    selected: bool,
    size: int,
    stroke: str = "#314154",
    fill: str = "#314154",
) -> QPixmap:
    """Render the side-panel icon matching the requested selected state."""
    left_fill = ""
    if selected:
        left_fill = f'<rect x="5.4" y="5.4" width="4.6" height="13.2" rx="0.8" fill="{fill}"/>'

    if QSvgRenderer is not None:
        svg = _SIDE_PANEL_SVG_TEMPLATE.format(
            stroke=stroke,
            left_fill=left_fill,
        ).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(stroke), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(int(size * 0.19), int(size * 0.19), int(size * 0.62), int(size * 0.62), 2, 2)
    divider_x = int(size * 0.44)
    painter.drawLine(divider_x, int(size * 0.24), divider_x, int(size * 0.78))
    if selected:
        painter.fillRect(int(size * 0.24), int(size * 0.24), int(size * 0.18), int(size * 0.53), QColor(fill))
    painter.end()
    return pixmap


def _render_search_icon_pixmap(color: str, size: int) -> QPixmap:
    """Render a search icon pixmap from inline SVG or a simple painter fallback."""
    if QSvgRenderer is not None:
        svg = _SEARCH_SVG_TEMPLATE.format(color=color).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    diameter = int(size * 0.5)
    offset = int(size * 0.14)
    painter.drawEllipse(offset, offset, diameter, diameter)
    painter.drawLine(
        int(size * 0.58),
        int(size * 0.58),
        int(size * 0.85),
        int(size * 0.85),
    )
    painter.end()
    return pixmap


def _resolve_sidebar_category_icon_name(category_text: str) -> str:
    """Choose one sidebar icon family from a category label."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (category_text or "").strip().lower()).strip()
    tokens = set(normalized.split())
    compact = normalized.replace(" ", "")

    if {"data", "prepare"} <= tokens:
        return "grid-panel"
    if "floorplan" in compact or {"floor", "plan"} <= tokens:
        return "layout-grid"
    if "place" in tokens:
        return "target"
    if "optcts" in compact or ("opt" in tokens and "cts" in tokens):
        return "trend-scan"
    if compact == "cts" or tokens == {"cts"}:
        return "clock-3"
    if "applymvreroute" in compact or ("apply" in tokens and "reroute" in tokens):
        return "branch-route"
    if "reroute" in compact:
        return "branch-route"
    if "optroute" in compact or ("opt" in tokens and "route" in tokens):
        return "spark-route"
    if "route" in compact:
        return "route-split"
    return "monogram"


def _render_sidebar_category_icon_pixmap(
    icon_name: str,
    color: str,
    size: int,
    category_text: str,
) -> QPixmap:
    """Render one sidebar category icon pixmap from SVG or a monogram fallback."""
    if icon_name == "clock-3":
        return build_status_icon_pixmap(icon_name, color, size)

    if QSvgRenderer is not None and icon_name in _SIDEBAR_CATEGORY_ICON_SVG_TEMPLATES:
        svg = _SIDEBAR_CATEGORY_ICON_SVG_TEMPLATES[icon_name].format(color=color).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    return _render_sidebar_monogram_pixmap(category_text, color, size)


def _render_sidebar_monogram_pixmap(category_text: str, color: str, size: int) -> QPixmap:
    """Render one compact outline badge with a short category monogram."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(color), 1.35, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    inset = max(1, int(size * 0.12))
    side = max(1, size - inset * 2)
    painter.drawRoundedRect(inset, inset, side, side, 3, 3)

    normalized = re.sub(r"[^A-Za-z0-9]+", " ", (category_text or "").strip()).strip()
    initials = "".join(part[:1] for part in normalized.split()[:2]).upper()
    initials = (initials or (normalized[:1].upper() if normalized else "S"))[:2]

    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(7, int(size * (0.4 if len(initials) == 1 else 0.3))))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, initials)
    painter.end()
    return pixmap


def _render_status_icon_pixmap_fallback(icon_name: str, color: str, size: int) -> QPixmap:
    """Draw one lightweight fallback when QtSvg is unavailable."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    margin = max(1, int(size * 0.14))
    diameter = max(1, size - margin * 2)
    if icon_name != "clock-3":
        if icon_name == "circle-dashed":
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
        painter.drawEllipse(margin, margin, diameter, diameter)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
    else:
        painter.drawEllipse(margin, margin, diameter, diameter)

    if icon_name == "circle-check":
        painter.drawLine(int(size * 0.36), int(size * 0.53), int(size * 0.48), int(size * 0.66))
        painter.drawLine(int(size * 0.48), int(size * 0.66), int(size * 0.7), int(size * 0.42))
    elif icon_name == "circle-play":
        points = [
            (int(size * 0.43), int(size * 0.36)),
            (int(size * 0.68), int(size * 0.5)),
            (int(size * 0.43), int(size * 0.64)),
        ]
        painter.drawPolygon(QPolygonF([QPointF(x_pos, y_pos) for x_pos, y_pos in points]))
    elif icon_name == "circle-x":
        painter.drawLine(int(size * 0.39), int(size * 0.39), int(size * 0.61), int(size * 0.61))
        painter.drawLine(int(size * 0.61), int(size * 0.39), int(size * 0.39), int(size * 0.61))
    elif icon_name == "circle-minus":
        painter.drawLine(int(size * 0.34), int(size * 0.5), int(size * 0.66), int(size * 0.5))
    elif icon_name == "clock-3":
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.5), int(size * 0.32))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.66), int(size * 0.5))

    painter.end()
    return pixmap
