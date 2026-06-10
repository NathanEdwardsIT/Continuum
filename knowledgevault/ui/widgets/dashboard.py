"""Designer dashboard — card grid layout."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from knowledgevault.models.entities import ActivityStats, Note
from knowledgevault.services.collections_engine import SmartCollection
from knowledgevault.services.insights_engine import WritingInsights
from knowledgevault.ui.components.card import ElevatedCard, GlassPanel
from knowledgevault.ui.components.clickable import ClickableCard
from knowledgevault.ui.components.typography import Badge, Body, Caption, H1, H2
from knowledgevault.ui.theme_palette import ThemePalette
from knowledgevault.ui.widgets.heatmap import ActivityHeatmap


class StatTile(ElevatedCard):
    def __init__(self, label: str, value: str = "0", parent=None) -> None:
        super().__init__(parent, padding=18)
        from PySide6.QtWidgets import QLabel
        self._val = QLabel(value)
        self._val.setObjectName("statNum")
        self._lbl = Caption(label)
        self.content_layout.addWidget(self._val)
        self.content_layout.addWidget(self._lbl)
        self.setMinimumHeight(96)

    def set_value(self, v: str) -> None:
        self._val.setText(v)

    def apply_palette(self, p: ThemePalette) -> None:
        super().apply_palette(p)
        self._val.setStyleSheet(f"""
          QLabel#statNum {{
            font-size: 30px; font-weight: 700;
            color: {p.text_primary}; letter-spacing: -1px;
            background: transparent;
          }}
        """)
        self._lbl.apply_palette(p)


class DashboardWidget(QWidget):
    note_clicked = Signal(int)
    collection_clicked = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace")
        self._palette: ThemePalette | None = None
        self._cards: list[ElevatedCard] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)

        self._heading = H1("Dashboard")
        layout.addWidget(self._heading)
        self._sub = Body("Your knowledge, automatically organized.")
        layout.addWidget(self._sub)

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        self._s1 = StatTile("Total Notes")
        self._s2 = StatTile("Categories")
        self._s3 = StatTile("Tags")
        self._s4 = StatTile("Connections")
        for s in (self._s1, self._s2, self._s3, self._s4):
            row1.addWidget(s)
            self._cards.append(s)
        layout.addLayout(row1)

        self._insight_title = H2("Writing Insights")
        layout.addWidget(self._insight_title)
        row2 = QHBoxLayout()
        row2.setSpacing(14)
        self._w = StatTile("Total Words")
        self._wk = StatTile("This Week")
        self._st = StatTile("Day Streak")
        self._av = StatTile("Avg Words")
        for s in (self._w, self._wk, self._st, self._av):
            row2.addWidget(s)
            self._cards.append(s)
        layout.addLayout(row2)

        heat_card = GlassPanel(padding=16)
        heat_card.content_layout.addWidget(Caption("Activity — last 90 days"))
        self._heatmap = ActivityHeatmap()
        heat_card.content_layout.addWidget(self._heatmap)
        self._heat_card = heat_card
        layout.addWidget(heat_card)

        self._coll_title = H2("Smart Collections")
        layout.addWidget(self._coll_title)
        self._coll_grid = QGridLayout()
        self._coll_grid.setSpacing(14)
        layout.addLayout(self._coll_grid)

        self._act_title = H2("Recent Activity")
        layout.addWidget(self._act_title)
        self._act_list = QVBoxLayout()
        self._act_list.setSpacing(10)
        layout.addLayout(self._act_list)
        layout.addStretch()

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._heading.apply_palette(p)
        self._sub.apply_palette(p)
        self._insight_title.apply_palette(p)
        self._coll_title.apply_palette(p)
        self._act_title.apply_palette(p)
        self._heat_card.apply_palette(p)
        self._heatmap.set_palette(p)
        for c in self._cards:
            c.apply_palette(p)

    set_palette = apply_palette

    def update_stats(self, stats: ActivityStats) -> None:
        self._s1.set_value(str(stats.total_notes))
        self._s2.set_value(str(stats.categories_count))
        self._s3.set_value(str(stats.tags_count))
        self._s4.set_value(str(stats.backlinks_count))

    def update_insights(self, insights: WritingInsights) -> None:
        self._w.set_value(f"{insights.total_words:,}")
        self._wk.set_value(str(insights.notes_this_week))
        self._st.set_value(str(insights.writing_streak_days))
        self._av.set_value(str(insights.avg_words_per_note))
        self._heatmap.set_activity(insights.daily_activity)

    def update_collections(self, collections: list[SmartCollection]) -> None:
        while self._coll_grid.count():
            item = self._coll_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        p = self._palette
        for i, coll in enumerate(collections[:4]):
            card = ClickableCard(padding=16)
            if p:
                card.apply_palette(p)
            card.clicked.connect(lambda c=coll.id: self.collection_clicked.emit(c))
            row = QHBoxLayout()
            title = H2(coll.name)
            if p:
                title.apply_palette(p)
            badge = Badge(str(len(coll.notes)))
            if p:
                badge.apply_palette(p)
            row.addWidget(title)
            row.addStretch()
            row.addWidget(badge)
            card.content_layout.addLayout(row)
            desc = Caption(coll.description)
            if p:
                desc.apply_palette(p)
            card.content_layout.addWidget(desc)
            previews = ", ".join((n.title or "Untitled")[:20] for n in coll.notes[:3])
            body = Body(previews)
            if p:
                body.apply_palette(p)
            card.content_layout.addWidget(body)
            self._coll_grid.addWidget(card, i // 2, i % 2)

    def update_activity(self, notes: list[Note]) -> None:
        while self._act_list.count():
            item = self._act_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        p = self._palette
        if not notes:
            empty = Body("Create your first note to get started.")
            if p:
                empty.apply_palette(p)
            self._act_list.addWidget(empty)
            return
        for note in notes[:8]:
            card = ClickableCard(padding=14)
            if p:
                card.apply_palette(p)
            if note.id:
                card.clicked.connect(lambda n=note.id: self.note_clicked.emit(n))
            t = H2(note.title or "Untitled")
            b = Body(note.preview)
            c = Caption(note.modified_at.strftime("%b %d, %Y"))
            if p:
                t.apply_palette(p)
                b.apply_palette(p)
                c.apply_palette(p)
            card.content_layout.addWidget(t)
            card.content_layout.addWidget(b)
            card.content_layout.addWidget(c)
            self._act_list.addWidget(card)
