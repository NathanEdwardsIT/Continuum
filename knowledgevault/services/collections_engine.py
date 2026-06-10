"""Smart Collections — auto-generated dynamic note groupings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from continuum.database.repository import NoteRepository
from continuum.models.entities import Note


@dataclass
class SmartCollection:
    id: str
    name: str
    description: str
    icon: str
    notes: list[Note]
    accent_hint: str  # color hint for UI


class CollectionsEngine:
    """Generates smart collections from note patterns."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def get_collections(self) -> list[SmartCollection]:
        notes = self._repo.get_all_notes()
        if not notes:
            return []

        collections: list[SmartCollection] = []
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        # Recently modified
        recent = sorted(notes, key=lambda n: n.modified_at, reverse=True)[:6]
        collections.append(SmartCollection(
            id="recent",
            name="Recently Active",
            description="Notes you've edited lately",
            icon="◉",
            notes=recent,
            accent_hint="accent",
        ))

        # New this week
        new_week = [n for n in notes if n.created_at >= week_ago]
        if new_week:
            collections.append(SmartCollection(
                id="new_week",
                name="Fresh This Week",
                description=f"{len(new_week)} notes created recently",
                icon="✦",
                notes=new_week[:6],
                accent_hint="success",
            ))

        # Deep dives (longest notes)
        deep = sorted(notes, key=lambda n: len(n.content), reverse=True)[:5]
        if deep and len(deep[0].content) > 200:
            collections.append(SmartCollection(
                id="deep",
                name="Deep Dives",
                description="Your most detailed notes",
                icon="▤",
                notes=deep,
                accent_hint="info",
            ))

        # Most connected
        connected: list[tuple[Note, int]] = []
        for note in notes:
            assert note.id is not None
            bl_count = len(self._repo.get_backlinks_for_note(note.id))
            if bl_count > 0:
                connected.append((note, bl_count))
        connected.sort(key=lambda x: x[1], reverse=True)
        if connected:
            collections.append(SmartCollection(
                id="connected",
                name="Highly Connected",
                description="Notes with the most relationships",
                icon="◎",
                notes=[n for n, _ in connected[:5]],
                accent_hint="warning",
            ))

        return collections
