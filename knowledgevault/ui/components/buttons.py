"""Designer-grade buttons with gradients."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from continuum.ui.theme_palette import ThemePalette


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primaryBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QPushButton#primaryBtn {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {p.accent}, stop:1 {p.accent_hover});
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#primaryBtn:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {p.accent_hover}, stop:1 {p.accent});
            }}
            QPushButton#primaryBtn:pressed {{
                background: {p.accent_hover};
            }}
        """)


class GhostButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("ghostBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QPushButton#ghostBtn {{
                background: transparent;
                color: {p.text_secondary};
                border: 1px solid {p.border};
                border-radius: 10px;
                padding: 7px 16px;
                font-weight: 500;
                font-size: 12px;
            }}
            QPushButton#ghostBtn:hover {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border-color: {p.border};
            }}
        """)


class NavButton(QPushButton):
    def __init__(self, text: str, icon: str = "", parent=None) -> None:
        label = f"  {icon}  {text}" if icon else f"  {text}"
        super().__init__(label, parent)
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QPushButton#navBtn {{
                text-align: left;
                background: transparent;
                color: {p.text_muted};
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#navBtn:hover {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
            }}
            QPushButton#navBtn:checked {{
                background: {p.accent_subtle};
                color: {p.accent_text};
                font-weight: 600;
            }}
        """)


class TabButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("tabBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)

    def apply_palette(self, p: ThemePalette) -> None:
        self.setStyleSheet(f"""
            QPushButton#tabBtn {{
                background: transparent;
                color: {p.text_muted};
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#tabBtn:hover {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
            }}
            QPushButton#tabBtn:checked {{
                background: {p.bg_elevated};
                color: {p.text_primary};
                font-weight: 600;
            }}
        """)
