"""Automatic categorization engine."""

from __future__ import annotations

from knowledgevault.utils.text_processing import score_categories


class CategorizationEngine:
    """Rule-based automatic category assignment."""

    def categorize(self, title: str, content: str) -> list[str]:
        """Determine categories from note title and content."""
        combined = f"{title}\n{content}"
        return score_categories(combined)
