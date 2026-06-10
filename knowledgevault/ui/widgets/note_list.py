"""Note list — elevated card per note."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from knowledgevault.models.entities import Note, SearchResult
from knowledgevault.ui.components.card import ElevatedCard
from knowledgevault.ui.components.inputs import SearchField
from knowledgevault.ui.components.typography import Badge, Body, Caption, H1, H2
from knowledgevault.ui.theme_palette import ThemePalette


class NoteListPanel(QWidget):
    note_selected = Signal(int)
    search_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace")
        self._palette: ThemePalette | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._title = H1("Notes")
        layout.addWidget(self._title)
        self._search = SearchField("Search notes, tags, categories…")
        self._search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list, stretch=1)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(lambda: self.search_changed.emit(self._search.text()))

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._title.apply_palette(p)
        self._search.apply_palette(p)

    set_palette = apply_palette

    def _make_card(self, title: str, preview: str, date: datetime, categories: list[str]) -> ElevatedCard:
        card = ElevatedCard(padding=16)
        if self._palette:
            card.apply_palette(self._palette)
        row = QHBoxLayout()
        t = H2(title or "Untitled")
        d = Caption(date.strftime("%b %d"))
        if self._palette:
            t.apply_palette(self._palette)
            d.apply_palette(self._palette)
        row.addWidget(t)
        row.addStretch()
        row.addWidget(d)
        card.content_layout.addLayout(row)
        if preview:
            b = Body(preview)
            if self._palette:
                b.apply_palette(self._palette)
            card.content_layout.addWidget(b)
        if categories:
            chips = QHBoxLayout()
            for cat in categories[:3]:
                chip = Badge(cat)
                if self._palette:
                    chip.apply_palette(self._palette)
                chips.addWidget(chip)
            chips.addStretch()
            card.content_layout.addLayout(chips)
        return card

    def set_notes(self, notes: list[Note]) -> None:
        self._list.clear()
        self._title.setText(f"{len(notes)} Notes")
        for note in notes:
            item = QListWidgetItem(self._list)
            card = self._make_card(note.title, note.preview, note.modified_at, note.categories)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
            item.setData(Qt.ItemDataRole.UserRole, note.id)

    def set_search_results(self, results: list[SearchResult]) -> None:
        self._list.clear()
        self._title.setText(f"{len(results)} Results")
        for r in results:
            item = QListWidgetItem(self._list)
            card = self._make_card(r.title, r.snippet, datetime.now(), r.categories)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
            item.setData(Qt.ItemDataRole.UserRole, r.note_id)

    def select_note(self, note_id: int) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == note_id:
                self._list.setCurrentRow(i)
                break

    def _on_search_changed(self, _t: str) -> None:
        self._search_timer.start()

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            item = self._list.item(row)
            if item:
                nid = item.data(Qt.ItemDataRole.UserRole)
                if nid is not None:
                    self.note_selected.emit(nid)

    def clear_search(self) -> None:
        self._search.clear()
