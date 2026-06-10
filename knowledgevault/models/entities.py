"""Domain entity dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    NOTE = "note"
    TAG = "tag"
    CATEGORY = "category"


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

    @property
    def preview(self) -> str:
        text = self.content.replace("\n", " ").strip()
        return text[:120] + ("…" if len(text) > 120 else "")


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
