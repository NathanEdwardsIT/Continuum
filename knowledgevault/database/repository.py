"""Data access layer for notes and related entities."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from continuum.config import TRASH_RETENTION_DAYS
from continuum.database.connection import DatabaseConnection
from continuum.models.entities import (
    ActivityStats,
    Attachment,
    Backlink,
    Category,
    CategoryProfile,
    Folder,
    Note,
    OrganizationOverrides,
    SearchFilters,
    Tag,
)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _format_dt(dt: datetime) -> str:
    return dt.isoformat()


class NoteRepository:
    """Repository for all note-related database operations."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._user_id: int | None = None

    def set_user_id(self, user_id: int | None) -> None:
        self._user_id = user_id

    def _active_clause(self, alias: str = "") -> str:
        col = f"{alias}deleted_at" if alias else "deleted_at"
        return f" AND {col} IS NULL"

    def _user_clause(self, alias: str = "") -> tuple[str, tuple]:
        if self._user_id is None:
            return "", ()
        col = f"{alias}user_id" if alias else "user_id"
        return f" AND {col} = ?", (self._user_id,)

    # ── Notes ──────────────────────────────────────────────────────────

    def create_note(self, title: str, content: str) -> Note:
        now = datetime.now()
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notes (user_id, title, content, created_at, modified_at, organization_overrides)
                VALUES (?, ?, ?, ?, ?, '{}')
                """,
                (self._user_id, title, content, _format_dt(now), _format_dt(now)),
            )
            note_id = cur.lastrowid
        return Note(id=note_id, title=title, content=content, created_at=now, modified_at=now)

    def update_note(self, note_id: int, title: str, content: str) -> Note:
        now = datetime.now()
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET title=?, content=?, modified_at=? WHERE id=?",
                (title, content, _format_dt(now), note_id),
            )
            cur.execute("SELECT created_at FROM notes WHERE id=?", (note_id,))
            row = cur.fetchone()
        created = _parse_dt(row["created_at"]) if row else now
        return Note(id=note_id, title=title, content=content, created_at=created, modified_at=now)

    def soft_delete_note(self, note_id: int) -> None:
        now = _format_dt(datetime.now())
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET deleted_at=?, pinned=0, pinned_at=NULL WHERE id=?",
                (now, note_id),
            )

    def restore_note(self, note_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET deleted_at=NULL WHERE id=?",
                (note_id,),
            )

    def permanently_delete_note(self, note_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id=?", (note_id,))

    def empty_trash(self) -> int:
        with self._db.cursor() as cur:
            clause, params = self._user_clause()
            cur.execute(
                f"DELETE FROM notes WHERE deleted_at IS NOT NULL{clause}",
                params,
            )
            return cur.rowcount

    def purge_old_trash(self) -> int:
        cutoff = datetime.now() - timedelta(days=TRASH_RETENTION_DAYS)
        with self._db.cursor() as cur:
            clause, params = self._user_clause()
            cur.execute(
                f"DELETE FROM notes WHERE deleted_at IS NOT NULL AND deleted_at < ?{clause}",
                (_format_dt(cutoff), *params),
            )
            return cur.rowcount

    def set_note_pinned(self, note_id: int, pinned: bool) -> None:
        now = _format_dt(datetime.now()) if pinned else None
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET pinned=?, pinned_at=? WHERE id=?",
                (1 if pinned else 0, now, note_id),
            )

    def update_organization_overrides(self, note_id: int, overrides: OrganizationOverrides) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET organization_overrides=? WHERE id=?",
                (overrides.to_json(), note_id),
            )

    def delete_note(self, note_id: int) -> None:
        self.soft_delete_note(note_id)

    def get_note(self, note_id: int, include_deleted: bool = False) -> Note | None:
        clause, params = self._user_clause()
        active = "" if include_deleted else self._active_clause()
        with self._db.cursor() as cur:
            cur.execute(f"SELECT * FROM notes WHERE id=?{clause}{active}", (note_id, *params))
            row = cur.fetchone()
        if not row:
            return None
        return self._hydrate_single(row)

    def get_all_notes(self, limit: int | None = None, offset: int = 0) -> list[Note]:
        clause, params = self._user_clause()
        sql = f"SELECT * FROM notes WHERE 1=1{clause}{self._active_clause()}{self._order_clause()}"
        if limit:
            sql += f" LIMIT {limit} OFFSET {offset}"
        with self._db.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def get_trash_notes(self) -> list[Note]:
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM notes WHERE deleted_at IS NOT NULL{clause} ORDER BY deleted_at DESC",
                params,
            )
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def get_title_index(self) -> dict[str, int]:
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(
                f"SELECT id, title FROM notes WHERE 1=1{clause}{self._active_clause()}",
                params,
            )
            return {r["title"].lower(): r["id"] for r in cur.fetchall() if r["title"]}

    def _order_clause(self) -> str:
        return " ORDER BY pinned DESC, pinned_at DESC, modified_at DESC"

    def search_notes(self, filters: SearchFilters, limit: int = 50) -> list[Note]:
        conditions: list[str] = ["n.deleted_at IS NULL"]
        params: list = []
        if self._user_id is not None:
            conditions.append("n.user_id = ?")
            params.append(self._user_id)
        if filters.category:
            conditions.append(
                "EXISTS (SELECT 1 FROM note_categories nc "
                "JOIN categories c ON nc.category_id = c.id "
                "WHERE nc.note_id = n.id AND c.name = ?)"
            )
            params.append(filters.category)
        if filters.tag:
            conditions.append(
                "EXISTS (SELECT 1 FROM note_tags nt "
                "JOIN tags t ON nt.tag_id = t.id "
                "WHERE nt.note_id = n.id AND t.name = ?)"
            )
            params.append(filters.tag)
        if filters.modified_after:
            conditions.append("n.modified_at >= ?")
            params.append(_format_dt(filters.modified_after))
        if filters.modified_before:
            conditions.append("n.modified_at <= ?")
            params.append(_format_dt(filters.modified_before))
        if filters.pinned_only:
            conditions.append("n.pinned = 1")
        q = filters.query.strip()
        if q:
            pattern = f"%{q}%"
            conditions.append("(n.title LIKE ? OR n.content LIKE ?)")
            params.extend([pattern, pattern])
        where = " AND ".join(conditions)
        sql = f"SELECT n.* FROM notes n WHERE {where}{self._order_clause()} LIMIT ?"
        params.append(limit)
        with self._db.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def get_notes_by_date_range(self, start: datetime, end: datetime) -> list[Note]:
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT * FROM notes
                WHERE created_at >= ? AND created_at <= ?{clause}{self._active_clause()}
                ORDER BY created_at
                """,
                (_format_dt(start), _format_dt(end), *params),
            )
            rows = cur.fetchall()
        notes = [self._row_to_note(r) for r in rows]
        for note in notes:
            assert note.id is not None
            note.categories = self._get_note_categories(note.id)
            note.tags = self._get_note_tags(note.id)
            note.folders = self._get_note_folders(note.id)
        return notes

    def get_notes_by_category(self, category_name: str) -> list[Note]:
        clause, params = self._user_clause("n.")
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT n.* FROM notes n
                JOIN note_categories nc ON n.id = nc.note_id
                JOIN categories c ON nc.category_id = c.id
                WHERE c.name = ?{clause}{self._active_clause('n.')}
                ORDER BY n.pinned DESC, n.modified_at DESC
                """,
                (category_name, *params),
            )
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def get_notes_by_folder(self, folder_name: str) -> list[Note]:
        clause, params = self._user_clause("n.")
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT n.* FROM notes n
                JOIN note_folders nf ON n.id = nf.note_id
                JOIN folders f ON nf.folder_id = f.id
                WHERE f.name = ?{clause}{self._active_clause('n.')}
                ORDER BY n.pinned DESC, n.modified_at DESC
                """,
                (folder_name, *params),
            )
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def get_notes_by_tag(self, tag_name: str) -> list[Note]:
        clause, params = self._user_clause("n.")
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT n.* FROM notes n
                JOIN note_tags nt ON n.id = nt.note_id
                JOIN tags t ON nt.tag_id = t.id
                WHERE t.name = ?{clause}{self._active_clause('n.')}
                ORDER BY n.pinned DESC, n.modified_at DESC
                """,
                (tag_name, *params),
            )
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def count_notes(self) -> int:
        clause, params = self._user_clause()
        row = self._db.execute(
            f"SELECT COUNT(*) FROM notes WHERE 1=1{clause}{self._active_clause()}",
            params,
        ).fetchone()
        return row[0] if row else 0

    # ── Categories ─────────────────────────────────────────────────────

    def set_note_categories(self, note_id: int, category_names: list[str]) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM note_categories WHERE note_id=?", (note_id,))
            for name in category_names:
                cat_id = self._ensure_category(cur, name)
                cur.execute(
                    "INSERT OR IGNORE INTO note_categories (note_id, category_id) VALUES (?, ?)",
                    (note_id, cat_id),
                )

    def get_all_categories(self) -> list[Category]:
        if self._user_id is None:
            join_filter = " AND (n.deleted_at IS NULL OR n.id IS NULL)"
            params: tuple = ()
        else:
            join_filter = " AND (n.deleted_at IS NULL OR n.id IS NULL) AND n.user_id = ?"
            params = (self._user_id,)
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT c.id, c.name, COUNT(nc.note_id) as cnt
                FROM categories c
                LEFT JOIN note_categories nc ON c.id = nc.category_id
                LEFT JOIN notes n ON nc.note_id = n.id{join_filter}
                GROUP BY c.id
                HAVING cnt > 0
                ORDER BY cnt DESC, c.name
                """,
                params,
            )
            return [Category(id=r["id"], name=r["name"], note_count=r["cnt"]) for r in cur.fetchall()]

    # ── Tags ───────────────────────────────────────────────────────────

    def set_note_tags(self, note_id: int, tag_names: list[str]) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM note_tags WHERE note_id=?", (note_id,))
            for name in tag_names:
                tag_id = self._ensure_tag(cur, name)
                cur.execute(
                    "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                    (note_id, tag_id),
                )

    def get_all_tags(self) -> list[Tag]:
        if self._user_id is None:
            join_filter = ""
            params: tuple = ()
        else:
            join_filter = " AND n.user_id = ?"
            params = (self._user_id,)
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT t.id, t.name, COUNT(nt.note_id) as cnt
                FROM tags t
                LEFT JOIN note_tags nt ON t.id = nt.tag_id
                LEFT JOIN notes n ON nt.note_id = n.id{join_filter}
                GROUP BY t.id
                HAVING cnt > 0
                ORDER BY cnt DESC, t.name
                """,
                params,
            )
            return [Tag(id=r["id"], name=r["name"], note_count=r["cnt"]) for r in cur.fetchall()]

    # ── Folders ────────────────────────────────────────────────────────

    def set_note_folders(self, note_id: int, folder_names: list[str]) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM note_folders WHERE note_id=?", (note_id,))
            for name in folder_names:
                folder_id = self._ensure_folder(cur, name)
                cur.execute(
                    "INSERT OR IGNORE INTO note_folders (note_id, folder_id) VALUES (?, ?)",
                    (note_id, folder_id),
                )

    def get_all_folders(self) -> list[Folder]:
        if self._user_id is None:
            join_filter = ""
            params: tuple = ()
        else:
            join_filter = " AND n.user_id = ?"
            params = (self._user_id,)
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT f.id, f.name, COUNT(nf.note_id) as cnt
                FROM folders f
                LEFT JOIN note_folders nf ON f.id = nf.folder_id
                LEFT JOIN notes n ON nf.note_id = n.id{join_filter}
                GROUP BY f.id
                HAVING cnt > 0
                ORDER BY cnt DESC, f.name
                """,
                params,
            )
            return [Folder(id=r["id"], name=r["name"], note_count=r["cnt"]) for r in cur.fetchall()]

    # ── Backlinks ──────────────────────────────────────────────────────

    def set_backlinks(self, note_id: int, backlinks: list[Backlink]) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "DELETE FROM backlinks WHERE source_note_id=? AND reason NOT LIKE 'Wiki link%'",
                (note_id,),
            )
            for bl in backlinks:
                if bl.source_note_id == bl.target_note_id:
                    continue
                cur.execute(
                    """
                    INSERT OR REPLACE INTO backlinks
                    (source_note_id, target_note_id, strength, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (bl.source_note_id, bl.target_note_id, bl.strength, bl.reason),
                )

    def set_wiki_backlinks(self, note_id: int, target_ids: list[int]) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "DELETE FROM backlinks WHERE source_note_id=? AND reason LIKE 'Wiki link%'",
                (note_id,),
            )
            for target_id in target_ids:
                if target_id == note_id:
                    continue
                cur.execute(
                    """
                    INSERT OR REPLACE INTO backlinks
                    (source_note_id, target_note_id, strength, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (note_id, target_id, 1.0, "Wiki link"),
                )

    def get_backlinks_for_note(self, note_id: int) -> list[tuple[Note, float, str]]:
        with self._db.cursor() as cur:
            cur.execute(
                """
                SELECT n.*, b.strength, b.reason FROM backlinks b
                JOIN notes n ON (
                    CASE WHEN b.source_note_id = ? THEN b.target_note_id
                         ELSE b.source_note_id END = n.id
                )
                WHERE b.source_note_id = ? OR b.target_note_id = ?
                """,
                (note_id, note_id, note_id),
            )
            rows = cur.fetchall()
        results = []
        for r in rows:
            note = self._row_to_note(r)
            results.append((note, r["strength"], r["reason"]))
        return results

    def get_all_backlinks(self) -> list[Backlink]:
        if self._user_id is None:
            clause = ""
            params: tuple = ()
        else:
            clause = """
                AND EXISTS (SELECT 1 FROM notes n1 WHERE n1.id = b.source_note_id AND n1.user_id = ?)
                AND EXISTS (SELECT 1 FROM notes n2 WHERE n2.id = b.target_note_id AND n2.user_id = ?)
            """
            params = (self._user_id, self._user_id)
        with self._db.cursor() as cur:
            cur.execute(f"SELECT * FROM backlinks b WHERE 1=1{clause}", params)
            return [
                Backlink(
                    source_note_id=r["source_note_id"],
                    target_note_id=r["target_note_id"],
                    strength=r["strength"],
                    reason=r["reason"],
                )
                for r in cur.fetchall()
            ]

    def count_backlinks(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM backlinks").fetchone()
        return row[0] if row else 0

    # ── FTS ────────────────────────────────────────────────────────────

    def update_fts(self, note_id: int, title: str, content: str, categories: str, tags: str) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notes_fts_content (note_id, title, content, categories, tags)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(note_id) DO UPDATE SET
                    title=excluded.title, content=excluded.content,
                    categories=excluded.categories, tags=excluded.tags
                """,
                (note_id, title, content, categories, tags),
            )

    # ── Stats ──────────────────────────────────────────────────────────

    def get_activity_stats(self, start: datetime | None = None, end: datetime | None = None) -> ActivityStats:
        total = self.count_notes()
        if start and end:
            notes_in_period = len(self.get_notes_by_date_range(start, end))
        else:
            notes_in_period = total

        categories = self.get_all_categories()
        tags = self.get_all_tags()
        backlinks = self.count_backlinks()

        most_cat = categories[0].name if categories else None
        most_tag = tags[0].name if tags else None

        return ActivityStats(
            total_notes=total,
            notes_in_period=notes_in_period,
            categories_count=len(categories),
            tags_count=len(tags),
            backlinks_count=backlinks,
            most_active_category=most_cat,
            most_used_tag=most_tag,
        )

    def get_all_note_summaries(self) -> list[tuple[int, str, str]]:
        """Lightweight fetch for backlink computation."""
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(
                f"SELECT id, title, content FROM notes WHERE 1=1{clause}{self._active_clause()}",
                params,
            )
            return [(r["id"], r["title"], r["content"]) for r in cur.fetchall()]

    # ── Attachments ────────────────────────────────────────────────────

    def add_attachment(
        self,
        note_id: int,
        user_id: int | None,
        filename: str,
        stored_name: str,
        mime_type: str,
        size_bytes: int,
    ) -> Attachment:
        now = datetime.now()
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attachments
                (note_id, user_id, filename, stored_name, mime_type, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, user_id, filename, stored_name, mime_type, size_bytes, _format_dt(now)),
            )
            att_id = cur.lastrowid
        return Attachment(
            id=att_id,
            note_id=note_id,
            user_id=user_id,
            filename=filename,
            stored_name=stored_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            created_at=now,
        )

    def get_attachments(self, note_id: int) -> list[Attachment]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT * FROM attachments WHERE note_id=? ORDER BY created_at",
                (note_id,),
            )
            return [self._row_to_attachment(r) for r in cur.fetchall()]

    def get_attachment(self, attachment_id: int) -> Attachment | None:
        row = self._db.execute(
            "SELECT * FROM attachments WHERE id=?",
            (attachment_id,),
        ).fetchone()
        return self._row_to_attachment(row) if row else None

    def delete_attachment(self, attachment_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))

    # ── Category profiles ──────────────────────────────────────────────

    def get_category_profiles(self, user_id: int) -> list[CategoryProfile]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT * FROM category_profiles WHERE user_id=? ORDER BY is_builtin DESC, name",
                (user_id,),
            )
            return [self._row_to_category_profile(r) for r in cur.fetchall()]

    def get_category_profile(self, profile_id: int) -> CategoryProfile | None:
        row = self._db.execute(
            "SELECT * FROM category_profiles WHERE id=?",
            (profile_id,),
        ).fetchone()
        return self._row_to_category_profile(row) if row else None

    def create_category_profile(
        self,
        user_id: int,
        name: str,
        keywords: list[str],
        is_builtin: bool = False,
    ) -> CategoryProfile:
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO category_profiles (user_id, name, keywords, is_builtin)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, name, json.dumps(keywords), 1 if is_builtin else 0),
            )
            pid = cur.lastrowid
        return CategoryProfile(id=pid, user_id=user_id, name=name, keywords=keywords, is_builtin=is_builtin)

    def update_category_profile(self, profile_id: int, name: str, keywords: list[str]) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE category_profiles SET name=?, keywords=? WHERE id=?",
                (name, json.dumps(keywords), profile_id),
            )

    def delete_category_profile(self, profile_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM category_profiles WHERE id=?", (profile_id,))

    # ── Helpers ────────────────────────────────────────────────────────

    def _hydrate_single(self, row) -> Note:
        note = self._row_to_note(row)
        assert note.id is not None
        note.categories = self._get_note_categories(note.id)
        note.tags = self._get_note_tags(note.id)
        note.folders = self._get_note_folders(note.id)
        note.attachment_count = len(self.get_attachments(note.id))
        return note

    def _row_to_note(self, row) -> Note:
        keys = row.keys()
        deleted = (
            _parse_dt(row["deleted_at"])
            if "deleted_at" in keys and row["deleted_at"]
            else None
        )
        pinned_at = (
            _parse_dt(row["pinned_at"])
            if "pinned_at" in keys and row["pinned_at"]
            else None
        )
        overrides_raw = row["organization_overrides"] if "organization_overrides" in keys else "{}"
        pinned = bool(row["pinned"]) if "pinned" in keys else False
        return Note(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            created_at=_parse_dt(row["created_at"]),
            modified_at=_parse_dt(row["modified_at"]),
            pinned=pinned,
            pinned_at=pinned_at,
            deleted_at=deleted,
            organization_overrides=OrganizationOverrides.from_json(overrides_raw),
        )

    def _row_to_attachment(self, row) -> Attachment:
        return Attachment(
            id=row["id"],
            note_id=row["note_id"],
            user_id=row["user_id"],
            filename=row["filename"],
            stored_name=row["stored_name"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            created_at=_parse_dt(row["created_at"]),
        )

    def _row_to_category_profile(self, row) -> CategoryProfile:
        keywords = json.loads(row["keywords"]) if row["keywords"] else []
        return CategoryProfile(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            keywords=keywords,
            is_builtin=bool(row["is_builtin"]),
        )

    def _hydrate_notes(self, rows) -> list[Note]:
        notes = [self._row_to_note(r) for r in rows]
        for note in notes:
            assert note.id is not None
            note.categories = self._get_note_categories(note.id)
            note.tags = self._get_note_tags(note.id)
            note.folders = self._get_note_folders(note.id)
            note.attachment_count = len(self.get_attachments(note.id))
        return notes

    def _get_note_categories(self, note_id: int) -> list[str]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT c.name FROM categories c JOIN note_categories nc ON c.id=nc.category_id WHERE nc.note_id=?",
                (note_id,),
            )
            return [r["name"] for r in cur.fetchall()]

    def _get_note_tags(self, note_id: int) -> list[str]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT t.name FROM tags t JOIN note_tags nt ON t.id=nt.tag_id WHERE nt.note_id=?",
                (note_id,),
            )
            return [r["name"] for r in cur.fetchall()]

    def _get_note_folders(self, note_id: int) -> list[str]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT f.name FROM folders f JOIN note_folders nf ON f.id=nf.folder_id WHERE nf.note_id=?",
                (note_id,),
            )
            return [r["name"] for r in cur.fetchall()]

    def _ensure_category(self, cur, name: str) -> int:
        cur.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        cur.execute("SELECT id FROM categories WHERE name=?", (name,))
        return cur.fetchone()["id"]

    def _ensure_tag(self, cur, name: str) -> int:
        cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        cur.execute("SELECT id FROM tags WHERE name=?", (name,))
        return cur.fetchone()["id"]

    def _ensure_folder(self, cur, name: str) -> int:
        cur.execute("INSERT OR IGNORE INTO folders (name) VALUES (?)", (name,))
        cur.execute("SELECT id FROM folders WHERE name=?", (name,))
        return cur.fetchone()["id"]
