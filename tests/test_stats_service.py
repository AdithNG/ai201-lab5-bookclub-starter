"""
tests/test_stats_service.py

Regression test for Bug 1: calculate_streak() must count consecutive days on
which books were *finished*. This test would have failed against the original
code, which built its date set from started_at.
"""

from datetime import datetime, timedelta, timezone

from models import User, Book, ReadingEvent
from services import stats_service


def test_calculate_streak_three_consecutive_days(db):
    user = User(username="tester", email="tester@bookclub.app")
    db.session.add(user)
    db.session.flush()

    now = datetime.now(timezone.utc)

    # Three books finished on three consecutive days: today, yesterday, two days
    # ago. started_at is set far in the past so a started_at-based streak would
    # (wrongly) return something other than 3.
    for i in range(3):
        book = Book(
            title=f"Book {i}",
            author="Author",
            pages=100,
            genre="sci-fi",
            added_by=user.id,
        )
        db.session.add(book)
        db.session.flush()
        db.session.add(
            ReadingEvent(
                user_id=user.id,
                book_id=book.id,
                started_at=now - timedelta(days=30 + i),
                finished_at=now - timedelta(days=i),
            )
        )
    db.session.commit()

    # Resolve dates in UTC so the assertion is independent of the machine's zone.
    assert stats_service.calculate_streak(user.id, tz=timezone.utc) == 3
