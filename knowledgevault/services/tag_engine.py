"""Automatic tag generation engine."""

from __future__ import annotations

from continuum.utils.text_processing import extract_keywords, tokenize


class TagEngine:
    """Extracts relevant tags from note content automatically."""

    def generate_tags(self, title: str, content: str, max_tags: int = 8) -> list[str]:
        """Generate tags from title and content."""
        combined = f"{title}\n{title}\n{content}"
        keywords = extract_keywords(combined, max_keywords=max_tags + 4)

        # Also extract multi-word concepts from title
        title_tokens = tokenize(title)
        tags: list[str] = []

        for kw in keywords:
            if kw not in tags:
                tags.append(kw)

        for token in title_tokens:
            if token not in tags and len(tags) < max_tags:
                tags.append(token)

        return tags[:max_tags]
