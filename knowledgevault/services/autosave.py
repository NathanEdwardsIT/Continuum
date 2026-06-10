"""Autosave manager for note editor."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal


class AutosaveManager(QObject):
    """Debounced autosave that triggers after user stops typing."""

    saved = Signal(int)  # note_id
    error = Signal(str)

    def __init__(self, interval_ms: int = 3000, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._interval = interval_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_save)
        self._save_callback: Callable[[], tuple[int | None, str, str]] | None = None
        self._dirty = False

    def set_save_callback(self, callback: Callable[[], tuple[int | None, str, str]]) -> None:
        self._save_callback = callback

    def mark_dirty(self) -> None:
        self._dirty = True
        self._timer.start(self._interval)

    def force_save(self) -> None:
        self._timer.stop()
        self._do_save()

    def _do_save(self) -> None:
        if not self._dirty or not self._save_callback:
            return
        try:
            note_id, title, content = self._save_callback()
            self._dirty = False
            if note_id is not None:
                self.saved.emit(note_id)
        except Exception as exc:
            self.error.emit(str(exc))

    @property
    def is_dirty(self) -> bool:
        return self._dirty
