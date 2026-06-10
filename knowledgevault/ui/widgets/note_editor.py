"""Inspector panel — note editor with markdown, attachments, and overrides."""

from __future__ import annotations

import os
import subprocess
import sys

import markdown
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from continuum.models.entities import Attachment, Note, OrganizationOverrides
from continuum.ui.components.buttons import GhostButton, PrimaryButton
from continuum.ui.components.card import ElevatedCard
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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("inspector")
        self._palette = get_palette(ThemeId.STUDIO)
        self._note_id: int | None = None
        self._loading = False
        self._preview = False
        self._is_deleted = False
        self._overrides = OrganizationOverrides()
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

        self._pin_btn = GhostButton("Pin")
        self._pin_btn.setCheckable(True)
        self._pin_btn.clicked.connect(self._toggle_pin)
        toolbar.addWidget(self._pin_btn)

        self._attach_btn = GhostButton("Attach")
        self._attach_btn.clicked.connect(lambda checked=False: self._add_attachment())
        toolbar.addWidget(self._attach_btn)

        self._prev_btn = GhostButton("Preview")
        self._prev_btn.setCheckable(True)
        self._prev_btn.clicked.connect(self._toggle_preview)
        toolbar.addWidget(self._prev_btn)

        self._focus_btn = GhostButton("Focus")
        self._focus_btn.setCheckable(True)
        self._focus_btn.clicked.connect(lambda c: self.focus_mode_toggled.emit(c))
        toolbar.addWidget(self._focus_btn)

        self._delete_btn = GhostButton("Delete")
        self._delete_btn.clicked.connect(lambda checked=False: self._delete_note())
        toolbar.addWidget(self._delete_btn)

        self._restore_btn = GhostButton("Restore")
        self._restore_btn.hide()
        self._restore_btn.clicked.connect(lambda checked=False: self._restore_note())
        toolbar.addWidget(self._restore_btn)

        cl.addLayout(toolbar)

        self._title = QLineEdit()
        self._title.setObjectName("titleField")
        self._title.setPlaceholderText("Untitled")
        self._title.textChanged.connect(lambda: self.content_changed.emit())
        cl.addWidget(self._title)

        self._stack = QStackedWidget()
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("Start writing… Use [[Note Title]] for wiki links.")
        self._editor.textChanged.connect(self._on_edit)
        self._stack.addWidget(self._editor)
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._stack.addWidget(self._browser)
        cl.addWidget(self._stack, stretch=1)

        self._words = Caption("")
        cl.addWidget(self._words)

        override_row = QHBoxLayout()
        self._lock_cat = QComboBox()
        self._lock_cat.setEditable(False)
        self._lock_cat.addItem("Lock category…", "")
        override_row.addWidget(self._lock_cat)
        lock_btn = GhostButton("Lock")
        lock_btn.clicked.connect(lambda checked=False: self._lock_category())
        override_row.addWidget(lock_btn)
        self._add_tag = QLineEdit()
        self._add_tag.setPlaceholderText("Add tag override")
        override_row.addWidget(self._add_tag)
        add_tag_btn = GhostButton("+ Tag")
        add_tag_btn.clicked.connect(lambda checked=False: self._add_tag_override())
        override_row.addWidget(add_tag_btn)
        cl.addLayout(override_row)

        meta = QHBoxLayout()
        self._cats = Caption("")
        self._tags = Caption("")
        meta.addWidget(self._cats)
        meta.addStretch()
        meta.addWidget(self._tags)
        cl.addLayout(meta)

        self._att_label = H2("Attachments")
        self._att_label.hide()
        cl.addWidget(self._att_label)
        self._att_scroll = QScrollArea()
        self._att_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._att_scroll.setMaximumHeight(72)
        self._att_scroll.hide()
        att_w = QWidget()
        self._att_row = QHBoxLayout(att_w)
        self._att_row.setContentsMargins(0, 0, 0, 0)
        self._att_scroll.setWidget(att_w)
        cl.addWidget(self._att_scroll)

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
        self._att_label.apply_palette(p)
        self._empty.apply_palette(p)
        self._prev_btn.apply_palette(p)
        self._focus_btn.apply_palette(p)
        self._pin_btn.apply_palette(p)
        self._attach_btn.apply_palette(p)
        self._delete_btn.apply_palette(p)
        self._restore_btn.apply_palette(p)
        self._title.setStyleSheet(f"""
          QLineEdit#titleField {{
            background: transparent; border: none;
            font-size: 24px; font-weight: 700;
            color: {p.text_primary}; padding: 8px 0;
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

    def _show_empty(self, show: bool) -> None:
        self._card.setVisible(not show)
        self._empty.setVisible(show)

    def set_category_options(self, categories: list[str]) -> None:
        current = self._lock_cat.currentData()
        self._lock_cat.blockSignals(True)
        self._lock_cat.clear()
        self._lock_cat.addItem("Lock category…", "")
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
        self._cats.setText(" · ".join(note.categories) or "No categories")
        self._tags.setText(" ".join(f"#{t}" for t in note.tags[:8]) or "No tags")
        self._pin_btn.setChecked(note.pinned)
        self._pin_btn.setText("Unpin" if note.pinned else "Pin")
        self._delete_btn.setVisible(not note.is_deleted)
        self._restore_btn.setVisible(note.is_deleted)
        self._title.setReadOnly(note.is_deleted)
        self._editor.setReadOnly(note.is_deleted)
        self._attach_btn.setEnabled(not note.is_deleted)
        self._update_words()
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
            aid = att.id
            btn.clicked.connect(lambda _c, a=att: self._open_attachment(a))
            if aid:
                btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
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
        self._title.clear()
        self._editor.clear()
        self._meta.clear()
        self._cats.clear()
        self._tags.clear()
        self._words.clear()
        self._rel.hide()
        self._bl_scroll.hide()
        self._att_label.hide()
        self._att_scroll.hide()
        self._delete_btn.setVisible(True)
        self._restore_btn.hide()
        self._title.setReadOnly(False)
        self._editor.setReadOnly(False)
        self._attach_btn.setEnabled(True)
        self._pin_btn.setChecked(False)
        self._pin_btn.setText("Pin")
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
        </style>
        <h1>{self._title.text() or 'Untitled'}</h1>
        {body}
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

    def _toggle_pin(self) -> None:
        if self._note_id:
            self.pin_toggled.emit(self._note_id, self._pin_btn.isChecked())
            self._pin_btn.setText("Unpin" if self._pin_btn.isChecked() else "Pin")

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
        if not cat or not self._note_id:
            return
        if cat not in self._overrides.locked_categories:
            self._overrides.locked_categories.append(cat)
            self.overrides_changed.emit(self._note_id)

    def _add_tag_override(self) -> None:
        tag = self._add_tag.text().strip().lower()
        if not tag or not self._note_id:
            return
        if tag not in self._overrides.added_tags:
            self._overrides.added_tags.append(tag)
            self._add_tag.clear()
            self.overrides_changed.emit(self._note_id)

    def remove_tag_override_prompt(self) -> None:
        if not self._note_id or not self._overrides.added_tags:
            return
        tag, ok = QInputDialog.getItem(
            self, "Remove Tag Override", "Tag:", self._overrides.added_tags, 0, False,
        )
        if ok and tag in self._overrides.added_tags:
            self._overrides.added_tags.remove(tag)
            self._overrides.removed_tags.append(tag)
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
