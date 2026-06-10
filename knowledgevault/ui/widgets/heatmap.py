"""Activity heatmap widget — GitHub-style writing streak visualization."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from knowledgevault.services.insights_engine import DayActivity
from knowledgevault.ui.theme_palette import ThemePalette, get_palette
from knowledgevault.ui.theme_palette import ThemeId


class ActivityHeatmap(QWidget):
    """Renders a compact activity heatmap grid."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("heatmapWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(80)
        self._activity: list[DayActivity] = []
        self._palette = get_palette(ThemeId.STUDIO)
        self._cell = 10
        self._gap = 3

    def set_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self.update()

    def set_activity(self, activity: list[DayActivity]) -> None:
        self._activity = activity[-90:] if len(activity) > 90 else activity
        weeks = max(1, (len(self._activity) + 6) // 7)
        self.setFixedWidth(weeks * (self._cell + self._gap) + 16)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._activity:
            painter.setPen(QColor(self._palette.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No activity yet")
            return

        max_count = max((d.note_count for d in self._activity), default=1)
        base = QColor(self._palette.bg_tertiary)
        accent = QColor(self._palette.accent)

        x_offset = 8
        y_offset = 8
        for i, day in enumerate(self._activity):
            week = i // 7
            dow = i % 7
            x = x_offset + week * (self._cell + self._gap)
            y = y_offset + dow * (self._cell + self._gap)

            if day.note_count == 0:
                color = base
            else:
                intensity = 0.25 + 0.75 * (day.note_count / max_count)
                color = accent
                color.setAlphaF(intensity)

            rect = QRectF(x, y, self._cell, self._cell)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 2, 2)

        painter.end()
