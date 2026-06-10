"""Automatic tag generation engine."""

from __future__ import annotations

from collections import Counter

from continuum.utils.text_processing import score_tag_candidates, tokenize


class TagEngine:
    """Extracts relevant tags from note content using corpus-aware scoring."""

    def generate_tags(
        self,
        title: str,
        content: str,
        *,
        corpus_doc_freq: Counter | None = None,
        num_docs: int = 1,
        exclude_keywords: set[str] | None = None,
        max_tags: int = 8,
    ) -> list[str]:
        """Generate tags from title and content with TF-IDF-style ranking."""
        return score_tag_candidates(
            title,
            content,
            corpus_doc_freq=corpus_doc_freq,
            num_docs=num_docs,
            exclude=exclude_keywords,
            max_tags=max_tags,
        )

    @staticmethod
    def build_corpus_frequencies(
        summaries: list[tuple[int, str, str]],
        *,
        exclude_note_id: int | None = None,
    ) -> tuple[Counter, int]:
        """Count how many notes each token appears in (document frequency)."""
        doc_freq: Counter[str] = Counter()
        doc_count = 0
        for note_id, title, content in summaries:
            if note_id == exclude_note_id:
                continue
            doc_count += 1
            tokens = set(tokenize(f"{title} {content}"))
            for token in tokens:
                doc_freq[token] += 1
        return doc_freq, max(doc_count, 1)
