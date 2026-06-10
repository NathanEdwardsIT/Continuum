"""Note list with search filters and pin indicators."""

from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from continuum.models.entities import Note, SearchFilters, SearchResult
from continuum.ui.components.card import ElevatedCard
from continuum.ui.components.inputs import SearchField
from continuum.ui.components.typography import Badge, Body, Caption, H1, H2
from continuum.ui.theme_palette import ThemePalette


class NoteListPanel(QWidget):
    note_selected = Signal(int)
    search_changed = Signal(object)
    trash_empty_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace")
        self._palette: ThemePalette | None = None
        self._categories: list[str] = []
        self._showing_trash = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._title = H1("Notes")
        header.addWidget(self._title)
        header.addStretch()
        self._empty_trash_btn = Caption("Empty Trash")
        self._empty_trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._empty_trash_btn.hide()
        self._empty_trash_btn.mousePressEvent = lambda _e: self.trash_empty_requested.emit()
        header.addWidget(self._empty_trash_btn)
        layout.addLayout(header)

        self._search = SearchField("Search notes, tags, categories…")
        self._search.textChanged.connect(self._emit_filters)
        layout.addWidget(self._search)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self._cat_filter = QComboBox()
        self._cat_filter.addItem("All categories", "")
        self._cat_filter.currentIndexChanged.connect(self._emit_filters)
        filters.addWidget(self._cat_filter)

        from PySide6.QtWidgets import QLineEdit
        self._tag_filter = QLineEdit()
        self._tag_filter.setPlaceholderText("Tag filter")
        self._tag_filter.textChanged.connect(self._emit_filters)
        filters.addWidget(self._tag_filter)

        self._pinned_filter = QCheckBox("Pinned only")
        self._pinned_filter.stateChanged.connect(self._emit_filters)
        filters.addWidget(self._pinned_filter)
        layout.addLayout(filters)

        date_row = QHBoxLayout()
        self._after = QDateEdit()
        self._after.setCalendarPopup(True)
        self._after.setSpecialValueText("Any")
        self._after.setDate(self._after.minimumDate())
        self._after.dateChanged.connect(self._emit_filters)
        self._before = QDateEdit()
        self._before.setCalendarPopup(True)
        self._before.setSpecialValueText("Any")
        self._before.setDate(self._before.maximumDate())
        self._before.dateChanged.connect(self._emit_filters)
        date_row.addWidget(Caption("From"))
        date_row.addWidget(self._after)
        date_row.addWidget(Caption("To"))
        date_row.addWidget(self._before)
        date_row.addStretch()
        layout.addLayout(date_row)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list, stretch=1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._emit_filters)

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._title.apply_palette(p)
        self._search.apply_palette(p)
        self._empty_trash_btn.apply_palette(p)

    set_palette = apply_palette

    def set_category_options(self, categories: list[str]) -> None:
        current = self._cat_filter.currentData()
        self._cat_filter.blockSignals(True)
        self._cat_filter.clear()
        self._cat_filter.addItem("All categories", "")
        for cat in categories:
            self._cat_filter.addItem(cat, cat)
        idx = self._cat_filter.findData(current)
        if idx >= 0:
            self._cat_filter.setCurrentIndex(idx)
        self._cat_filter.blockSignals(False)
        self._categories = categories

    def get_filters(self) -> SearchFilters:
        after = self._after.date()
        before = self._before.date()
        modified_after = None
        modified_before = None
        if after != self._after.minimumDate():
            modified_after = datetime.combine(after.toPython(), time.min)
        if before != self._before.maximumDate():
            modified_before = datetime.combine(before.toPython(), time.max)
        return SearchFilters(
            query=self._search.text(),
            category=self._cat_filter.currentData() or None,
            tag=self._tag_filter.text().strip() or None,
            modified_after=modified_after,
            modified_before=modified_before,
            pinned_only=self._pinned_filter.isChecked(),
        )

    def set_trash_mode(self, enabled: bool) -> None:
        self._showing_trash = enabled
        self._empty_trash_btn.setVisible(enabled)
        self._title.setText("Trash" if enabled else "Notes")

    def _make_card(self, title: str, preview: str, date: datetime, categories: list[str], pinned: bool = False, attachments: int = 0) -> ElevatedCard:
        card = ElevatedCard(padding=16)
        if self._palette:
            card.apply_palette(self._palette)
        row = QHBoxLayout()
        prefix = "📌 " if pinned else ""
        t = H2(f"{prefix}{title or 'Untitled'}")
        d = Caption(date.strftime("%b %d"))
        if self._palette:
            t.apply_palette(self._palette)
            d.apply_palette(self._palette)
        row.addWidget(t)
        row.addStretch()
        if attachments:
            att = Caption(f"📎 {attachments}")
            if self._palette:
                att.apply_palette(self._palette)
            row.addWidget(att)
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
        if not self._showing_trash:
            self._title.setText(f"{len(notes)} Notes")
        for note in notes:
            item = QListWidgetItem(self._list)
            card = self._make_card(
                note.title, note.preview, note.modified_at, note.categories,
                pinned=note.pinned, attachments=note.attachment_count,
            )
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

    def _emit_filters(self, *_args) -> None:
        if self._showing_trash:
            return
        self._search_timer.start()

    def emit_filters_now(self) -> None:
        if not self._showing_trash:
            self.search_changed.emit(self.get_filters())

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            item = self._list.item(row)
            if item:
                nid = item.data(Qt.ItemDataRole.UserRole)
                if nid is not None:
                    self.note_selected.emit(nid)

    def clear_search(self) -> None:
        self._search.clear()
