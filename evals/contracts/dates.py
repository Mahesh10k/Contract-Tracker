"""Date arithmetic for the answer key, standard library only.

The product computes dates with python-dateutil and its own duration parser
(ADR-0007). The answer key must not reuse that code, or the eval would only
prove the code agrees with itself; this module is the independent second
implementation.
"""

import calendar
from datetime import date


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def end_of_term(start: date, *, years: int) -> date:
    """Last day of a term of `years` starting on the first of a month."""
    year, month = start.year + years, start.month - 1
    if month == 0:
        year, month = year - 1, 12
    return date(year, month, _last_day(year, month))


def months_after(day: date, *, months: int) -> date:
    """The same day `months` later (or earlier when negative), clamped to that month's last day."""
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    return date(year, month, min(day.day, _last_day(year, month)))


def months_before(day: date, *, months: int) -> date:
    """The same day `months` earlier, clamped to that month's last day."""
    return months_after(day, months=-months)
