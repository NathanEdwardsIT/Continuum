"""Text processing utilities for categorization, tagging, and similarity."""

from __future__ import annotations

import re
from collections import Counter

import math

from continuum.config import CATEGORY_PROFILES, STOP_WORDS, TAG_STOP_WORDS


def tokenize(text: str) -> list[str]:
    """Lowercase tokenization with basic punctuation stripping."""
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def _is_valid_tag(token: str) -> bool:
    if token in TAG_STOP_WORDS:
        return False
    if token.isdigit() and len(token) < 4:
        return False
    return True


def extract_bigrams(text: str) -> list[str]:
    """Extract adjacent token pairs as hyphenated tag candidates."""
    tokens = tokenize(text)
    return [f"{tokens[i]}-{tokens[i + 1]}" for i in range(len(tokens) - 1)]


def score_tag_candidates(
    title: str,
    content: str,
    *,
    corpus_doc_freq: Counter | None = None,
    num_docs: int = 1,
    exclude: set[str] | None = None,
    max_tags: int = 8,
) -> list[str]:
    """Rank tag candidates with TF-IDF-style scoring and title emphasis."""
    exclude = exclude or set()
    corpus_doc_freq = corpus_doc_freq or Counter()
    scores: Counter[str] = Counter()

    title_tokens = tokenize(title)
    content_tokens = tokenize(content)

    for token in title_tokens:
        if _is_valid_tag(token) and token not in exclude:
            scores[token] += 4.0
    for bigram in extract_bigrams(title):
        if bigram not in exclude:
            scores[bigram] += 6.0

    content_counts = Counter(content_tokens)
    for token, count in content_counts.items():
        if not _is_valid_tag(token) or token in exclude:
            continue
        if count < 2 and token not in title_tokens:
            continue
        tf = 1.0 + math.log1p(count)
        df = corpus_doc_freq.get(token, 0)
        idf = math.log((num_docs + 1) / (df + 1)) + 1.0
        title_boost = 2.0 if token in title_tokens else 1.0
        scores[token] += tf * idf * title_boost

    if not scores:
        return [t for t in title_tokens if _is_valid_tag(t) and t not in exclude][:max_tags]

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    max_score = ranked[0][1]
    threshold = max(max_score * 0.35, 1.5)
    return [word for word, score in ranked if score >= threshold][:max_tags]


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
