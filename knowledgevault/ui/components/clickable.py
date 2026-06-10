"""Clickable card wrapper."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget

from knowledgevault.ui.components.card import ElevatedCard


class ClickableCard(ElevatedCard):
    clicked = Signal()

    def __init__(self, parent=None, padding: int = 16) -> None:
        super().__init__(parent, padding=padding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
