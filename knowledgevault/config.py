"""Application configuration and paths."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "KnowledgeVault"
APP_VERSION = "1.0.0"

# Default data directory in user's home
DATA_DIR = Path(os.environ.get("KNOWLEDGEVAULT_DATA", Path.home() / ".knowledgevault"))
DB_PATH = DATA_DIR / "vault.db"
BACKUP_DIR = DATA_DIR / "backups"

AUTOSAVE_INTERVAL_MS = 3000
BACKUP_INTERVAL_MS = 300_000  # 5 minutes
MAX_BACKUPS = 10

# Category keyword profiles (AI-free rule-based classification)
CATEGORY_PROFILES: dict[str, list[str]] = {
    "Programming": [
        "python", "javascript", "code", "function", "class", "api", "database",
        "algorithm", "debug", "git", "framework", "library", "variable", "loop",
        "compiler", "runtime", "typescript", "react", "sql", "docker", "kubernetes",
    ],
    "Finance": [
        "budget", "investment", "stock", "money", "expense", "income", "tax",
        "portfolio", "savings", "loan", "interest", "dividend", "accounting",
        "revenue", "profit", "cost", "financial", "bank", "credit", "debt",
    ],
    "Personal": [
        "family", "health", "hobby", "travel", "recipe", "journal", "diary",
        "friend", "home", "garden", "fitness", "meditation", "goal", "habit",
        "birthday", "vacation", "relationship", "self", "life", "wellness",
    ],
    "Education": [
        "learn", "study", "course", "lecture", "exam", "university", "school",
        "research", "thesis", "homework", "textbook", "professor", "degree",
        "tutorial", "lesson", "assignment", "academic", "science", "math",
    ],
    "Work": [
        "meeting", "project", "deadline", "client", "team", "manager", "task",
        "sprint", "deliverable", "presentation", "colleague", "office", "report",
        "milestone", "stakeholder", "workflow", "productivity", "quarterly",
    ],
}

STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "been", "be", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "need", "this", "that", "these", "those", "it", "its",
    "i", "you", "he", "she", "we", "they", "my", "your", "his", "her", "our",
    "their", "what", "which", "who", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "also", "now",
    "about", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here", "there",
    "any", "if", "because", "until", "while", "although", "though", "since",
    "being", "having", "doing", "get", "got", "make", "made", "like", "one", "two",
})
