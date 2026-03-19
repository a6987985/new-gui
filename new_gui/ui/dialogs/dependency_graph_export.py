"""Export helpers for the dependency graph dialog."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QFileDialog

from new_gui.config.settings import logger


class DependencyGraphExportMixin:
    """Provide export helpers for the dependency graph dialog shell."""

    def export_png(self):
        """Export the current graph scene to a PNG file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Graph",
            "dependency_graph.png",
            "PNG Files (*.png)",
        )
        if not file_path:
            return

        rect = self.scene.itemsBoundingRect()
        image = QImage(int(rect.width()) + 100, int(rect.height()) + 100, QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter)
        painter.end()

        image.save(file_path)
        logger.info(f"Graph exported to: {file_path}")
