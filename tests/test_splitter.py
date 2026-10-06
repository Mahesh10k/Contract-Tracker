"""Clause splitter: numbered headings become clauses (US-00-001, AC-US-00-001-2)."""

from app.ingestion.splitter import Clause, split_clauses, split_pages


def test_two_plain_clauses_are_split_in_order() -> None:
    text = "1 Parties\nAcme Ltd and Beta LLC.\n2 Term\nThree years."

    clauses = split_clauses(text)

    assert clauses == [
        Clause(number="1", heading="Parties", body="Acme Ltd and Beta LLC."),
        Clause(number="2", heading="Term", body="Three years."),
    ]


# TC-0005
def test_tc0005_cross_reference_inside_text_is_not_a_heading() -> None:
    text = "7.1 Term\nThe term ends as set out in clause\n7.2 below.\n7.2 Renewal\nIt renews."

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["7.1", "7.2"]
    assert "clause 7.2 below." in " ".join(clauses[0].body.split())
    assert all(c.heading != "below." for c in clauses)


# TC-0006
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


# TC-0007
def test_tc0007_heading_hyphenated_across_lines_is_rejoined() -> None:
    text = "12.10 Limit-\nation of Liability\nCapped at fees."

    clauses = split_clauses(text)

    assert clauses == [
        Clause(number="12.10", heading="Limitation of Liability", body="Capped at fees.")
    ]
    assert not clauses[0].heading.endswith("-")


def test_a_date_line_before_clause_1_is_preamble_not_a_clause() -> None:
    # TASK-001 review finding 3: "1 March 2026" used to become clause 1.
    text = "1 March 2026\n1 Parties\nAcme and Beta.\n2 Term\nThree years."

    clauses = split_clauses(text)

    assert [(c.number, c.heading) for c in clauses] == [("1", "Parties"), ("2", "Term")]


def test_a_numbered_address_before_clause_1_is_not_a_clause() -> None:
    # TASK-001 review finding 3: "100 Main Street" used to swallow the contract.
    text = "100 Main Street\n1 Parties\nAcme and Beta.\n2 Term\nThree years."

    clauses = split_clauses(text)

    assert [c.number for c in clauses] == ["1", "2"]


def test_heading_with_a_trailing_dot_after_the_number_is_a_heading() -> None:
    # TASK-001 review finding 5: TC-0003's documented data is "1. Services".
    text = "1. Services\nCleaning of the offices.\n2. Fees\nMonthly."

    clauses = split_clauses(text)

    assert [(c.number, c.heading) for c in clauses] == [("1", "Services"), ("2", "Fees")]


def test_heading_only_parent_clause_takes_its_heading_as_body() -> None:
    # TASK-001 review finding 4: an empty body made the database refuse the contract.
    text = "2 Term\n2.1 Commencement\nStarts 1 March 2026."

    clauses = split_clauses(text)

    assert clauses[0] == Clause(number="2", heading="Term", body="Term")


def test_a_date_wrapped_to_a_line_start_inside_clause_1_stays_in_its_body() -> None:
    # TASK-001 re-review finding 1: the preamble rule restarted clause 1 here.
    text = (
        "1 Parties\nThis Lease is made on\n"
        "1 March 2026 between Acme and Beta.\n2 Term\nThree years."
    )

    clauses = split_clauses(text)

    assert [(c.number, c.heading) for c in clauses] == [("1", "Parties"), ("2", "Term")]
    assert "1 March 2026 between Acme and Beta." in clauses[0].body


def test_a_dotted_list_inside_undotted_clauses_is_body_text() -> None:
    # TASK-001 re-review finding 2: "1." list items took over clause 1 and swallowed "2 Term".
    text = (
        "1 Parties\nThe parties are:\n1. Harbor Properties LLC\n"
        "2. Acme Analytics Inc\n2 Term\nThree years."
    )

    clauses = split_clauses(text)

    assert [(c.number, c.heading) for c in clauses] == [("1", "Parties"), ("2", "Term")]
    assert "2. Acme Analytics Inc" in clauses[0].body


# TC-0066
def test_tc0066_a_clause_on_page_2_has_pages_2_to_2() -> None:
    pages = ["1 Parties\nAcme and Beta.", "2 Term\nThree years."]

    clauses = split_pages(pages)

    assert [(c.number, c.first_page, c.last_page) for c in clauses] == [
        ("1", 1, 1),
        ("2", 2, 2),
    ]


# TC-0067
def test_tc0067_a_clause_across_a_page_break_is_one_clause_on_pages_1_to_2() -> None:
    pages = [
        "1 Parties\nAcme and Beta.\n2 Term\nThe term is three",
        "years from the start.\n3 Law\nDelaware.",
    ]

    clauses = split_pages(pages)

    assert [(c.number, c.first_page, c.last_page) for c in clauses] == [
        ("1", 1, 1),
        ("2", 1, 2),
        ("3", 2, 2),
    ]
    assert clauses[1].body == "The term is three\nyears from the start."


# TC-0070
def test_tc0070_a_heading_alone_at_the_foot_of_page_1_starts_on_page_1() -> None:
    clauses = split_pages(["1 Parties\nAcme.\n2 Term", "Three years."])

    assert (clauses[1].first_page, clauses[1].last_page) == (1, 2)


# TC-0071
def test_tc0071_text_without_pages_has_no_page_numbers() -> None:
    clauses = split_clauses("1 Parties\nAcme.")

    assert (clauses[0].first_page, clauses[0].last_page) == (None, None)
