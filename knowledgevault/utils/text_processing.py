"""Text processing utilities for categorization, tagging, and similarity."""

from __future__ import annotations

import re
from collections import Counter

from continuum.config import CATEGORY_PROFILES, STOP_WORDS


def tokenize(text: str) -> list[str]:
    """Lowercase tokenization with basic punctuation stripping."""
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def extract_keywords(text: str, max_keywords: int = 12) -> list[str]:
    """Extract top keywords from text using frequency analysis."""
    tokens = tokenize(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    # Boost tokens that appear in title-like positions (first line)
    first_line = text.split("\n", 1)[0] if text else ""
    for token in tokenize(first_line):
        counts[token] += 2
    return [word for word, _ in counts.most_common(max_keywords)]


def score_categories(
    text: str,
    profiles: dict[str, list[str]] | None = None,
    min_score: float = 0.15,
) -> list[str]:
    """Score text against category keyword profiles."""
    profiles = profiles or CATEGORY_PROFILES
    tokens = set(tokenize(text))
    if not tokens:
        return ["Personal"]

    scores: dict[str, float] = {}
    for category, keywords in profiles.items():
        keyword_set = set(keywords)
        overlap = len(tokens & keyword_set)
        if overlap > 0:
            scores[category] = overlap / len(keyword_set)

    if not scores:
        return ["Personal"]

    max_score = max(scores.values())
    threshold = max(min_score, max_score * 0.5)
    matched = [cat for cat, score in scores.items() if score >= threshold]
    return sorted(matched, key=lambda c: scores[c], reverse=True)[:3]


def jaccard_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def compute_similarity(text_a: str, text_b: str) -> float:
    """Compute content similarity between two texts."""
    tokens_a = set(tokenize(text_a))
    tokens_b = set(tokenize(text_b))
    return jaccard_similarity(tokens_a, tokens_b)
