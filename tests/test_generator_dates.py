"""The answer key's own date arithmetic (stdlib only, independent of the product's)."""

from datetime import date

from evals.contracts.dates import end_of_term, months_after, months_before


def test_three_year_term_from_first_of_march_ends_on_last_day_of_february() -> None:
    assert end_of_term(date(2026, 3, 1), years=3) == date(2029, 2, 28)


def test_term_ending_in_a_leap_february_ends_on_the_29th() -> None:
    assert end_of_term(date(2025, 3, 1), years=3) == date(2028, 2, 29)


def test_months_before_clamps_to_the_last_day_of_a_shorter_month() -> None:
    assert months_before(date(2029, 5, 31), months=3) == date(2029, 2, 28)


def test_months_after_crosses_the_year_end() -> None:
    assert months_after(date(2026, 11, 15), months=3) == date(2027, 2, 15)
