"""Central theme engine — applies designer system globally."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from knowledgevault.ui.theme_palette import ThemeId, ThemePalette, get_palette
from knowledgevault.ui.themes import get_stylesheet


class ThemeEngine:
    """Applies palette to the widget tree."""

    _instance: ThemeEngine | None = None

    def __init__(self) -> None:
        self.palette = get_palette(ThemeId.STUDIO)
        self.theme_id = ThemeId.STUDIO

    @classmethod
    def instance(cls) -> ThemeEngine:
        if cls._instance is None:
            cls._instance = ThemeEngine()
        return cls._instance

    def apply(self, root: QWidget, theme_id: ThemeId) -> ThemePalette:
        self.theme_id = theme_id
        self.palette = get_palette(theme_id)
        root.setStyleSheet(get_stylesheet(theme_id))
        self._walk(root, self.palette)
        return self.palette

    def _walk(self, widget: QWidget, p: ThemePalette) -> None:
        if hasattr(widget, "apply_palette"):
            widget.apply_palette(p)
        for child in widget.findChildren(QWidget):
            if hasattr(child, "apply_palette"):
                child.apply_palette(p)
