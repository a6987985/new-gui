"""Small icon builders for lightweight in-app action buttons."""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, QPointF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

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


def build_terminal_follow_run_icon(size: int = 16) -> QIcon:
    """Return a two-state link icon used by the terminal follow-run toggle."""
    icon = QIcon()
    icon.addPixmap(_render_link_icon_pixmap("#7b8794", size), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_render_link_icon_pixmap("#1f6fb2", size), QIcon.Normal, QIcon.On)
    icon.addPixmap(_render_link_icon_pixmap("#7b8794", size), QIcon.Active, QIcon.Off)
    icon.addPixmap(_render_link_icon_pixmap("#1f6fb2", size), QIcon.Active, QIcon.On)
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
