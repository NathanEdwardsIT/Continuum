"""Data access layer for notes and related entities."""

from __future__ import annotations

from datetime import datetime

from knowledgevault.database.connection import DatabaseConnection
from knowledgevault.models.entities import (
    ActivityStats,
    Backlink,
    Category,
    Folder,
    Note,
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
                INSERT INTO notes (user_id, title, content, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?)
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

    def delete_note(self, note_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id=?", (note_id,))

    def get_note(self, note_id: int) -> Note | None:
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(f"SELECT * FROM notes WHERE id=?{clause}", (note_id, *params))
            row = cur.fetchone()
        if not row:
            return None
        note = self._row_to_note(row)
        note.categories = self._get_note_categories(note_id)
        note.tags = self._get_note_tags(note_id)
        note.folders = self._get_note_folders(note_id)
        return note

    def get_all_notes(self, limit: int | None = None, offset: int = 0) -> list[Note]:
        clause, params = self._user_clause()
        sql = f"SELECT * FROM notes WHERE 1=1{clause} ORDER BY modified_at DESC"
        if limit:
            sql += f" LIMIT {limit} OFFSET {offset}"
        with self._db.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        notes = [self._row_to_note(r) for r in rows]
        for note in notes:
            assert note.id is not None
            note.categories = self._get_note_categories(note.id)
            note.tags = self._get_note_tags(note.id)
            note.folders = self._get_note_folders(note.id)
        return notes

    def get_notes_by_date_range(self, start: datetime, end: datetime) -> list[Note]:
        clause, params = self._user_clause()
        with self._db.cursor() as cur:
            cur.execute(
                f"""
                SELECT * FROM notes
                WHERE created_at >= ? AND created_at <= ?{clause}
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
                WHERE c.name = ?{clause}
                ORDER BY n.modified_at DESC
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
                WHERE f.name = ?{clause}
                ORDER BY n.modified_at DESC
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
                WHERE t.name = ?{clause}
                ORDER BY n.modified_at DESC
                """,
                (tag_name, *params),
            )
            rows = cur.fetchall()
        return self._hydrate_notes(rows)

    def count_notes(self) -> int:
        clause, params = self._user_clause()
        row = self._db.execute(f"SELECT COUNT(*) FROM notes WHERE 1=1{clause}", params).fetchone()
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
            join_filter = ""
            params: tuple = ()
        else:
            join_filter = " AND n.user_id = ?"
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
            cur.execute("DELETE FROM backlinks WHERE source_note_id=?", (note_id,))
            for bl in backlinks:
                if bl.source_note_id == bl.target_note_id:
                    continue
                cur.execute(
                    "INSERT OR REPLACE INTO backlinks (source_note_id, target_note_id, strength, reason) VALUES (?, ?, ?, ?)",
                    (bl.source_note_id, bl.target_note_id, bl.strength, bl.reason),
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
            cur.execute(f"SELECT id, title, content FROM notes WHERE 1=1{clause}", params)
            return [(r["id"], r["title"], r["content"]) for r in cur.fetchall()]

    # ── Helpers ────────────────────────────────────────────────────────

    def _row_to_note(self, row) -> Note:
        return Note(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            created_at=_parse_dt(row["created_at"]),
            modified_at=_parse_dt(row["modified_at"]),
        )

    def _hydrate_notes(self, rows) -> list[Note]:
        notes = [self._row_to_note(r) for r in rows]
        for note in notes:
            assert note.id is not None
            note.categories = self._get_note_categories(note.id)
            note.tags = self._get_note_tags(note.id)
            note.folders = self._get_note_folders(note.id)
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
