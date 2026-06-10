"""Markdown formatting helpers, smart editor, and toolbar for the note editor."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QWidget,
)

from continuum.ui.theme_palette import ThemePalette

FONT_FAMILIES = ["Segoe UI", "Georgia", "Cambria", "Arial", "Consolas", "Courier New"]
FONT_SIZES = [13, 14, 15, 16, 18, 20, 24]

_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s(.*)$")
_CHECKBOX_RE = re.compile(r"^(\s*)- \[([ xX])\] (.*)$")
_HEADING_RE = re.compile(r"^(\s*)(#{1,3})\s(.*)$")
_BLOCKQUOTE_RE = re.compile(r"^(\s*)> (.*)$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def selected_text(cursor: QTextCursor) -> str:
    return cursor.selectedText().replace("\u2029", "\n")


class LinkDialog(QDialog):
    """Prompt for hyperlink display text and URL."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str = "",
        url: str = "https://",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Hyperlink")
        layout = QFormLayout(self)
        self._text = QLineEdit(text)
        self._text.setPlaceholderText("Text shown in the note")
        self._url = QLineEdit(url)
        self._url.setPlaceholderText("https://example.com")
        layout.addRow("Display text", self._text)
        layout.addRow("URL", self._url)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, str]:
        return self._text.text().strip(), self._url.text().strip()


def wrap_selection(editor: QPlainTextEdit, before: str, after: str = "") -> None:
    cursor = editor.textCursor()
    if not cursor.hasSelection():
        pos = cursor.position()
        cursor.insertText(f"{before}text{after}")
        cursor.setPosition(pos + len(before))
        cursor.setPosition(pos + len(before) + 4, QTextCursor.MoveMode.KeepAnchor)
    else:
        start = cursor.selectionStart()
        text = selected_text(cursor)
        cursor.insertText(f"{before}{text}{after}")
        cursor.setPosition(start + len(before))
        cursor.setPosition(start + len(before) + len(text), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    editor.setFocus()


def prefix_lines(editor: QPlainTextEdit, prefix: str, *, toggle: bool = False) -> None:
    cursor = editor.textCursor()
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    doc = editor.document()
    start_block = doc.findBlock(start).blockNumber()
    end_block = doc.findBlock(end).blockNumber()
    cursor.beginEditBlock()
    for block_num in range(start_block, end_block + 1):
        block = doc.findBlockByNumber(block_num)
        text = block.text()
        c = QTextCursor(block)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        if toggle and text.startswith(prefix):
            c.insertText(text[len(prefix):])
        elif not text.startswith(prefix):
            c.insertText(prefix + text)
    cursor.endEditBlock()
    editor.setTextCursor(cursor)
    editor.setFocus()


def indent_lines(editor: QPlainTextEdit, spaces: int = 2) -> None:
    prefix = " " * spaces
    cursor = editor.textCursor()
    anchor, pos = cursor.anchor(), cursor.position()
    start, end = min(anchor, pos), max(anchor, pos)
    has_selection = cursor.hasSelection()
    doc = editor.document()
    start_block = doc.findBlock(start).blockNumber()
    end_block = doc.findBlock(end).blockNumber()
    cursor.beginEditBlock()
    indented = 0
    for block_num in range(start_block, end_block + 1):
        block = doc.findBlockByNumber(block_num)
        if not block.text().strip():
            continue
        c = QTextCursor(block)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.insertText(prefix)
        indented += 1
    cursor.endEditBlock()
    new_cursor = editor.textCursor()
    if has_selection:
        new_cursor.setPosition(start)
        new_cursor.setPosition(end + indented * spaces, QTextCursor.MoveMode.KeepAnchor)
    else:
        new_cursor.setPosition(pos + (spaces if indented else 0))
    editor.setTextCursor(new_cursor)
    editor.setFocus()


def outdent_lines(editor: QPlainTextEdit, spaces: int = 2) -> None:
    prefix = " " * spaces
    cursor = editor.textCursor()
    anchor, pos = cursor.anchor(), cursor.position()
    start, end = min(anchor, pos), max(anchor, pos)
    has_selection = cursor.hasSelection()
    doc = editor.document()
    start_block = doc.findBlock(start).blockNumber()
    end_block = doc.findBlock(end).blockNumber()
    cursor.beginEditBlock()
    removed = 0
    for block_num in range(start_block, end_block + 1):
        block = doc.findBlockByNumber(block_num)
        text = block.text()
        if text.startswith(prefix):
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            c.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                spaces,
            )
            c.removeSelectedText()
            removed += 1
    cursor.endEditBlock()
    new_cursor = editor.textCursor()
    if has_selection:
        new_cursor.setPosition(start)
        new_cursor.setPosition(max(start, end - removed * spaces), QTextCursor.MoveMode.KeepAnchor)
    else:
        block = doc.findBlock(pos)
        offset = pos - block.position()
        new_cursor.setPosition(block.position() + max(0, offset - spaces))
    editor.setTextCursor(new_cursor)
    editor.setFocus()


def _link_at_cursor(cursor: QTextCursor) -> re.Match[str] | None:
    block = cursor.block()
    text = block.text()
    for match in _LINK_RE.finditer(text):
        start = block.position() + match.start()
        end = block.position() + match.end()
        if start <= cursor.position() <= end:
            return match
    return None


def insert_link(editor: QPlainTextEdit) -> None:
    cursor = editor.textCursor()
    existing = _link_at_cursor(cursor)
    if existing and not cursor.hasSelection():
        label, url = existing.group(1), existing.group(2)
    elif cursor.hasSelection():
        label, url = selected_text(cursor), "https://"
    else:
        label, url = "", "https://"

    dialog = LinkDialog(editor.window(), text=label, url=url)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    label, url = dialog.values()
    if not label or not url:
        return

    markdown = f"[{label}]({url})"
    if existing and not cursor.hasSelection():
        start = cursor.block().position() + existing.start()
        end = cursor.block().position() + existing.end()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(markdown)
    else:
        cursor.insertText(markdown)
    editor.setTextCursor(cursor)
    editor.setFocus()


def insert_codeblock(editor: QPlainTextEdit) -> None:
    cursor = editor.textCursor()
    if cursor.hasSelection():
        selected = cursor.selectedText().replace("\u2029", "\n")
        cursor.insertText(f"```\n{selected}\n```")
    else:
        cursor.insertText("```\n\n```")
        cursor.movePosition(QTextCursor.MoveOperation.Up)
        editor.setTextCursor(cursor)
    editor.setFocus()


class MarkdownEditor(QPlainTextEdit):
    """Plain-text editor with smart list continuation and Tab indent."""

    def contextMenuEvent(self, event) -> None:
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        link_action = menu.addAction("Insert Hyperlink…")
        link_action.setShortcut(QKeySequence("Ctrl+K"))
        link_action.triggered.connect(lambda: insert_link(self))
        menu.exec(event.globalPos())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self._handle_enter():
                return
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                if self._should_structured_indent(cursor):
                    outdent_lines(self)
                    return
            elif self._should_structured_indent(cursor):
                indent_lines(self)
                return
            cursor.insertText("  ")
            self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)

    def _should_structured_indent(self, cursor: QTextCursor) -> bool:
        if cursor.hasSelection():
            start_block = self.document().findBlock(cursor.selectionStart()).blockNumber()
            end_block = self.document().findBlock(cursor.selectionEnd()).blockNumber()
            if start_block != end_block:
                return True
        line = cursor.block().text()
        return bool(
            _LIST_RE.match(line)
            or _CHECKBOX_RE.match(line)
            or _BLOCKQUOTE_RE.match(line)
            or _HEADING_RE.match(line)
        )

    def _handle_enter(self) -> bool:
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()

        checkbox = _CHECKBOX_RE.match(block_text)
        if checkbox:
            indent, _, content = checkbox.groups()
            if not content.strip() and pos_in_block >= len(block_text):
                self._clear_line_prefix(cursor, len(indent) + 6)
                return True
            cursor.insertText(f"\n{indent}- [ ] ")
            self.setTextCursor(cursor)
            return True

        heading = _HEADING_RE.match(block_text)
        if heading:
            indent, markers, content = heading.groups()
            if not content.strip() and pos_in_block >= len(block_text):
                self._clear_line_prefix(cursor, len(indent) + len(markers) + 1)
                return True

        blockquote = _BLOCKQUOTE_RE.match(block_text)
        if blockquote:
            indent, content = blockquote.groups()
            if not content.strip() and pos_in_block >= len(block_text):
                self._clear_line_prefix(cursor, len(indent) + 2)
                return True
            cursor.insertText(f"\n{indent}> ")
            self.setTextCursor(cursor)
            return True

        match = _LIST_RE.match(block_text)
        if match:
            indent, marker, content = match.groups()
            if not content.strip() and pos_in_block >= len(block_text):
                self._clear_line_prefix(cursor, len(indent) + len(marker) + 1)
                return True
            if marker[:-1].isdigit():
                num = int(marker[:-1]) + 1
                cursor.insertText(f"\n{indent}{num}. ")
            else:
                cursor.insertText(f"\n{indent}{marker} ")
            self.setTextCursor(cursor)
            return True

        return False

    def _clear_line_prefix(self, cursor: QTextCursor, prefix_len: int) -> None:
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            prefix_len,
        )
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.setTextCursor(cursor)


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
            ("U", "Underline (Ctrl+U)", lambda: wrap_selection(self._editor, "<u>", "</u>"), False),
            ("S", "Strikethrough", lambda: wrap_selection(self._editor, "~~", "~~"), False),
            ("H1", "Heading 1", lambda: prefix_lines(self._editor, "# ", toggle=True), False),
            ("H2", "Heading 2", lambda: prefix_lines(self._editor, "## ", toggle=True), False),
            ("H3", "Heading 3", lambda: prefix_lines(self._editor, "### ", toggle=True), False),
            ("•", "Bullet list", lambda: prefix_lines(self._editor, "- "), False),
            ("1.", "Numbered list", lambda: prefix_lines(self._editor, "1. "), False),
            ("☑", "Checklist", lambda: prefix_lines(self._editor, "- [ ] "), False),
            (">", "Blockquote", lambda: prefix_lines(self._editor, "> ", toggle=True), False),
            ("—", "Divider", lambda: self._insert_divider(), False),
            ("</>", "Inline code", lambda: wrap_selection(self._editor, "`", "`"), False),
            ("{ }", "Code block", lambda: insert_codeblock(self._editor), False),
            ("🔗", "Hyperlink (Ctrl+K)", lambda: insert_link(self._editor), False),
            ("[[", "Wiki link", lambda: wrap_selection(self._editor, "[[", "]]"), False),
            ("→", "Indent (Tab)", lambda: indent_lines(self._editor), False),
            ("←", "Outdent (Shift+Tab)", lambda: outdent_lines(self._editor), False),
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
        QShortcut(QKeySequence("Ctrl+K"), self._editor, lambda: insert_link(self._editor))

    def _insert_divider(self) -> None:
        cursor = self._editor.textCursor()
        cursor.insertText("\n---\n")
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

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
