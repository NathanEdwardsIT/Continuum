"""FTS5-powered search engine."""

from __future__ import annotations

import re

from continuum.database.repository import NoteRepository
from continuum.models.entities import SearchFilters, SearchResult


class SearchEngine:
    """Fast full-text search across notes, categories, and tags."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def search_with_filters(self, filters: SearchFilters, limit: int = 50) -> list[SearchResult]:
        """Search with optional text query (FTS5) plus category/tag/date/pinned filters."""
        q = filters.query.strip()
        if not q:
            notes = self._repo.search_notes(filters, limit=limit)
            return [
                SearchResult(
                    note_id=n.id or 0,
                    title=n.title,
                    snippet=n.preview,
                    rank=0.0,
                    categories=n.categories,
                    tags=n.tags,
                )
                for n in notes
            ]

        fts_query = self._build_fts_query(q)
        candidates = self._fts_search(fts_query, limit * 3)
        if not candidates:
            candidates = self._like_search(q, limit * 3)

        results: list[SearchResult] = []
        for r in candidates:
            note = self._repo.get_note(r.note_id)
            if not note or note.is_deleted:
                continue
            if filters.category and filters.category not in note.categories:
                continue
            if filters.tag and filters.tag.lower() not in [t.lower() for t in note.tags]:
                continue
            if filters.pinned_only and not note.pinned:
                continue
            if filters.modified_after and note.modified_at < filters.modified_after:
                continue
            if filters.modified_before and note.modified_at > filters.modified_before:
                continue
            results.append(r)
            if len(results) >= limit:
                break
        return results

    def search(self, query: str, limit: int = 50) -> list[SearchResult]:
        """Search notes using FTS5 with fallback to LIKE."""
        query = query.strip()
        if not query:
            return self._recent_notes(limit)

        fts_query = self._build_fts_query(query)
        results = self._fts_search(fts_query, limit)

        if not results:
            results = self._like_search(query, limit)

        return results

    def _build_fts_query(self, query: str) -> str:
        tokens = re.findall(r"\w+", query.lower())
        if not tokens:
            return query
        return " ".join(f'"{t}"*' for t in tokens)

    def _fts_search(self, fts_query: str, limit: int) -> list[SearchResult]:
        clause, params = self._repo._user_clause("n.")
        try:
            with self._repo._db.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        n.id, n.title,
                        snippet(notes_fts, 1, '<b>', '</b>', '…', 20) as snippet,
                        -rank as rank
                    FROM notes_fts
                    JOIN notes n ON notes_fts.rowid = n.id
                    WHERE notes_fts MATCH ? AND n.deleted_at IS NULL{clause}
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, *params, limit),
                )
                rows = cur.fetchall()
        except Exception:
            return []

        return self._rows_to_results(rows)

    def _like_search(self, query: str, limit: int) -> list[SearchResult]:
        pattern = f"%{query}%"
        clause, params = self._repo._user_clause()
        with self._repo._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, title, content FROM notes
                WHERE (title LIKE ? OR content LIKE ?){clause}{self._repo._active_clause()}
                ORDER BY pinned DESC, modified_at DESC LIMIT ?
                """,
                (pattern, pattern, *params, limit),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            snippet = self._make_snippet(r["content"], query)
            note_id = r["id"]
            results.append(
                SearchResult(
                    note_id=note_id,
                    title=r["title"],
                    snippet=snippet,
                    rank=0.5,
                    categories=self._repo._get_note_categories(note_id),
                    tags=self._repo._get_note_tags(note_id),
                )
            )
        return results

    def _recent_notes(self, limit: int) -> list[SearchResult]:
        notes = self._repo.get_all_notes(limit=limit)
        return [
            SearchResult(
                note_id=n.id or 0,
                title=n.title,
                snippet=n.preview,
                rank=0.0,
                categories=n.categories,
                tags=n.tags,
            )
            for n in notes
        ]

    def _rows_to_results(self, rows) -> list[SearchResult]:
        results = []
        for r in rows:
            note_id = r["id"]
            results.append(
                SearchResult(
                    note_id=note_id,
                    title=r["title"],
                    snippet=r["snippet"],
                    rank=r["rank"],
                    categories=self._repo._get_note_categories(note_id),
                    tags=self._repo._get_note_tags(note_id),
                )
            )
        return results

    @staticmethod
    def _make_snippet(content: str, query: str, context: int = 60) -> str:
        lower = content.lower()
        idx = lower.find(query.lower())
        if idx == -1:
            text = content[:120]
            return text + ("…" if len(content) > 120 else "")
        start = max(0, idx - context)
        end = min(len(content), idx + len(query) + context)
        snippet = content[start:end]
        if start > 0:
            snippet = "…" + snippet
        if end < len(content):
            snippet += "…"
        return snippet
