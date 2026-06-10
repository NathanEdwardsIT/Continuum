"""Writing insights and activity analytics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from continuum.database.repository import NoteRepository


@dataclass
class DayActivity:
    date: datetime
    note_count: int
    word_count: int


@dataclass
class WritingInsights:
    total_words: int
    notes_this_week: int
    notes_today: int
    avg_words_per_note: int
    busiest_category: str | None
    writing_streak_days: int
    daily_activity: list[DayActivity] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)


class InsightsEngine:
    """Computes writing analytics from note data."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def compute(self, days: int = 90) -> WritingInsights:
        notes = self._repo.get_all_notes()
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_words = 0
        notes_this_week = 0
        notes_today = 0
        cat_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        daily: dict[str, DayActivity] = {}

        for note in notes:
            words = len(note.content.split())
            total_words += words

            if note.created_at >= week_ago:
                notes_this_week += 1
            if note.created_at >= today_start:
                notes_today += 1

            cat_counter.update(note.categories)
            tag_counter.update(note.tags)

            day_key = note.created_at.strftime("%Y-%m-%d")
            if day_key not in daily:
                daily[day_key] = DayActivity(
                    date=note.created_at.replace(hour=0, minute=0, second=0, microsecond=0),
                    note_count=0,
                    word_count=0,
                )
            daily[day_key].note_count += 1
            daily[day_key].word_count += words

        # Build heatmap range
        activity_list: list[DayActivity] = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            key = d.strftime("%Y-%m-%d")
            activity_list.append(
                daily.get(key, DayActivity(date=d, note_count=0, word_count=0))
            )

        streak = self._compute_streak(activity_list)
        avg = total_words // max(len(notes), 1)

        return WritingInsights(
            total_words=total_words,
            notes_this_week=notes_this_week,
            notes_today=notes_today,
            avg_words_per_note=avg,
            busiest_category=cat_counter.most_common(1)[0][0] if cat_counter else None,
            writing_streak_days=streak,
            daily_activity=activity_list,
            top_tags=tag_counter.most_common(8),
        )

    @staticmethod
    def _compute_streak(activity: list[DayActivity]) -> int:
        streak = 0
        for day in reversed(activity):
            if day.note_count > 0:
                streak += 1
            else:
                break
        return streak
