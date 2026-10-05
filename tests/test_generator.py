"""Synthetic contracts and their answer keys (ADR-0006, US-00-001, TC-0004)."""

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import split_clauses
from evals.contracts.generate import (
    BASE_IDS,
    CONTRACT_IDS,
    FIELDS,
    HOLDOUT,
    UNPARSEABLE_NOTICE,
    generate,
)
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


def test_eighteen_base_contracts_six_of_each_type(truths: dict[str, Truth]) -> None:
    assert Counter(truths[cid]["contract_type"] for cid in BASE_IDS) == {
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


def test_every_base_contract_has_all_ten_fields(truths: dict[str, Truth]) -> None:
    assert {tuple(sorted(truths[cid]["fields"])) for cid in BASE_IDS} == {tuple(sorted(FIELDS))}


@pytest.mark.parametrize("contract_id", BASE_IDS)
@pytest.mark.parametrize("field", FIELDS)
def test_every_quote_is_inside_the_clause_it_cites(
    truths: dict[str, Truth], contract_id: str, field: str
) -> None:
    truth = truths[contract_id]
    cited = truth["fields"][field]
    bodies = {c["number"]: c["body"] for c in truth["clauses"]}

    assert cited["quote"] in bodies[cited["clause"]]


def test_five_contracts_are_held_out(truths: dict[str, Truth]) -> None:
    held = sorted(cid for cid, t in truths.items() if t["holdout"])

    assert held == sorted(HOLDOUT)


def test_two_contracts_expect_their_notice_period_in_review(truths: dict[str, Truth]) -> None:
    held = sorted(cid for cid, t in truths.items() if t["expected_review"] == ["notice_period"])

    assert held == sorted(UNPARSEABLE_NOTICE)


@pytest.mark.parametrize("contract_id", sorted(UNPARSEABLE_NOTICE))
def test_unparseable_contracts_expect_no_notice_deadline(
    truths: dict[str, Truth], contract_id: str
) -> None:
    assert truths[contract_id]["expected"]["notice_deadline"] is None


def test_lease_01_dates_follow_its_stated_terms(truths: dict[str, Truth]) -> None:
    expected = truths["lease-01"]["expected"]

    assert date.fromisoformat(expected["expiry"]) > date.fromisoformat(truths["lease-01"]["start"])
    assert len(expected["payment_dates"]) == truths["lease-01"]["term_years"] * 12


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_tc0004_pdf_round_trip_gives_the_truth_clauses(out_dir: Path, contract_id: str) -> None:
    truth = load_truth(out_dir / f"{contract_id}.truth.json")
    pdf = read_pdf((out_dir / f"{contract_id}.pdf").read_bytes())

    got = [(c.number, c.heading) for c in split_clauses(pdf.text)]

    assert got == [(c["number"], c["heading"]) for c in truth["clauses"]]
