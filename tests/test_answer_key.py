"""The 6-contract golden set and data/answer_key.json (US-02-006, TC-0072 to TC-0079)."""

from collections import Counter
from pathlib import Path

import pytest

from evals.contracts.generate import HOLDOUT, generate
from evals.contracts.golden import (
    ANSWER_FIELDS,
    GOLDEN_IDS,
    AnswerKey,
    build_answer_key,
    load_answer_key,
    write_answer_key,
)
from evals.contracts.truth import Truth, load_truth


@pytest.fixture(scope="module")
def contracts_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("contracts")
    generate(out)
    return out


@pytest.fixture(scope="module")
def key(contracts_dir: Path) -> AnswerKey:
    path = contracts_dir / "answer_key.json"
    write_answer_key(contracts_dir, path)
    return load_answer_key(path)


def truth_of(contracts_dir: Path, contract_id: str) -> Truth:
    return load_truth(contracts_dir / f"{contract_id}.truth.json")


def test_tc0072_six_contracts_two_of_each_type(key: AnswerKey) -> None:
    contracts = key["contracts"]
    assert len(contracts) == 6
    assert Counter(c["contract_type"] for c in contracts.values()) == {
        "lease": 2,
        "vendor": 2,
        "service": 2,
    }


def test_tc0073_unknown_golden_id_is_refused(contracts_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "answer_key.json"
    with pytest.raises(ValueError, match="lease-99"):
        write_answer_key(contracts_dir, target, ids=("lease-01", "lease-99"))
    assert not target.exists()


def test_tc0074_no_golden_contract_is_a_holdout(contracts_dir: Path, key: AnswerKey) -> None:
    assert not set(key["contracts"]) & set(HOLDOUT)
    assert all(not truth_of(contracts_dir, cid)["holdout"] for cid in GOLDEN_IDS)


def test_tc0075_both_hard_cases_are_in_the_set(key: AnswerKey) -> None:
    assert key["contracts"]["vendor-07"]["hard_case"] == "notice-elsewhere"
    assert key["contracts"]["vendor-08"]["hard_case"] == "no-renewal"


# vendor-08 has no renewal clause; TC-0078 covers its auto_renewal.
FIELD_CASES = [
    (cid, name)
    for cid in GOLDEN_IDS
    for name in ANSWER_FIELDS
    if (cid, name) != ("vendor-08", "auto_renewal")
]


@pytest.mark.parametrize(("contract_id", "field"), FIELD_CASES)
def test_tc0076_field_equals_truth(
    contracts_dir: Path, key: AnswerKey, contract_id: str, field: str
) -> None:
    expected = truth_of(contracts_dir, contract_id)["fields"][field]

    got = key["contracts"][contract_id]["fields"][field]

    assert got == {
        "value": expected["value"],
        "quote": expected["quote"],
        "clause": expected["clause"],
    }


@pytest.mark.parametrize("contract_id", GOLDEN_IDS)
def test_tc0076_dates_equal_truth(contracts_dir: Path, key: AnswerKey, contract_id: str) -> None:
    expected = truth_of(contracts_dir, contract_id)["expected"]

    got = key["contracts"][contract_id]["expected"]

    assert got == {"expiry": expected["expiry"], "notice_deadline": expected["notice_deadline"]}


def test_tc0076_lease_01_worked_example(key: AnswerKey) -> None:
    entry = key["contracts"]["lease-01"]

    assert entry["fields"]["notice_period"]["clause"] == "7"
    assert entry["expected"]["notice_deadline"] == "2026-12-01"


def test_tc0077_answer_fields_are_the_five_of_req_045() -> None:
    assert ANSWER_FIELDS == (
        "parties",
        "effective_date",
        "term",
        "auto_renewal",
        "notice_period",
    )


@pytest.mark.parametrize("contract_id", GOLDEN_IDS)
def test_tc0077_each_contract_has_exactly_the_five_fields(key: AnswerKey, contract_id: str) -> None:
    fields = key["contracts"][contract_id]["fields"]

    assert tuple(fields) == ANSWER_FIELDS
    assert "payment_terms" not in fields


def test_tc0078_missing_renewal_clause_is_null(key: AnswerKey) -> None:
    assert key["contracts"]["vendor-08"]["fields"]["auto_renewal"] == {
        "value": None,
        "quote": None,
        "clause": None,
    }


def test_tc0079_answer_key_is_byte_identical_across_runs(
    contracts_dir: Path, tmp_path: Path
) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_answer_key(contracts_dir, a)
    write_answer_key(contracts_dir, b)
    assert a.read_bytes() == b.read_bytes()


def test_build_rejects_truths_missing_a_golden_id(contracts_dir: Path) -> None:
    truths = {cid: truth_of(contracts_dir, cid) for cid in GOLDEN_IDS[:-1]}
    with pytest.raises(ValueError, match=GOLDEN_IDS[-1]):
        build_answer_key(truths, GOLDEN_IDS)
