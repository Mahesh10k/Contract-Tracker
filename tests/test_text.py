"""normalise_for_match: layout noise ignored, real wording kept (review task T5, R-011)."""

import pytest

from app.core.text import normalise_for_match


def test_tc0040_line_breaks_and_runs_of_spaces_fold_to_one_space() -> None:
    assert normalise_for_match("ninety (90)\n  days") == normalise_for_match("ninety (90) days")
    assert normalise_for_match("ninety (90)\n  days") == "ninety (90) days"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Limit-\nation", "Limitation"),  # a word the PDF broke at a line end
        ("Limi\u00adtation", "Limitation"),  # a soft hyphen
        ("\u201cParty\u201d", '"Party"'),  # curly double quotes
        ("party\u2019s", "party's"),  # curly apostrophe
        ("thirty\u00a0days", "thirty days"),  # non-breaking space
    ],
)
def test_tc0041_layout_characters_are_unified(raw: str, expected: str) -> None:
    assert normalise_for_match(raw) == expected


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("ninety (90) days", "thirty (30) days"),
        ("may terminate", "may not terminate"),
        ("USD 50,000", "USD 5,000"),
        ("self-insured", "selfinsured"),  # a real hyphen inside a line is kept
    ],
)
def test_tc0042_different_numbers_or_words_never_match(a: str, b: str) -> None:
    assert normalise_for_match(a) != normalise_for_match(b)


def test_a_quote_found_inside_a_clause_after_normalising() -> None:
    clause = (
        "Either party may end this Lease at expiry by giving ninety (90) days written\n"
        "notice before the end of the term."
    )
    quote = "giving ninety (90) days written notice"

    assert normalise_for_match(quote) in normalise_for_match(clause)
