"""Elevated card surfaces with drop shadows."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget

from continuum.ui.theme_palette import ThemePalette


def _shadow(widget: QWidget, blur: int = 32, y: int = 6, alpha: int = 80) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class ElevatedCard(QWidget):
    """Card with shadow — the core surface primitive."""

    def __init__(self, parent=None, padding: int = 20, radius: int = 16) -> None:
        super().__init__(parent)
        self.setObjectName("elevatedCard")
        self._padding = padding
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(12)
        _shadow(self)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QWidget#elevatedCard {{
                background-color: {p.bg_card};
                border: 1px solid {p.glass_border};
                border-radius: 16px;
            }}
        """)


class GlassPanel(QWidget):
    """Lighter glass surface without heavy shadow."""

    def __init__(self, parent=None, padding: int = 16) -> None:
        super().__init__(parent)
        self.setObjectName("glassPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(10)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QWidget#glassPanel {{
                background-color: {p.glass_bg};
                border: 1px solid {p.glass_border};
                border-radius: 14px;
            }}
        """)
