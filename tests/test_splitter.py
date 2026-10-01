"""Clause splitter: numbered headings become clauses (US-00-001, AC-US-00-001-2)."""

from app.ingestion.splitter import Clause, split_clauses


def test_two_plain_clauses_are_split_in_order() -> None:
    text = "1 Parties\nAcme Ltd and Beta LLC.\n2 Term\nThree years."

    clauses = split_clauses(text)

    assert clauses == [
        Clause(number="1", heading="Parties", body="Acme Ltd and Beta LLC."),
        Clause(number="2", heading="Term", body="Three years."),
    ]


def test_tc0005_cross_reference_inside_text_is_not_a_heading() -> None:
    text = "7.1 Term\nThe term ends as set out in clause\n7.2 below.\n7.2 Renewal\nIt renews."

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["7.1", "7.2"]
    assert "clause 7.2 below." in " ".join(clauses[0].body.split())
    assert all(c.heading != "below." for c in clauses)


def test_tc0006_decimal_at_line_start_is_not_a_heading() -> None:
    text = "4.1 Rent\nRent rises by\n3.5 percent each year.\n4.2 Deposit\nTwo months."

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["4.1", "4.2"]
    assert "3.5 percent each year." in clauses[0].body


def test_capitalised_number_out_of_sequence_is_not_a_heading() -> None:
    text = (
        "2 Notice\nEither party may end it on not less than\n90 Days notice.\n3 Payment\nMonthly."
    )

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["2", "3"]
    assert "90 Days notice." in clauses[0].body


def test_nested_numbering_follows_the_sequence() -> None:
    text = "7 Term\nIntro.\n7.1 Length\nThree years.\n7.2 Renewal\nYearly.\n8 Payment\nMonthly."

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["7", "7.1", "7.2", "8"]


def test_tc0007_heading_hyphenated_across_lines_is_rejoined() -> None:
    text = "12.10 Limit-\nation of Liability\nCapped at fees."

    clauses = split_clauses(text)

    assert clauses == [
        Clause(number="12.10", heading="Limitation of Liability", body="Capped at fees.")
    ]
    assert not clauses[0].heading.endswith("-")
