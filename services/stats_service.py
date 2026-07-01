"""
services/stats_service.py — BookClub

Computes reading statistics for a user: streak, books finished this month,
and total pages read.
"""

from datetime import date, datetime, timezone
from services import reading_service


def _local_date(dt: datetime, tz: timezone) -> date:
    """
    Convert a stored timestamp to a calendar date in the given timezone.

    finished_at values are written as UTC but come back from SQLite as naive
    datetimes (the tzinfo is dropped on round-trip). We therefore treat a naive
    value as UTC, then convert to ``tz`` before extracting the date — so the
    calendar day matches what the user actually saw on their own clock.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


def _streak_from_dates(finish_dates: set, today: date) -> int:
    """
    Given a set of calendar dates on which something was finished, return the
    length of the consecutive-day streak ending at today or yesterday.

    Returns 0 if the set is empty or the most recent date is more than one day
    before today (the streak has already broken).
    """
    if not finish_dates:
        return 0

    dates = sorted(finish_dates, reverse=True)

    # Streak must start from today or yesterday — otherwise it has already broken.
    if (today - dates[0]).days > 1:
        return 0

    streak = 1
    for i in range(len(dates) - 1):
        if (dates[i] - dates[i + 1]).days == 1:
            streak += 1
        else:
            break

    return streak


def calculate_streak(user_id: str, tz: timezone = None) -> int:
    """
    Calculate a user's current reading streak in consecutive days.

    A streak is the number of consecutive calendar days on which the user
    finished at least one book, counting back from today (or yesterday, if
    nothing has been finished today yet).

    Dates are computed in ``tz`` (defaulting to the server's local timezone).
    Because finished_at is stored in UTC, a book finished late at night is
    counted on the correct local day rather than being pushed onto the UTC day.

    Returns 0 if the user has no reading history or if there is a gap of
    more than one day since their most recent finished book.

    Args:
        user_id: ID of the user.
        tz:      Timezone to resolve calendar dates in. Defaults to the
                 server's local timezone.

    Returns:
        The streak count as an integer.
    """
    tz = tz or datetime.now().astimezone().tzinfo

    events = reading_service.get_reading_history(user_id)
    finish_dates = {_local_date(e.finished_at, tz) for e in events}
    return _streak_from_dates(finish_dates, datetime.now(tz).date())


def calculate_genre_streak(user_id: str, genre: str, tz: timezone = None) -> int:
    """
    Calculate a user's current reading streak restricted to a single genre.

    Identical to :func:`calculate_streak`, except only books whose genre
    matches ``genre`` count toward the streak. A day counts if the user
    finished at least one book in that genre on it.

    Args:
        user_id: ID of the user.
        genre:   Genre to restrict the streak to (matched exactly).
        tz:      Timezone to resolve calendar dates in. Defaults to the
                 server's local timezone.

    Returns:
        The genre-specific streak count as an integer.
    """
    tz = tz or datetime.now().astimezone().tzinfo

    events = reading_service.get_reading_history(user_id)
    finish_dates = {
        _local_date(e.finished_at, tz) for e in events if e.book.genre == genre
    }
    return _streak_from_dates(finish_dates, datetime.now(tz).date())


def books_this_month(user_id: str) -> int:
    """
    Count the number of books the user finished in the current calendar month.

    Args:
        user_id: ID of the user.

    Returns:
        Count of books finished this month.
    """
    events = reading_service.get_reading_history(user_id)
    today = date.today()
    return sum(
        1
        for e in events
        if e.finished_at.year == today.year and e.finished_at.month == today.month
    )


def total_pages_read(user_id: str) -> int:
    """
    Sum the page counts of all books the user has finished.

    Args:
        user_id: ID of the user.

    Returns:
        Total pages read as an integer.
    """
    events = reading_service.get_reading_history(user_id)
    return sum(e.book.pages for e in events)
