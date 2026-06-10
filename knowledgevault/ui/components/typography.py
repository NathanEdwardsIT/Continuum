"""Typography primitives."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from knowledgevault.ui.theme_palette import ThemePalette


class H1(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("h1")

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#h1 {{
                font-size: 26px;
                font-weight: 700;
                color: {p.text_primary};
                letter-spacing: -0.6px;
                background: transparent;
            }}
        """)


class H2(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("h2")

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#h2 {{
                font-size: 15px;
                font-weight: 600;
                color: {p.text_primary};
                letter-spacing: -0.2px;
                background: transparent;
            }}
        """)


class Body(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("body")
        self.setWordWrap(True)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#body {{
                font-size: 13px;
                color: {p.text_secondary};
                line-height: 1.5;
                background: transparent;
            }}
        """)


class Caption(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("caption")

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#caption {{
                font-size: 11px;
                color: {p.text_muted};
                background: transparent;
            }}
        """)


class Badge(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#badge {{
                font-size: 10px;
                font-weight: 700;
                color: {p.accent_text};
                background: {p.accent_subtle};
                padding: 3px 10px;
                border-radius: 8px;
            }}
        """)


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("sectionLabel")

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QLabel#sectionLabel {{
                font-size: 10px;
                font-weight: 700;
                color: {p.text_muted};
                letter-spacing: 1.6px;
                padding: 16px 4px 8px 4px;
                background: transparent;
            }}
        """)
