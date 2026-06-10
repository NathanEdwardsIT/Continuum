"""User-defined category profile management."""

from __future__ import annotations

import json

from continuum.config import CATEGORY_PROFILES
from continuum.database.repository import NoteRepository
from continuum.models.entities import CategoryProfile


class CategoryProfileService:
    def __init__(self, repository: NoteRepository, user_id: int | None = None) -> None:
        self._repo = repository
        self._user_id = user_id

    def set_user_id(self, user_id: int | None) -> None:
        self._user_id = user_id

    def ensure_defaults(self) -> None:
        if self._user_id is None:
            return
        existing = {p.name for p in self._repo.get_category_profiles(self._user_id)}
        for name, keywords in CATEGORY_PROFILES.items():
            if name not in existing:
                self._repo.create_category_profile(
                    self._user_id, name, keywords, is_builtin=True
                )

    def get_profiles(self) -> list[CategoryProfile]:
        if self._user_id is None:
            return [
                CategoryProfile(id=None, user_id=None, name=n, keywords=k, is_builtin=True)
                for n, k in CATEGORY_PROFILES.items()
            ]
        self.ensure_defaults()
        return self._repo.get_category_profiles(self._user_id)

    def get_profile_map(self) -> dict[str, list[str]]:
        return {p.name: p.keywords for p in self.get_profiles()}

    def add_profile(self, name: str, keywords: list[str]) -> CategoryProfile:
        assert self._user_id is not None
        return self._repo.create_category_profile(self._user_id, name, keywords, is_builtin=False)

    def update_profile(self, profile_id: int, name: str, keywords: list[str]) -> None:
        self._repo.update_category_profile(profile_id, name, keywords)

    def delete_profile(self, profile_id: int) -> None:
        profile = self._repo.get_category_profile(profile_id)
        if profile and profile.is_builtin:
            raise ValueError("Built-in categories cannot be deleted.")
        self._repo.delete_category_profile(profile_id)

    @staticmethod
    def keywords_to_text(keywords: list[str]) -> str:
        return ", ".join(keywords)

    @staticmethod
    def text_to_keywords(text: str) -> list[str]:
        return [k.strip().lower() for k in text.split(",") if k.strip()]

    @staticmethod
    def serialize_keywords(keywords: list[str]) -> str:
        return json.dumps(keywords)
