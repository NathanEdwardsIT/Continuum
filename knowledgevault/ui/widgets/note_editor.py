"""Inspector panel — note editor with glass card."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from knowledgevault.models.entities import Note
from knowledgevault.ui.components.buttons import GhostButton, PrimaryButton
from knowledgevault.ui.components.card import ElevatedCard
from knowledgevault.ui.components.typography import Body, Caption, H2
from knowledgevault.ui.theme_palette import ThemePalette, get_palette, ThemeId


def _md_html(text: str) -> str:
    h = text
    h = re.sub(r"^### (.+)$", r"<h3>\1</h3>", h, flags=re.MULTILINE)
    h = re.sub(r"^## (.+)$", r"<h2>\1</h2>", h, flags=re.MULTILINE)
    h = re.sub(r"^# (.+)$", r"<h1>\1</h1>", h, flags=re.MULTILINE)
    h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h)
    h = re.sub(r"\*(.+?)\*", r"<i>\1</i>", h)
    h = re.sub(r"`(.+?)`", r"<code>\1</code>", h)
    h = re.sub(r"\n\n", "</p><p>", h)
    return f"<p>{h}</p>"


class NoteEditorPanel(QWidget):
    content_changed = Signal()
    focus_mode_toggled = Signal(bool)
    backlink_clicked = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("inspector")
        self._palette = get_palette(ThemeId.STUDIO)
        self._note_id: int | None = None
        self._loading = False
        self._preview = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        self._card = ElevatedCard(padding=24)
        outer.addWidget(self._card, stretch=1)

        cl = self._card.content_layout
        toolbar = QHBoxLayout()
        self._meta = Caption("")
        toolbar.addWidget(self._meta)
        toolbar.addStretch()
        self._prev_btn = GhostButton("Preview")
        self._prev_btn.setCheckable(True)
        self._prev_btn.clicked.connect(self._toggle_preview)
        toolbar.addWidget(self._prev_btn)
        self._focus_btn = GhostButton("Focus")
        self._focus_btn.setCheckable(True)
        self._focus_btn.clicked.connect(lambda c: self.focus_mode_toggled.emit(c))
        toolbar.addWidget(self._focus_btn)
        cl.addLayout(toolbar)

        self._title = QLineEdit()
        self._title.setObjectName("titleField")
        self._title.setPlaceholderText("Untitled")
        self._title.textChanged.connect(lambda: self.content_changed.emit())
        cl.addWidget(self._title)

        self._stack = QStackedWidget()
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("Start writing…")
        self._editor.textChanged.connect(self._on_edit)
        self._stack.addWidget(self._editor)
        self._browser = QTextBrowser()
        self._stack.addWidget(self._browser)
        cl.addWidget(self._stack, stretch=1)

        self._words = Caption("")
        cl.addWidget(self._words)

        meta = QHBoxLayout()
        self._cats = Caption("")
        self._tags = Caption("")
        meta.addWidget(self._cats)
        meta.addStretch()
        meta.addWidget(self._tags)
        cl.addLayout(meta)

        self._rel = H2("Related")
        self._rel.hide()
        cl.addWidget(self._rel)
        self._bl_scroll = QScrollArea()
        self._bl_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._bl_scroll.setMaximumHeight(56)
        self._bl_scroll.hide()
        bl_w = QWidget()
        self._bl_row = QHBoxLayout(bl_w)
        self._bl_row.setContentsMargins(0, 0, 0, 0)
        self._bl_scroll.setWidget(bl_w)
        cl.addWidget(self._bl_scroll)

        self._empty = Body("Select a note or create a new one")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty)
        self._show_empty(True)

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._card.apply_palette(p)
        self._meta.apply_palette(p)
        self._words.apply_palette(p)
        self._cats.apply_palette(p)
        self._tags.apply_palette(p)
        self._rel.apply_palette(p)
        self._empty.apply_palette(p)
        self._prev_btn.apply_palette(p)
        self._focus_btn.apply_palette(p)
        self._title.setStyleSheet(f"""
          QLineEdit#titleField {{
            background: transparent; border: none;
            font-size: 24px; font-weight: 700;
            color: {p.text_primary}; padding: 8px 0;
          }}
        """)
        for i in range(self._bl_row.count()):
            w = self._bl_row.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setStyleSheet(f"""
                  QPushButton {{
                    background: {p.bg_tertiary};
                    color: {p.text_secondary};
                    border: 1px solid {p.glass_border};
                    border-radius: 14px;
                    padding: 4px 12px;
                    font-size: 11px;
                  }}
                  QPushButton:hover {{
                    background: {p.accent_subtle};
                    color: {p.accent_text};
                    border-color: {p.accent};
                  }}
                """)

    set_palette = apply_palette

    def _show_empty(self, show: bool) -> None:
        self._card.setVisible(not show)
        self._empty.setVisible(show)

    def load_note(self, note: Note | None) -> None:
        self._loading = True
        if not note:
            self._note_id = None
            self._show_empty(True)
            self._loading = False
            return
        self._show_empty(False)
        self._note_id = note.id
        self._title.setText(note.title)
        self._editor.setPlainText(note.content)
        self._meta.setText(
            f"Created {note.created_at.strftime('%b %d')} · edited {note.modified_at.strftime('%b %d')}"
        )
        self._cats.setText(" · ".join(note.categories))
        self._tags.setText(" ".join(f"#{t}" for t in note.tags[:6]))
        self._update_words()
        self._loading = False

    def load_backlinks(self, backlinks) -> None:
        while self._bl_row.count():
            c = self._bl_row.takeAt(0)
            if c.widget():
                c.widget().deleteLater()
        if not backlinks:
            self._rel.hide()
            self._bl_scroll.hide()
            return
        self._rel.show()
        self._bl_scroll.show()
        for note, strength, reason in backlinks[:5]:
            btn = QPushButton(note.title[:22])
            btn.setObjectName("chipBtn")
            btn.setToolTip(f"{reason} ({strength:.0%})")
            if note.id:
                btn.clicked.connect(lambda c, n=note.id: self.backlink_clicked.emit(n))
            self._bl_row.addWidget(btn)
        self._bl_row.addStretch()

    def new_note(self) -> None:
        self._loading = True
        self._note_id = None
        self._title.clear()
        self._editor.clear()
        self._meta.clear()
        self._cats.clear()
        self._tags.clear()
        self._words.clear()
        self._rel.hide()
        self._bl_scroll.hide()
        self._show_empty(False)
        self._title.setFocus()
        self._loading = False

    def get_title(self) -> str:
        return self._title.text().strip()

    def get_content(self) -> str:
        return self._editor.toPlainText()

    @property
    def current_note_id(self) -> int | None:
        return self._note_id

    def set_note_id(self, nid: int) -> None:
        self._note_id = nid

    def _toggle_preview(self, on: bool) -> None:
        self._preview = on
        if on:
            self._render_preview()
            self._stack.setCurrentIndex(1)
            self._prev_btn.setText("Edit")
        else:
            self._stack.setCurrentIndex(0)
            self._prev_btn.setText("Preview")

    def _render_preview(self) -> None:
        p = self._palette
        self._browser.setHtml(f"""
        <style>
          body{{font-family:Segoe UI,sans-serif;color:{p.text_secondary};
                line-height:1.7;font-size:15px;background:transparent;}}
          h1{{color:{p.text_primary};font-size:22px;}}
          code{{background:{p.bg_tertiary};padding:2px 6px;border-radius:4px;}}
        </style>
        <h1>{self._title.text() or 'Untitled'}</h1>
        {_md_html(self._editor.toPlainText())}
        """)

    def _update_words(self) -> None:
        t = self._editor.toPlainText()
        self._words.setText(f"{len(t.split())} words · {len(t)} chars")

    def _on_edit(self) -> None:
        if not self._loading:
            self.content_changed.emit()
            self._update_words()
            if self._preview:
                self._render_preview()
