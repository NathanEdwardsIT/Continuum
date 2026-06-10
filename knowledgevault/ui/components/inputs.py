"""Search and text inputs."""

from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

from knowledgevault.ui.theme_palette import ThemePalette


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search…", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("searchField")
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(42)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLineEdit#searchField {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid transparent;
                border-radius: 21px;
                padding: 0 18px;
                font-size: 14px;
            }}
            QLineEdit#searchField:focus {{
                background: {p.bg_elevated};
                border: 1px solid {p.accent};
            }}
        """)
