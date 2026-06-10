"""Incremental schema migrations for existing databases."""

from __future__ import annotations

import sqlite3


MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "ALTER TABLE notes ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;",
    ),
    (
        3,
        "CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);",
    ),
    (
        4,
        "ALTER TABLE notes ADD COLUMN deleted_at TEXT;",
    ),
    (
        5,
        "ALTER TABLE notes ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0;",
    ),
    (
        6,
        "ALTER TABLE notes ADD COLUMN pinned_at TEXT;",
    ),
    (
        7,
        "ALTER TABLE notes ADD COLUMN organization_overrides TEXT NOT NULL DEFAULT '{}';",
    ),
    (
        8,
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            mime_type TEXT NOT NULL DEFAULT '',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_attachments_note ON attachments(note_id);
        """,
    ),
    (
        9,
        """
        CREATE TABLE IF NOT EXISTS category_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            keywords TEXT NOT NULL DEFAULT '[]',
            is_builtin INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, name)
        );
        CREATE INDEX IF NOT EXISTS idx_category_profiles_user ON category_profiles(user_id);
        """,
    ),
    (
        10,
        "CREATE INDEX IF NOT EXISTS idx_notes_deleted ON notes(deleted_at);",
    ),
    (
        11,
        "CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);",
    ),
]


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
        """
    )
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    current = row[0] if row else 0

    for version, sql in MIGRATIONS:
        if version <= current:
            continue
        try:
            conn.executescript(sql)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            row = (version,)
        else:
            conn.execute("UPDATE schema_version SET version = ?", (version,))
        current = version

    conn.commit()
