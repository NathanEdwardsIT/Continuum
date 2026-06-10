"""Central note service orchestrating all automatic organization."""

from __future__ import annotations

from datetime import datetime

from knowledgevault.database.connection import DatabaseConnection
from knowledgevault.database.repository import NoteRepository
from knowledgevault.models.entities import Note
from knowledgevault.services.backlink_engine import BacklinkEngine
from knowledgevault.services.categorization import CategorizationEngine
from knowledgevault.services.folder_engine import FolderEngine
from knowledgevault.services.collections_engine import CollectionsEngine
from knowledgevault.services.graph_engine import GraphEngine
from knowledgevault.services.insights_engine import InsightsEngine
from knowledgevault.services.search_engine import SearchEngine
from knowledgevault.services.tag_engine import TagEngine


class NoteService:
    """Orchestrates note CRUD and automatic organization pipelines."""

    def __init__(self, db: DatabaseConnection | None = None, user_id: int | None = None) -> None:
        self.db = db or DatabaseConnection()
        self.repository = NoteRepository(self.db)
        self.repository.set_user_id(user_id)
        self.categorization = CategorizationEngine()
        self.tags = TagEngine()
        self.backlinks = BacklinkEngine()
        self.folders = FolderEngine()
        self.search = SearchEngine(self.repository)
        self.graph = GraphEngine(self.repository)
        self.insights = InsightsEngine(self.repository)
        self.collections = CollectionsEngine(self.repository)
        self._user_id = user_id

    def set_user_id(self, user_id: int | None) -> None:
        self._user_id = user_id
        self.repository.set_user_id(user_id)

    def create_note(self, title: str = "", content: str = "") -> Note:
        note = self.repository.create_note(title, content)
        assert note.id is not None
        self._organize_note(note.id, title, content)
        return self.repository.get_note(note.id) or note

    def save_note(self, note_id: int | None, title: str, content: str) -> Note:
        if note_id is None:
            return self.create_note(title, content)

        note = self.repository.update_note(note_id, title, content)
        self._organize_note(note_id, title, content)
        return self.repository.get_note(note_id) or note

    def delete_note(self, note_id: int) -> None:
        self.repository.delete_note(note_id)

    def get_note(self, note_id: int) -> Note | None:
        return self.repository.get_note(note_id)

    def get_all_notes(self, limit: int | None = None) -> list[Note]:
        return self.repository.get_all_notes(limit=limit)

    def get_notes_by_filter(
        self, filter_type: str, filter_value: str
    ) -> list[Note]:
        if filter_type == "category":
            return self.repository.get_notes_by_category(filter_value)
        if filter_type == "folder":
            return self.repository.get_notes_by_folder(filter_value)
        if filter_type == "tag":
            return self.repository.get_notes_by_tag(filter_value)
        return self.repository.get_all_notes()

    def _organize_note(self, note_id: int, title: str, content: str) -> None:
        """Run the full automatic organization pipeline."""
        categories = self.categorization.categorize(title, content)
        tags = self.tags.generate_tags(title, content)
        folder_names = self.folders.determine_folders(categories, tags)

        self.repository.set_note_categories(note_id, categories)
        self.repository.set_note_tags(note_id, tags)
        self.repository.set_note_folders(note_id, folder_names)

        all_notes = self.repository.get_all_note_summaries()
        new_backlinks = self.backlinks.find_backlinks(note_id, title, content, all_notes)
        self.repository.set_backlinks(note_id, new_backlinks)

        self.repository.update_fts(
            note_id, title, content,
            " ".join(categories), " ".join(tags),
        )

    def get_stats(self, start: datetime | None = None, end: datetime | None = None):
        return self.repository.get_activity_stats(start, end)

    def get_categories(self):
        return self.repository.get_all_categories()

    def get_tags(self):
        return self.repository.get_all_tags()

    def get_folders(self):
        return self.repository.get_all_folders()

    def get_backlinks(self, note_id: int):
        return self.repository.get_backlinks_for_note(note_id)

    def rebuild_graph(
        self,
        show_notes: bool = True,
        show_categories: bool = True,
        show_tags: bool = False,
        layout: str = "spring",
    ):
        self.graph.set_layout(layout)
        return self.graph.build_graph(show_notes, show_categories, show_tags)

    def get_insights(self):
        return self.insights.compute()

    def get_collections(self):
        return self.collections.get_collections()

    def close(self) -> None:
        self.db.close()
