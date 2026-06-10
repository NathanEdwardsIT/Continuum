"""Automatic categorization engine."""

from __future__ import annotations

from continuum.config import CATEGORY_PROFILES
from continuum.utils.text_processing import score_categories


class CategorizationEngine:
    """Rule-based automatic category assignment."""

    def categorize(
        self,
        title: str,
        content: str,
        profiles: dict[str, list[str]] | None = None,
    ) -> list[str]:
        combined = f"{title}\n{content}"
        return score_categories(combined, profiles or CATEGORY_PROFILES)
