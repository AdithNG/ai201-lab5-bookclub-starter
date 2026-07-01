# Stats Audit — `books_this_month()` and `total_pages_read()`

During the bug hunt we confirmed these two functions return the *right* values
for the seed data. This audit asks the sharper question: are they correct **by
design**, or correct **by coincidence** — i.e. only because the seed data
happens to avoid their weak spots? Both turn out to be the latter.

---

## 1. `books_this_month()`

```python
def books_this_month(user_id: str) -> int:
    events = reading_service.get_reading_history(user_id)
    today = date.today()
    return sum(
        1
        for e in events
        if e.finished_at.year == today.year and e.finished_at.month == today.month
    )
```

**Contract:** books the user finished *in the current calendar month*.

### Edge case — month boundary across timezones

`finished_at` is stored in **UTC** (and comes back from SQLite as a naive
datetime), but `today` comes from `date.today()`, which is the **server-local**
date. The function compares a UTC month against a local month — two different
clocks.

Concretely: a user in UTC-5 finishes a book at **11:30 PM local on January 31**.
That is stored as **04:30 UTC on February 1**, so `finished_at.month == 2`.

- On Jan 31 (local), the user expects this book to count toward **January** — it
  doesn't (the stored month is February).
- It instead gets counted in **February**, a month the user hadn't reached yet
  on their own clock.

So on the first/last day of any month, a late-night finish can be attributed to
the wrong month. The same class of inconsistency also skews the **year** field
every December 31 → January 1.

**Why the seed passes:** the seeded finishes are days apart and nowhere near a
month boundary, so the UTC month and the local month always agree. Remove that
coincidence and the count drifts.

**Fix direction:** resolve `finished_at` into the target timezone before reading
`.year`/`.month`, and take `today` in the same zone — exactly the
`_local_date(...)` approach already applied to `calculate_streak()` in
Challenge 1. (`books_this_month` was left untouched to keep this an audit, not a
second refactor.)

---

## 2. `total_pages_read()`

```python
def total_pages_read(user_id: str) -> int:
    events = reading_service.get_reading_history(user_id)
    return sum(e.book.pages for e in events)
```

**Contract:** total pages across all finished books.

### Edge case — a book with `pages == 0`

`Book.pages` is `nullable=False`, so it can never be `None` — but the schema
places **no lower bound on it**, so `pages = 0` is a perfectly storable value
(e.g. a book added before its real page count was known, or a bad import).

When such a book is finished, `total_pages_read()` adds `0` for it. No exception
is raised — the function **silently under-reports** the true total. A user who
reads a 300-page book and a mis-entered 0-page book sees 300, with nothing to
signal that a value is missing. "No error" is not the same as "correct."

(Contrast with `pages = None`: that *would* raise `TypeError` inside `sum(...)`
— but the schema forbids it, so the realistic failure is the silent `0`, not a
crash.)

**Why the seed passes:** every seeded book has a real, positive page count, so
the zero case never arises. The function is correct only as long as upstream
data-entry stays clean.

**Fix direction:** enforce the invariant where the data is created — a
`CheckConstraint("pages > 0")` on the model and/or validation in
`add_book()` — so a 0-page book can't be stored in the first place. That keeps
the summation trivially correct instead of quietly wrong.

---

## Summary

| Function | Correct on seed? | Correct by design? | Weak spot |
|---|---|---|---|
| `books_this_month()` | Yes | No | UTC-vs-local month boundary (off-by-one month/year) |
| `total_pages_read()` | Yes | No | Silently sums `pages == 0` with no signal |

Both pass today only because the seed data avoids their edge cases. Each is one
plausible real-world input away from a wrong-but-silent result — the most
expensive kind, because nothing crashes to tell you.
