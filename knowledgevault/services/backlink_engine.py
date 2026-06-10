"""Automatic backlink creation engine."""

from __future__ import annotations

from continuum.models.entities import Backlink
from continuum.utils.text_processing import compute_similarity, tokenize


class BacklinkEngine:
    """Creates backlinks between related notes based on content similarity."""

    MIN_SIMILARITY = 0.08
    MAX_BACKLINKS = 15

    def find_backlinks(
        self,
        note_id: int,
        title: str,
        content: str,
        all_notes: list[tuple[int, str, str]],
    ) -> list[Backlink]:
        """Find related notes and create bidirectional backlink entries."""
        combined = f"{title}\n{content}"
        note_tokens = set(tokenize(combined))
        candidates: list[Backlink] = []

        for other_id, other_title, other_content in all_notes:
            if other_id == note_id:
                continue

            other_combined = f"{other_title}\n{other_content}"
            similarity = compute_similarity(combined, other_combined)

            # Boost if titles share tokens
            title_overlap = len(set(tokenize(title)) & set(tokenize(other_title)))
            if title_overlap > 0:
                similarity += title_overlap * 0.05

            # Boost for shared significant tokens
            shared = note_tokens & set(tokenize(other_combined))
            if len(shared) >= 3:
                similarity += 0.05

            if similarity >= self.MIN_SIMILARITY:
                shared_words = sorted(shared)[:5]
                reason = f"Shared: {', '.join(shared_words)}" if shared_words else "Related content"
                candidates.append(
                    Backlink(
                        source_note_id=note_id,
                        target_note_id=other_id,
                        strength=round(min(similarity, 1.0), 3),
                        reason=reason,
                    )
                )

        candidates.sort(key=lambda b: b.strength, reverse=True)
        return candidates[: self.MAX_BACKLINKS]
