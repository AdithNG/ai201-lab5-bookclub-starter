"""
tests/test_reading_service.py

Regression test for Bug 2: get_reading_history() must return finished books
most-recently-finished first. The two books below are deliberately arranged so
started_at order is the *opposite* of finished_at order — a started_at sort
(the original bug) would fail this test, a finished_at sort passes it.
"""

from datetime import datetime, timedelta, timezone

from models import User, Book, ReadingEvent
from services import reading_service


def test_history_most_recently_finished_first(db):
    user = User(username="reader", email="reader@bookclub.app")
    db.session.add(user)
    db.session.flush()

    now = datetime.now(timezone.utc)

    recent_finish = Book(
        title="Finished Most Recently", author="A", pages=100,
        genre="sci-fi", added_by=user.id,
    )
    earlier_finish = Book(
        title="Finished Earlier", author="B", pages=200,
        genre="sci-fi", added_by=user.id,
    )
    db.session.add_all([recent_finish, earlier_finish])
    db.session.flush()

    # recent_finish: started long ago, finished 1 day ago  -> should sort FIRST
    # earlier_finish: started more recently, finished 2 days ago -> sorts SECOND
    # (started_at order is reversed relative to finished_at, so the two sorts
    #  disagree and the test can tell them apart.)
    db.session.add_all(
        [
            ReadingEvent(
                user_id=user.id, book_id=recent_finish.id,
                started_at=now - timedelta(days=20),
                finished_at=now - timedelta(days=1),
            ),
            ReadingEvent(
                user_id=user.id, book_id=earlier_finish.id,
                started_at=now - timedelta(days=10),
                finished_at=now - timedelta(days=2),
            ),
        ]
    )
    db.session.commit()

    history = reading_service.get_reading_history(user.id)
    titles = [e.book.title for e in history]
    assert titles == ["Finished Most Recently", "Finished Earlier"]
