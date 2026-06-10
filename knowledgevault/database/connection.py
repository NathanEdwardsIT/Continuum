"""Database connection management with recovery safeguards."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from continuum.config import ATTACHMENTS_DIR, BACKUP_DIR, DB_PATH
from continuum.database.migrations import run_migrations
from continuum.database.schema import FTS_TRIGGERS_SQL, SCHEMA_SQL


class DatabaseConnection:
    """Thread-safe SQLite connection wrapper."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._initialize()

    def _initialize(self) -> None:
        if not self.db_path.exists():
            self._create_schema()
            return
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1 FROM notes LIMIT 1")
            self._ensure_migrations()
        except sqlite3.DatabaseError:
            self._recover()

    def _create_schema(self) -> None:
        conn = self._get_connection()
        conn.executescript(SCHEMA_SQL)
        conn.executescript(FTS_TRIGGERS_SQL)
        run_migrations(conn)
        conn.commit()

    def _ensure_migrations(self) -> None:
        conn = self._get_connection()
        run_migrations(conn)

    def _recover(self) -> None:
        """Attempt recovery from corruption using latest backup."""
        corrupt_path = self.db_path.with_suffix(".corrupt")
        if self.db_path.exists():
            shutil.move(str(self.db_path), str(corrupt_path))

        backups = sorted(BACKUP_DIR.glob("vault_*.db"), reverse=True)
        if backups:
            shutil.copy2(str(backups[0]), str(self.db_path))
        else:
            self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self._get_connection()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params: list[tuple]) -> None:
        conn = self._get_connection()
        conn.executemany(sql, params)
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def integrity_check(self) -> bool:
        row = self.execute("PRAGMA integrity_check").fetchone()
        return row is not None and row[0] == "ok"

    def create_backup(self) -> Path:
        """Create a timestamped backup of the database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"vault_{timestamp}.db"
        if self._conn:
            self._conn.commit()
        shutil.copy2(str(self.db_path), str(backup_path))
        self._prune_backups()
        return backup_path

    def _prune_backups(self, max_backups: int = 10) -> None:
        backups = sorted(BACKUP_DIR.glob("vault_*.db"), reverse=True)
        for old in backups[max_backups:]:
            old.unlink(missing_ok=True)
