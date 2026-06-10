"""Markdown formatting helpers and toolbar for the note editor."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPlainTextEdit,
    QToolButton,
    QWidget,
)

from continuum.ui.theme_palette import ThemePalette

FONT_FAMILIES = ["Segoe UI", "Georgia", "Cambria", "Arial", "Consolas", "Courier New"]
FONT_SIZES = [13, 14, 15, 16, 18, 20, 24]


def wrap_selection(editor: QPlainTextEdit, before: str, after: str = "") -> None:
    cursor = editor.textCursor()
    if not cursor.hasSelection():
        pos = cursor.position()
        cursor.insertText(f"{before}text{after}")
        cursor.setPosition(pos + len(before))
        cursor.setPosition(pos + len(before) + 4, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
    else:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        selected = cursor.selectedText().replace("\u2029", "\n")
        cursor.insertText(f"{before}{selected}{after}")
        cursor.setPosition(start + len(before))
        cursor.setPosition(end + len(before), QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
    editor.setFocus()


def prefix_lines(editor: QPlainTextEdit, prefix: str) -> None:
    cursor = editor.textCursor()
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    doc = editor.document()
    start_block = doc.findBlock(start).blockNumber()
    end_block = doc.findBlock(end).blockNumber()
    cursor.beginEditBlock()
    for block_num in range(start_block, end_block + 1):
        block = doc.findBlockByNumber(block_num)
        c = QTextCursor(block)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.insertText(prefix)
    cursor.endEditBlock()
    editor.setFocus()


class MarkdownToolBar(QWidget):
    """Formatting controls — inserts Markdown around the selection."""

    def __init__(self, editor: QPlainTextEdit, parent=None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._palette: ThemePalette | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        specs = [
            ("B", "Bold (Ctrl+B)", lambda: wrap_selection(self._editor, "**", "**"), True),
            ("I", "Italic (Ctrl+I)", lambda: wrap_selection(self._editor, "*", "*"), True),
            ("S", "Strikethrough", lambda: wrap_selection(self._editor, "~~", "~~"), False),
            ("H1", "Heading 1", lambda: prefix_lines(self._editor, "# "), False),
            ("H2", "Heading 2", lambda: prefix_lines(self._editor, "## "), False),
            ("•", "Bullet list", lambda: prefix_lines(self._editor, "- "), False),
            ("1.", "Numbered list", lambda: prefix_lines(self._editor, "1. "), False),
            ("</>", "Code", lambda: wrap_selection(self._editor, "`", "`"), False),
            ("[[", "Wiki link", lambda: wrap_selection(self._editor, "[[", "]]"), False),
        ]
        self._buttons: list[QToolButton] = []
        for label, tip, action, bold in specs:
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 32)
            if bold:
                font = btn.font()
                font.setBold(True)
                btn.setFont(font)
            btn.clicked.connect(action)
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addSpacing(8)
        self._font_combo = QComboBox()
        self._font_combo.addItems(FONT_FAMILIES)
        self._font_combo.setFixedWidth(120)
        self._font_combo.currentTextChanged.connect(self._on_font_family)
        layout.addWidget(self._font_combo)

        self._size_combo = QComboBox()
        self._size_combo.addItems([str(s) for s in FONT_SIZES])
        self._size_combo.setCurrentText("15")
        self._size_combo.setFixedWidth(52)
        self._size_combo.currentTextChanged.connect(self._on_font_size)
        layout.addWidget(self._size_combo)

        layout.addStretch()

        QShortcut(QKeySequence("Ctrl+B"), self._editor, lambda: wrap_selection(self._editor, "**", "**"))
        QShortcut(QKeySequence("Ctrl+I"), self._editor, lambda: wrap_selection(self._editor, "*", "*"))
        QShortcut(QKeySequence("Ctrl+U"), self._editor, lambda: wrap_selection(self._editor, "~~", "~~"))

    def _on_font_family(self, family: str) -> None:
        font = self._editor.font()
        font.setFamily(family)
        self._editor.setFont(font)

    def _on_font_size(self, size: str) -> None:
        try:
            pt = int(size)
        except ValueError:
            return
        font = self._editor.font()
        font.setPointSize(pt)
        self._editor.setFont(font)

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        style = f"""
            QToolButton {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid {p.border_subtle};
                border-radius: 6px;
                font-size: 12px;
            }}
            QToolButton:hover {{
                background: {p.accent_subtle};
                color: {p.accent_text};
                border-color: {p.accent};
            }}
            QToolButton:pressed {{
                background: {p.bg_elevated};
            }}
            QComboBox {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid {p.border_subtle};
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 28px;
            }}
            QComboBox:hover {{
                border-color: {p.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """
        self.setStyleSheet(style)
        for btn in self._buttons:
            btn.setStyleSheet(style)


def style_plain_editor(editor: QPlainTextEdit, p: ThemePalette) -> None:
    editor.setObjectName("noteBody")
    editor.setTabStopDistance(28)
    editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    font = QFont("Segoe UI", 15)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    editor.setFont(font)
    editor.setStyleSheet(f"""
        QPlainTextEdit#noteBody {{
            background: {p.bg_tertiary};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 10px;
            padding: 16px 18px;
            selection-background-color: {p.selection};
            selection-color: {p.text_primary};
        }}
        QPlainTextEdit#noteBody:focus {{
            border: 2px solid {p.accent};
            padding: 15px 17px;
        }}
    """)
