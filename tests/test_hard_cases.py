"""Planted hard cases in the synthetic set (US-02-005, TASK-007)."""

import calendar
import re
from datetime import date
from pathlib import Path

import pytest

from app.core.text import normalise_for_match
from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import split_clauses, split_pages
from evals.contracts.dates import end_of_term, months_after
from evals.contracts.generate import BASE_IDS, CONTRACT_IDS, HARD_CASES, generate
from evals.contracts.truth import Truth, load_truth

COMMITTED = Path(__file__).parents[1] / "data" / "contracts"
RELATIVE = re.compile(r"^(?P<words>[a-z]+) \((?P<n>\d+)\) months? after (?P<anchor>\d+ \w+ \d{4})$")


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("hard")
    generate(path)
    return path


@pytest.fixture(scope="module")
def truths(out: Path) -> dict[str, Truth]:
    return {cid: load_truth(out / f"{cid}.truth.json") for cid in CONTRACT_IDS}


def test_five_hard_cases_are_added_beside_the_eighteen() -> None:
    assert len(BASE_IDS) == 18
    assert sorted(HARD_CASES.values()) == [
        "amendment",
        "no-renewal",
        "notice-elsewhere",
        "page-break",
        "relative-date",
    ]
    assert (*BASE_IDS, *HARD_CASES) == CONTRACT_IDS


def test_tc0057_three_contracts_start_relative_to_an_anchor(
    truths: dict[str, Truth],
) -> None:
    relative = {
        cid: RELATIVE.match(t["fields"]["effective_date"]["value"]) for cid, t in truths.items()
    }
    found = {cid: m for cid, m in relative.items() if m}

    assert len(found) >= 3
    assert {cid: date.fromisoformat(truths[cid]["start"]) for cid in found} == {
        cid: months_after(long_date(m["anchor"]), months=int(m["n"])) for cid, m in found.items()
    }


def test_tc0058_notice_in_days_and_months_and_renewal_both_ways(
    truths: dict[str, Truth],
) -> None:
    notices = {t["fields"]["notice_period"]["value"] for t in truths.values()}
    renewals = {t["expected"]["renewal"] is None for t in truths.values()}

    assert any("days" in n for n in notices)
    assert any("months" in n for n in notices)
    assert renewals == {True, False}


def test_tc0059_notice_period_is_cited_outside_the_notice_clause(
    truths: dict[str, Truth],
) -> None:
    truth = truths[case("notice-elsewhere")]
    headings = {c["number"]: c["heading"] for c in truth["clauses"]}

    cited = truth["fields"]["notice_period"]["clause"]

    assert headings[cited] != "Notice of Non-Renewal"
    assert "Notice of Non-Renewal" in headings.values()


def test_tc0060_the_amendment_sets_the_term_and_its_dates(
    truths: dict[str, Truth],
) -> None:
    truth = truths[case("amendment")]
    headings = {c["number"]: c["heading"] for c in truth["clauses"]}
    term = truth["fields"]["term"]

    assert headings[term["clause"]] == "Amendment"
    assert term["value"] == "three (3) years"
    assert truth["term_years"] == 3
    expiry = end_of_term(date.fromisoformat(truth["start"]), years=3)
    assert truth["expected"]["expiry"] == expiry.isoformat()


def test_tc0061_one_clause_runs_from_page_1_onto_page_2(out: Path) -> None:
    cid = case("page-break")
    truth = load_truth(out / f"{cid}.truth.json")
    pdf = read_pdf((out / f"{cid}.pdf").read_bytes())

    clauses = split_pages(pdf.pages)

    spanning = [c for c in clauses if (c.first_page, c.last_page) == (1, 2)]
    assert len(spanning) == 1
    expected = {c["number"]: c["body"] for c in truth["clauses"]}[spanning[0].number]
    assert normalise_for_match(spanning[0].body) == normalise_for_match(expected)


def test_tc0062_the_no_renewal_contract_has_no_renewal_clause(
    truths: dict[str, Truth],
) -> None:
    truth = truths[case("no-renewal")]

    assert "Renewal" not in {c["heading"] for c in truth["clauses"]}
    assert "auto_renewal" not in truth["fields"]
    assert truth["expected"]["renewal"] is None
    assert truth["expected_review"] == ["auto_renewal"]


@pytest.mark.parametrize("contract_id", BASE_IDS)
def test_tc0063_the_eighteen_are_byte_identical(out: Path, contract_id: str) -> None:
    for suffix in (".pdf", ".truth.json"):
        name = f"{contract_id}{suffix}"
        assert (out / name).read_bytes() == (COMMITTED / name).read_bytes(), name


@pytest.mark.parametrize("contract_id", list(HARD_CASES))
def test_tc0064_every_hard_case_quote_is_inside_its_clause(
    truths: dict[str, Truth], contract_id: str
) -> None:
    truth = truths[contract_id]
    bodies = {c["number"]: c["body"] for c in truth["clauses"]}

    missing = [n for n, f in truth["fields"].items() if f["quote"] not in bodies[f["clause"]]]

    assert missing == []


@pytest.mark.parametrize("contract_id", list(HARD_CASES))
def test_tc0065_every_hard_case_pdf_splits_into_its_truth_clauses(
    out: Path, contract_id: str
) -> None:
    truth = load_truth(out / f"{contract_id}.truth.json")
    pdf = read_pdf((out / f"{contract_id}.pdf").read_bytes())

    got = [(c.number, c.heading) for c in split_clauses(pdf.text)]

    assert got == [(c["number"], c["heading"]) for c in truth["clauses"]]


@pytest.mark.parametrize("contract_id", list(HARD_CASES))
def test_hard_cases_are_committed(contract_id: str) -> None:
    assert (COMMITTED / f"{contract_id}.pdf").exists()
    assert (COMMITTED / f"{contract_id}.truth.json").exists()


def case(kind: str) -> str:
    """The contract id planted for one kind of hard case."""
    return next(cid for cid, k in HARD_CASES.items() if k == kind)


def long_date(text: str) -> date:
    """Parse "1 January 2026" without the clock (strptime would need a timezone lint waiver)."""
    day, month, year = text.split()
    return date(int(year), list(calendar.month_name).index(month), int(day))
