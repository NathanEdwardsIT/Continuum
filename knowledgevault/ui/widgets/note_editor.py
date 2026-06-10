"""Inspector panel — note editor with formatting toolbar and improved layout."""

from __future__ import annotations

import os
import subprocess
import sys

import markdown
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from continuum.models.entities import Attachment, Note, OrganizationOverrides
from continuum.ui.components.buttons import GhostButton
from continuum.ui.components.card import ElevatedCard
from continuum.ui.components.markdown_toolbar import MarkdownToolBar, style_plain_editor
from continuum.ui.components.typography import Body, Caption, H2
from continuum.ui.theme_palette import ThemePalette, ThemeId, get_palette


class NoteEditorPanel(QWidget):
    content_changed = Signal()
    focus_mode_toggled = Signal(bool)
    backlink_clicked = Signal(int)
    delete_requested = Signal(int)
    restore_requested = Signal(int)
    pin_toggled = Signal(int, bool)
    overrides_changed = Signal(int)
    attachment_added = Signal(int, str)
    attachment_removed = Signal(int)
    add_category_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("inspector")
        self._palette = get_palette(ThemeId.STUDIO)
        self._note_id: int | None = None
        self._loading = False
        self._preview = False
        self._is_deleted = False
        self._overrides = OrganizationOverrides()
        self._toolbar_btns: list[GhostButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        self._card = ElevatedCard(padding=16)
        card = self._card.content_layout
        card.setSpacing(10)
        outer.addWidget(self._card, stretch=1)

        # ── Header: actions menu + meta + cursor position ──
        header = QHBoxLayout()
        header.setSpacing(8)
        self._actions_btn = QToolButton()
        self._actions_btn.setText("Actions ▾")
        self._actions_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._actions_menu = QMenu(self)
        self._pin_action = self._actions_menu.addAction("Pin note")
        self._pin_action.setCheckable(True)
        self._pin_action.triggered.connect(self._menu_pin)
        self._actions_menu.addAction("Attach file…", self._add_attachment)
        self._prev_action = self._actions_menu.addAction("Toggle preview")
        self._prev_action.setCheckable(True)
        self._prev_action.triggered.connect(self._menu_preview)
        self._focus_action = self._actions_menu.addAction("Focus mode")
        self._focus_action.setCheckable(True)
        self._focus_action.triggered.connect(lambda on: self.focus_mode_toggled.emit(on))
        self._actions_menu.addSeparator()
        self._delete_action = self._actions_menu.addAction("Move to trash", self._delete_note)
        self._restore_action = self._actions_menu.addAction("Restore note", self._restore_note)
        self._restore_action.setVisible(False)
        self._actions_btn.setMenu(self._actions_menu)
        header.addWidget(self._actions_btn)

        self._meta = Caption("")
        header.addWidget(self._meta)
        header.addStretch()
        self._cursor_pos = Caption("Ln 1, Col 1")
        header.addWidget(self._cursor_pos)
        card.addLayout(header)

        # ── Markdown formatting toolbar ──
        self._editor = QPlainTextEdit()
        style_plain_editor(self._editor, self._palette)
        self._editor.setPlaceholderText(
            "Start writing…  Use the toolbar for bold, italic, headings, and lists.\n"
            "Wiki links: [[Note Title]]"
        )
        self._editor.setMinimumHeight(280)
        self._editor.textChanged.connect(self._on_edit)
        self._editor.cursorPositionChanged.connect(self._update_cursor_pos)
        self._editor.setCursorWidth(2)

        self._fmt_toolbar = MarkdownToolBar(self._editor)
        card.addWidget(self._fmt_toolbar)

        # ── Title ──
        self._title = QLineEdit()
        self._title.setObjectName("titleField")
        self._title.setPlaceholderText("Note title")
        self._title.setMinimumHeight(44)
        self._title.textChanged.connect(lambda: self.content_changed.emit())
        card.addWidget(self._title)

        # ── Editor / preview stack ──
        self._stack = QStackedWidget()
        self._stack.addWidget(self._editor)
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._stack.addWidget(self._browser)
        card.addWidget(self._stack, stretch=1)

        # ── Status line ──
        status = QHBoxLayout()
        self._words = Caption("")
        status.addWidget(self._words)
        status.addStretch()
        self._preview_hint = Caption("Ctrl+B bold · Ctrl+I italic · Ctrl+P preview")
        status.addWidget(self._preview_hint)
        card.addLayout(status)

        # ── Organize section ──
        org_frame = QFrame()
        org_frame.setObjectName("orgSection")
        org_layout = QVBoxLayout(org_frame)
        org_layout.setContentsMargins(0, 4, 0, 0)
        org_layout.setSpacing(6)
        org_title = Caption("ORGANIZE")
        org_layout.addWidget(org_title)
        self._org_title = org_title

        org_row = QHBoxLayout()
        org_row.setSpacing(6)
        self._new_cat_btn = GhostButton("+ Category")
        self._new_cat_btn.clicked.connect(lambda checked=False: self.add_category_requested.emit())
        org_row.addWidget(self._new_cat_btn)

        self._lock_cat = QComboBox()
        self._lock_cat.setMinimumHeight(32)
        self._lock_cat.addItem("Assign category…", "")
        org_row.addWidget(self._lock_cat, stretch=1)

        lock_btn = GhostButton("Lock")
        lock_btn.clicked.connect(lambda checked=False: self._lock_category())
        org_row.addWidget(lock_btn)
        self._toolbar_btns.extend([self._new_cat_btn, lock_btn])
        org_layout.addLayout(org_row)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        self._add_tag = QLineEdit()
        self._add_tag.setPlaceholderText("Add custom tag")
        self._add_tag.setMinimumHeight(32)
        tag_row.addWidget(self._add_tag, stretch=1)
        add_tag_btn = GhostButton("+ Tag")
        add_tag_btn.clicked.connect(lambda checked=False: self._add_tag_override())
        tag_row.addWidget(add_tag_btn)
        self._toolbar_btns.append(add_tag_btn)
        org_layout.addLayout(tag_row)
        card.addWidget(org_frame)

        meta = QHBoxLayout()
        self._cats = Caption("")
        self._tags = Caption("")
        self._cats.setWordWrap(True)
        meta.addWidget(self._cats, stretch=1)
        meta.addWidget(self._tags, stretch=1)
        card.addLayout(meta)

        # ── Attachments & backlinks in scroll areas ──
        self._att_label = H2("Attachments")
        self._att_label.hide()
        card.addWidget(self._att_label)
        self._att_scroll = QScrollArea()
        self._att_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._att_scroll.setWidgetResizable(True)
        self._att_scroll.setMaximumHeight(64)
        self._att_scroll.hide()
        att_w = QWidget()
        self._att_row = QHBoxLayout(att_w)
        self._att_row.setContentsMargins(0, 0, 0, 0)
        self._att_scroll.setWidget(att_w)
        card.addWidget(self._att_scroll)

        self._rel = H2("Related notes")
        self._rel.hide()
        card.addWidget(self._rel)
        self._bl_scroll = QScrollArea()
        self._bl_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._bl_scroll.setWidgetResizable(True)
        self._bl_scroll.setMaximumHeight(56)
        self._bl_scroll.hide()
        bl_w = QWidget()
        self._bl_row = QHBoxLayout(bl_w)
        self._bl_row.setContentsMargins(0, 0, 0, 0)
        self._bl_scroll.setWidget(bl_w)
        card.addWidget(self._bl_scroll)

        self._empty = Body("Select a note or press Ctrl+N to start writing")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty)
        self._show_empty(True)

        # Hidden compat refs for main_window shortcuts
        self._prev_btn = self._prev_action
        self._pin_btn = self._pin_action
        self._focus_btn = self._focus_action
        self._delete_btn = self._delete_action
        self._attach_btn = self._actions_menu.actions()[1]
        self._restore_btn = self._restore_action

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._card.apply_palette(p)
        self._meta.apply_palette(p)
        self._words.apply_palette(p)
        self._cats.apply_palette(p)
        self._tags.apply_palette(p)
        self._rel.apply_palette(p)
        self._att_label.apply_palette(p)
        self._org_title.apply_palette(p)
        self._preview_hint.apply_palette(p)
        self._cursor_pos.apply_palette(p)
        self._empty.apply_palette(p)
        self._fmt_toolbar.apply_palette(p)
        style_plain_editor(self._editor, p)
        for btn in self._toolbar_btns:
            btn.apply_palette(p)

        pal = self._editor.palette()
        pal.setColor(QPalette.ColorRole.Text, QColor(p.text_primary))
        pal.setColor(QPalette.ColorRole.Base, QColor(p.bg_tertiary))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(p.selection))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(p.text_primary))
        self._editor.setPalette(pal)

        self._title.setStyleSheet(f"""
          QLineEdit#titleField {{
            background: {p.bg_tertiary};
            border: 1px solid {p.border_subtle};
            border-radius: 8px;
            font-size: 22px;
            font-weight: 700;
            color: {p.text_primary};
            padding: 8px 12px;
          }}
          QLineEdit#titleField:focus {{
            border: 2px solid {p.accent};
            padding: 7px 11px;
          }}
        """)
        self._actions_btn.setStyleSheet(f"""
            QToolButton {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid {p.border_subtle};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QToolButton::menu-indicator {{ image: none; }}
            QToolButton:hover {{ border-color: {p.accent}; }}
        """)
        self._lock_cat.setStyleSheet(f"""
            QComboBox {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid {p.border_subtle};
                border-radius: 8px;
                padding: 4px 10px;
            }}
            QComboBox:focus {{ border-color: {p.accent}; }}
        """)
        self._add_tag.setStyleSheet(f"""
            QLineEdit {{
                background: {p.bg_tertiary};
                color: {p.text_primary};
                border: 1px solid {p.border_subtle};
                border-radius: 8px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{ border: 2px solid {p.accent}; }}
        """)
        org_frame = self.findChild(QFrame, "orgSection")
        if org_frame:
            org_frame.setStyleSheet(f"""
                QFrame#orgSection {{
                    border-top: 1px solid {p.border_subtle};
                    margin-top: 4px;
                    padding-top: 4px;
                }}
            """)
        self._style_chips()

    set_palette = apply_palette

    def _style_chips(self) -> None:
        p = self._palette
        for layout in (self._bl_row, self._att_row):
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
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

    def _update_cursor_pos(self) -> None:
        cursor = self._editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self._cursor_pos.setText(f"Ln {line}, Col {col}")

    def _show_empty(self, show: bool) -> None:
        self._card.setVisible(not show)
        self._empty.setVisible(show)

    def set_category_options(self, categories: list[str]) -> None:
        current = self._lock_cat.currentData()
        self._lock_cat.blockSignals(True)
        self._lock_cat.clear()
        self._lock_cat.addItem("Assign category…", "")
        for cat in categories:
            self._lock_cat.addItem(cat, cat)
        idx = self._lock_cat.findData(current)
        if idx >= 0:
            self._lock_cat.setCurrentIndex(idx)
        self._lock_cat.blockSignals(False)

    def load_note(self, note: Note | None) -> None:
        self._loading = True
        if not note:
            self._note_id = None
            self._show_empty(True)
            self._loading = False
            return
        self._show_empty(False)
        self._note_id = note.id
        self._is_deleted = note.is_deleted
        self._overrides = note.organization_overrides
        self._title.setText(note.title)
        self._editor.setPlainText(note.content)
        self._meta.setText(
            f"Created {note.created_at.strftime('%b %d')} · edited {note.modified_at.strftime('%b %d')}"
        )
        self._cats.setText("Categories: " + (" · ".join(note.categories) if note.categories else "—"))
        self._tags.setText("Tags: " + (" ".join(f"#{t}" for t in note.tags[:8]) if note.tags else "—"))
        self._pin_action.setChecked(note.pinned)
        self._pin_action.setText("Unpin note" if note.pinned else "Pin note")
        self._delete_action.setVisible(not note.is_deleted)
        self._restore_action.setVisible(note.is_deleted)
        self._title.setReadOnly(note.is_deleted)
        self._editor.setReadOnly(note.is_deleted)
        self._new_cat_btn.setEnabled(not note.is_deleted)
        self._update_words()
        self._update_cursor_pos()
        self._loading = False

    def load_attachments(self, attachments: list[Attachment]) -> None:
        while self._att_row.count():
            c = self._att_row.takeAt(0)
            if c.widget():
                c.widget().deleteLater()
        if not attachments:
            self._att_label.hide()
            self._att_scroll.hide()
            return
        self._att_label.show()
        self._att_scroll.show()
        for att in attachments:
            btn = QPushButton(att.filename[:24])
            btn.setToolTip(f"{att.filename} ({att.size_bytes // 1024} KB)")
            btn.clicked.connect(lambda _c, a=att: self._open_attachment(a))
            self._att_row.addWidget(btn)
        self._att_row.addStretch()
        self._style_chips()

    def _open_attachment(self, attachment: Attachment) -> None:
        if attachment.id:
            self.attachment_added.emit(self._note_id or 0, str(attachment.id))

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
            btn.setToolTip(f"{reason} ({strength:.0%})")
            if note.id:
                btn.clicked.connect(lambda _c, n=note.id: self.backlink_clicked.emit(n))
            self._bl_row.addWidget(btn)
        self._bl_row.addStretch()
        self._style_chips()

    def new_note(self) -> None:
        self._loading = True
        self._note_id = None
        self._is_deleted = False
        self._overrides = OrganizationOverrides()
        self._title.clear()
        self._editor.clear()
        self._meta.clear()
        self._cats.setText("Categories: —")
        self._tags.setText("Tags: —")
        self._words.clear()
        self._rel.hide()
        self._bl_scroll.hide()
        self._att_label.hide()
        self._att_scroll.hide()
        self._delete_action.setVisible(True)
        self._restore_action.setVisible(False)
        self._title.setReadOnly(False)
        self._editor.setReadOnly(False)
        self._new_cat_btn.setEnabled(True)
        self._pin_action.setChecked(False)
        self._pin_action.setText("Pin note")
        self._prev_action.setChecked(False)
        self._stack.setCurrentIndex(0)
        self._show_empty(False)
        self._title.setFocus()
        self._update_cursor_pos()
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

    def _menu_preview(self, on: bool) -> None:
        self._preview = on
        if on:
            self._render_preview()
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)
        self._editor.setFocus()

    def _menu_pin(self, on: bool) -> None:
        if self._note_id:
            self.pin_toggled.emit(self._note_id, on)
            self._pin_action.setText("Unpin note" if on else "Pin note")

    def _render_preview(self) -> None:
        p = self._palette
        body = markdown.markdown(
            self._editor.toPlainText(),
            extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
        )
        self._browser.setHtml(f"""
        <style>
          body{{font-family:Segoe UI,sans-serif;color:{p.text_secondary};
                line-height:1.7;font-size:15px;background:transparent;}}
          h1,h2,h3{{color:{p.text_primary};}}
          code,pre{{background:{p.bg_tertiary};padding:2px 6px;border-radius:4px;}}
          pre{{padding:12px;overflow-x:auto;}}
          blockquote{{border-left:3px solid {p.accent};margin-left:0;padding-left:12px;color:{p.text_muted};}}
          a{{color:{p.accent};}}
          strong{{color:{p.text_primary};}}
        </style>
        <h1>{self._title.text() or 'Untitled'}</h1>
        {body}
        """)

    def _update_words(self) -> None:
        t = self._editor.toPlainText()
        self._words.setText(f"{len(t.split())} words · {len(t)} characters")

    def _on_edit(self) -> None:
        if not self._loading:
            self.content_changed.emit()
            self._update_words()
            if self._preview:
                self._render_preview()

    def _delete_note(self) -> None:
        if self._note_id and QMessageBox.question(
            self, "Move to Trash", "Move this note to trash?",
        ) == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(self._note_id)

    def _restore_note(self) -> None:
        if self._note_id:
            self.restore_requested.emit(self._note_id)

    def _add_attachment(self) -> None:
        if not self._note_id:
            QMessageBox.information(self, "Save First", "Save the note before adding attachments.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Attach File")
        if path:
            self.attachment_added.emit(self._note_id, path)

    def _lock_category(self) -> None:
        cat = self._lock_cat.currentData()
        if not cat:
            return
        if not self._note_id:
            QMessageBox.information(
                self, "Save First",
                "Start typing — the note will save automatically, then you can lock a category.",
            )
            return
        if cat not in self._overrides.locked_categories:
            self._overrides.locked_categories.append(cat)
            self.overrides_changed.emit(self._note_id)

    def lock_category_by_name(self, name: str) -> None:
        if name not in self._overrides.locked_categories:
            self._overrides.locked_categories.append(name)
        if self._note_id:
            self.overrides_changed.emit(self._note_id)

    def _add_tag_override(self) -> None:
        tag = self._add_tag.text().strip().lower()
        if not tag:
            return
        if not self._note_id:
            QMessageBox.information(self, "Save First", "The note will save automatically once you start writing.")
            return
        if tag not in self._overrides.added_tags:
            self._overrides.added_tags.append(tag)
            self._add_tag.clear()
            self.overrides_changed.emit(self._note_id)

    def get_overrides(self) -> OrganizationOverrides:
        return self._overrides

    @staticmethod
    def open_file_path(path: str) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
