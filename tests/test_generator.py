"""Synthetic contracts and their answer keys (ADR-0006, US-00-001, TC-0004)."""

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import split_clauses
from evals.contracts.generate import FIELDS, generate
from evals.contracts.truth import Truth, load_truth


@pytest.fixture(scope="module")
def truths(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Truth]:
    out = tmp_path_factory.mktemp("contracts")
    generate(out)
    return {p.name.removesuffix(".truth.json"): load_truth(p) for p in out.glob("*.truth.json")}


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("roundtrip")
    generate(out)
    return out


def test_eighteen_contracts_six_of_each_type(truths: dict[str, Truth]) -> None:
    assert Counter(t["contract_type"] for t in truths.values()) == {
        "lease": 6,
        "vendor": 6,
        "service": 6,
    }


def test_generation_is_byte_identical_across_runs(tmp_path: Path) -> None:
    generate(tmp_path / "a")
    generate(tmp_path / "b")

    first = {p.name: p.read_bytes() for p in (tmp_path / "a").iterdir()}
    second = {p.name: p.read_bytes() for p in (tmp_path / "b").iterdir()}

    assert first == second


def test_every_contract_has_all_ten_fields(truths: dict[str, Truth]) -> None:
    assert {tuple(sorted(t["fields"])) for t in truths.values()} == {tuple(sorted(FIELDS))}


def test_every_quote_is_inside_the_clause_it_cites(truths: dict[str, Truth]) -> None:
    misplaced = [
        (cid, name)
        for cid, t in truths.items()
        for name, field in t["fields"].items()
        if field["quote"] not in {c["number"]: c["body"] for c in t["clauses"]}[field["clause"]]
    ]

    assert misplaced == []


def test_five_contracts_are_held_out(truths: dict[str, Truth]) -> None:
    assert sum(1 for t in truths.values() if t["holdout"]) == 5


def test_two_contracts_expect_their_notice_period_in_review(
    truths: dict[str, Truth],
) -> None:
    held = [cid for cid, t in truths.items() if t["expected_review"] == ["notice_period"]]

    assert len(held) == 2
    assert all(truths[cid]["expected"]["notice_deadline"] is None for cid in held)


def test_lease_01_dates_follow_its_stated_terms(truths: dict[str, Truth]) -> None:
    expected = truths["lease-01"]["expected"]

    assert date.fromisoformat(expected["expiry"]) > date.fromisoformat(truths["lease-01"]["start"])
    assert len(expected["payment_dates"]) == truths["lease-01"]["term_years"] * 12


def test_tc0004_pdf_round_trip_gives_the_truth_clauses(out_dir: Path) -> None:
    mismatched = []
    for truth_path in sorted(out_dir.glob("*.truth.json")):
        truth = load_truth(truth_path)
        pdf = truth_path.with_name(truth_path.name.replace(".truth.json", ".pdf"))
        got = [(c.number, c.heading) for c in split_clauses(read_pdf(pdf.read_bytes()).text)]
        want = [(c["number"], c["heading"]) for c in truth["clauses"]]
        if got != want:
            mismatched.append(truth_path.name)

    assert mismatched == []
