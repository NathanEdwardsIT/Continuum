"""Periodic backup service."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from knowledgevault.database.connection import DatabaseConnection


class BackupService(QObject):
    """Manages periodic database backups."""

    backup_created = Signal(str)  # backup path

    def __init__(
        self,
        db: DatabaseConnection,
        interval_ms: int = 300_000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.create_backup)
        self._timer.start(interval_ms)

    def create_backup(self) -> Path:
        path = self._db.create_backup()
        self.backup_created.emit(str(path))
        return path

    def stop(self) -> None:
        self._timer.stop()
