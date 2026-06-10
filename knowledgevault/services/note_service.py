"""Central note service orchestrating all automatic organization."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from continuum.database.connection import DatabaseConnection
from continuum.database.repository import NoteRepository
from continuum.models.entities import Note, OrganizationOverrides, SearchFilters
from continuum.services.attachment_service import AttachmentService
from continuum.services.backlink_engine import BacklinkEngine
from continuum.services.categorization import CategorizationEngine
from continuum.services.category_profile_service import CategoryProfileService
from continuum.services.folder_engine import FolderEngine
from continuum.services.collections_engine import CollectionsEngine
from continuum.services.graph_engine import GraphEngine
from continuum.services.insights_engine import InsightsEngine
from continuum.services.search_engine import SearchEngine
from continuum.services.tag_engine import TagEngine
from continuum.utils.wiki_links import extract_wiki_links, resolve_wiki_targets


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
        self.categories = CategoryProfileService(self.repository, user_id)
        self.attachments = AttachmentService(self.repository, user_id)
        self._user_id = user_id
        if user_id is not None:
            self.categories.ensure_defaults()
            self.repository.purge_old_trash()

    def set_user_id(self, user_id: int | None) -> None:
        self._user_id = user_id
        self.repository.set_user_id(user_id)
        self.categories.set_user_id(user_id)
        self.attachments.set_user_id(user_id)
        if user_id is not None:
            self.categories.ensure_defaults()

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

    def move_to_trash(self, note_id: int) -> None:
        self.repository.soft_delete_note(note_id)

    def restore_note(self, note_id: int) -> None:
        self.repository.restore_note(note_id)

    def permanently_delete(self, note_id: int) -> None:
        for att in self.repository.get_attachments(note_id):
            self.attachments.remove_attachment(att.id or 0)
        self.repository.permanently_delete_note(note_id)

    def empty_trash(self) -> int:
        notes = self.repository.get_trash_notes()
        for note in notes:
            if note.id:
                self.permanently_delete(note.id)
        return len(notes)

    def get_trash_notes(self) -> list[Note]:
        return self.repository.get_trash_notes()

    def set_pinned(self, note_id: int, pinned: bool) -> None:
        self.repository.set_note_pinned(note_id, pinned)

    def update_overrides(self, note_id: int, overrides: OrganizationOverrides) -> Note | None:
        self.repository.update_organization_overrides(note_id, overrides)
        note = self.repository.get_note(note_id)
        if note:
            self._organize_note(note_id, note.title, note.content)
        return self.repository.get_note(note_id)

    def add_attachment(self, note_id: int, source_path: Path):
        return self.attachments.add_attachment(note_id, source_path)

    def get_attachments(self, note_id: int):
        return self.attachments.get_attachments(note_id)

    def remove_attachment(self, attachment_id: int) -> None:
        self.attachments.remove_attachment(attachment_id)

    def open_attachment(self, attachment):
        return self.attachments.open_attachment(attachment)

    def delete_note(self, note_id: int) -> None:
        self.move_to_trash(note_id)

    def get_note(self, note_id: int) -> Note | None:
        return self.repository.get_note(note_id)

    def get_all_notes(self, limit: int | None = None) -> list[Note]:
        return self.repository.get_all_notes(limit=limit)

    def search_filtered(self, filters: SearchFilters) -> list[Note]:
        return self.repository.search_notes(filters)

    def get_notes_by_filter(self, filter_type: str, filter_value: str) -> list[Note]:
        if filter_type == "category":
            return self.repository.get_notes_by_category(filter_value)
        if filter_type == "folder":
            return self.repository.get_notes_by_folder(filter_value)
        if filter_type == "tag":
            return self.repository.get_notes_by_tag(filter_value)
        if filter_type == "trash":
            return self.repository.get_trash_notes()
        if filter_type == "pinned":
            return self.repository.search_notes(SearchFilters(pinned_only=True))
        return self.repository.get_all_notes()

    def _organize_note(self, note_id: int, title: str, content: str) -> None:
        note = self.repository.get_note(note_id)
        if not note or note.is_deleted:
            return

        overrides = note.organization_overrides
        profiles = self.categories.get_profile_map()
        auto_categories = self.categorization.categorize(title, content, profiles)
        auto_tags = self.tags.generate_tags(title, content)

        categories = [c for c in auto_categories if c not in overrides.removed_categories]
        for locked in overrides.locked_categories:
            if locked not in categories:
                categories.append(locked)
        categories = list(dict.fromkeys(categories))

        tags = [t for t in auto_tags if t not in overrides.removed_tags]
        for added in overrides.added_tags:
            if added not in tags:
                tags.append(added)

        folder_names = self.folders.determine_folders(categories, tags)
        self.repository.set_note_categories(note_id, categories)
        self.repository.set_note_tags(note_id, tags)
        self.repository.set_note_folders(note_id, folder_names)

        all_notes = self.repository.get_all_note_summaries()
        similarity_links = self.backlinks.find_backlinks(note_id, title, content, all_notes)
        self.repository.set_backlinks(note_id, similarity_links)

        wiki_targets = extract_wiki_links(content)
        title_index = self.repository.get_title_index()
        resolved = resolve_wiki_targets(wiki_targets, title_index)
        self.repository.set_wiki_backlinks(note_id, [nid for nid, _ in resolved])

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
