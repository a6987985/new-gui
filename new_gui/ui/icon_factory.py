"""Small icon builders for lightweight in-app action buttons."""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

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
    icon.addPixmap(_render_stack_panel_icon_pixmap(False, size), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_render_stack_panel_icon_pixmap(True, size), QIcon.Normal, QIcon.On)
    icon.addPixmap(_render_stack_panel_icon_pixmap(False, size, stroke="#FFFFFF"), QIcon.Active, QIcon.Off)
    icon.addPixmap(_render_stack_panel_icon_pixmap(True, size, stroke="#FFFFFF"), QIcon.Active, QIcon.On)
    return icon


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


def _render_stack_panel_icon_pixmap(selected: bool, size: int, stroke: str = "#F4F4F4") -> QPixmap:
    """Render the panel-stack icon matching the requested selected state."""
    bottom_fill = ""
    if selected:
        bottom_fill = '<rect x="5.4" y="13.9" width="13.2" height="4.7" rx="0.8" fill="#D9D9D9"/>'

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
        painter.fillRect(int(size * 0.24), int(size * 0.58), int(size * 0.53), int(size * 0.18), QColor("#D9D9D9"))
    painter.end()
    return pixmap
