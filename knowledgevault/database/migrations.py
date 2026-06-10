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
