"""Global QSS — structural styles; components handle their own surfaces."""

from __future__ import annotations

from knowledgevault.ui.theme_palette import ThemeId, ThemePalette, get_palette

Theme = ThemeId


def build_stylesheet(p: ThemePalette) -> str:
    return f"""
* {{
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {p.bg_primary};
}}

QDialog {{
    background-color: {p.bg_secondary};
    color: {p.text_primary};
}}

QWidget#shell {{
    background-color: {p.bg_primary};
}}

QWidget#sidebar {{
    background-color: {p.bg_secondary};
    border-right: 1px solid {p.border_subtle};
}}

QWidget#workspace {{
    background-color: {p.bg_primary};
}}

QWidget#inspector {{
    background-color: {p.bg_secondary};
    border-left: 1px solid {p.border_subtle};
}}

QWidget#topChrome {{
    background-color: {p.topbar};
    border-bottom: 1px solid {p.border_subtle};
}}

QStatusBar {{
    background: {p.bg_secondary};
    color: {p.text_muted};
    border-top: 1px solid {p.border_subtle};
    font-size: 11px;
    padding: 4px 12px;
}}

QMenu {{
    background: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 12px;
    padding: 6px;
    color: {p.text_secondary};
}}

QMenu::item {{
    padding: 8px 28px 8px 14px;
    border-radius: 8px;
}}

QMenu::item:selected {{
    background: {p.accent_subtle};
    color: {p.accent_text};
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 6px 2px;
}}

QScrollBar::handle:vertical {{
    background: {p.scrollbar};
    border-radius: 2px;
    min-height: 48px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QTreeWidget {{
    background: transparent;
    border: none;
    color: {p.text_secondary};
    font-size: 12px;
    outline: none;
}}

QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 8px;
    margin: 1px 0;
}}

QTreeWidget::item:hover {{
    background: {p.bg_tertiary};
}}

QTreeWidget::item:selected {{
    background: {p.accent_subtle};
    color: {p.accent_text};
}}

QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}

QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0;
    margin-bottom: 8px;
}}

QListWidget::item:selected {{
    background: transparent;
}}

QSplitter::handle {{
    background: {p.border_subtle};
    width: 1px;
}}

QComboBox {{
    background: {p.bg_tertiary};
    border: 1px solid {p.border_subtle};
    border-radius: 8px;
    padding: 6px 12px;
    color: {p.text_secondary};
    min-height: 28px;
}}

QComboBox QAbstractItemView {{
    background: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 8px;
    selection-background-color: {p.accent_subtle};
    color: {p.text_secondary};
}}

QPlainTextEdit, QTextBrowser {{
    background: transparent;
    border: none;
    color: {p.text_secondary};
    selection-background-color: {p.selection};
}}

QLineEdit#titleField {{
    background: transparent;
    border: none;
    font-size: 24px;
    font-weight: 700;
    color: {p.text_primary};
    padding: 0;
}}

QDateEdit {{
    background: {p.bg_tertiary};
    border: 1px solid {p.border_subtle};
    border-radius: 8px;
    padding: 6px 12px;
    color: {p.text_primary};
}}

QToolTip {{
    background: {p.bg_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 6px 10px;
}}
"""


def get_stylesheet(theme: ThemeId) -> str:
    return build_stylesheet(get_palette(theme))
