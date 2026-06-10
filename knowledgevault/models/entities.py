"""Domain entity dataclasses."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    NOTE = "note"
    TAG = "tag"
    CATEGORY = "category"


@dataclass
class OrganizationOverrides:
    locked_categories: list[str] = field(default_factory=list)
    removed_categories: list[str] = field(default_factory=list)
    added_tags: list[str] = field(default_factory=list)
    removed_tags: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "locked_categories": self.locked_categories,
            "removed_categories": self.removed_categories,
            "added_tags": self.added_tags,
            "removed_tags": self.removed_tags,
        })

    @classmethod
    def from_json(cls, raw: str | None) -> OrganizationOverrides:
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return cls()
        return cls(
            locked_categories=list(data.get("locked_categories", [])),
            removed_categories=list(data.get("removed_categories", [])),
            added_tags=list(data.get("added_tags", [])),
            removed_tags=list(data.get("removed_tags", [])),
        )


@dataclass
class Note:
    id: int | None
    title: str
    content: str
    created_at: datetime
    modified_at: datetime
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)
    pinned: bool = False
    pinned_at: datetime | None = None
    deleted_at: datetime | None = None
    organization_overrides: OrganizationOverrides = field(default_factory=OrganizationOverrides)
    attachment_count: int = 0

    @property
    def preview(self) -> str:
        text = self.content.replace("\n", " ").strip()
        return text[:120] + ("…" if len(text) > 120 else "")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


@dataclass
class Attachment:
    id: int | None
    note_id: int
    user_id: int | None
    filename: str
    stored_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


@dataclass
class CategoryProfile:
    id: int | None
    user_id: int | None
    name: str
    keywords: list[str]
    is_builtin: bool = False


@dataclass
class Category:
    id: int | None
    name: str
    note_count: int = 0


@dataclass
class Tag:
    id: int | None
    name: str
    note_count: int = 0


@dataclass
class Folder:
    id: int | None
    name: str
    note_count: int = 0


@dataclass
class Backlink:
    source_note_id: int
    target_note_id: int
    strength: float
    reason: str


@dataclass
class SearchResult:
    note_id: int
    title: str
    snippet: str
    rank: float
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class SearchFilters:
    query: str = ""
    category: str | None = None
    tag: str | None = None
    modified_after: datetime | None = None
    modified_before: datetime | None = None
    pinned_only: bool = False


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: NodeType
    size: float = 1.0


@dataclass
class GraphEdge:
    source: str
    target: str
    weight: float = 1.0
    edge_type: str = "backlink"


@dataclass
class ActivityStats:
    total_notes: int
    notes_in_period: int
    categories_count: int
    tags_count: int
    backlinks_count: int
    most_active_category: str | None
    most_used_tag: str | None


@dataclass
class ReportData:
    start_date: datetime
    end_date: datetime
    notes: list[Note]
    stats: ActivityStats
    category_breakdown: dict[str, int]
    tag_breakdown: dict[str, int]
    connections: list[tuple[str, str, float]]
