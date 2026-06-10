"""Attachment file storage."""

from __future__ import annotations

import mimetypes
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from continuum.config import ATTACHMENTS_DIR
from continuum.database.repository import NoteRepository
from continuum.models.entities import Attachment


class AttachmentService:
    def __init__(self, repository: NoteRepository, user_id: int | None) -> None:
        self._repo = repository
        self._user_id = user_id

    def set_user_id(self, user_id: int | None) -> None:
        self._user_id = user_id

    def add_attachment(self, note_id: int, source_path: Path) -> Attachment:
        if not source_path.exists():
            raise FileNotFoundError(str(source_path))
        stored_name = f"{uuid.uuid4().hex}{source_path.suffix.lower()}"
        dest_dir = ATTACHMENTS_DIR / str(self._user_id or 0) / str(note_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / stored_name
        shutil.copy2(source_path, dest_path)
        mime, _ = mimetypes.guess_type(source_path.name)
        return self._repo.add_attachment(
            note_id=note_id,
            user_id=self._user_id,
            filename=source_path.name,
            stored_name=stored_name,
            mime_type=mime or "application/octet-stream",
            size_bytes=dest_path.stat().st_size,
        )

    def get_attachments(self, note_id: int) -> list[Attachment]:
        return self._repo.get_attachments(note_id)

    def get_file_path(self, attachment: Attachment) -> Path:
        return (
            ATTACHMENTS_DIR
            / str(attachment.user_id or 0)
            / str(attachment.note_id)
            / attachment.stored_name
        )

    def remove_attachment(self, attachment_id: int) -> None:
        attachment = self._repo.get_attachment(attachment_id)
        if attachment:
            path = self.get_file_path(attachment)
            path.unlink(missing_ok=True)
            self._repo.delete_attachment(attachment_id)

    def open_attachment(self, attachment: Attachment) -> Path:
        path = self.get_file_path(attachment)
        if not path.exists():
            raise FileNotFoundError(path)
        return path
