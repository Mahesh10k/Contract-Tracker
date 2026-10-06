"""Embedding text and in-memory ranking (US-00-004, TC-0136 to TC-0139)."""

import math

from app.retrieval.rank import Candidate, rank
from app.retrieval.text import QUERY_INSTRUCTION, embedding_text, query_text


def candidate(number: str, vector: list[float], title: str = "Lease Agreement 01") -> Candidate:
    return Candidate(title, number, "Heading", f"body {number}", vector)


def at_degrees(degrees: float) -> list[float]:
    return [math.cos(math.radians(degrees)), math.sin(math.radians(degrees))]


def test_tc0136_clause_text_is_title_number_heading_then_body() -> None:
    text = embedding_text("Lease Agreement 01", "2.2", "Duration", "The term is two (2) years.")

    assert text == "Lease Agreement 01 | 2.2 Duration | The term is two (2) years."


def test_tc0137_a_question_gets_the_bge_instruction_and_a_clause_does_not() -> None:
    assert query_text("Who pays?") == f"{QUERY_INSTRUCTION}Who pays?"
    assert not embedding_text("T", "1", "H", "B").startswith(QUERY_INSTRUCTION)


def test_tc0138_the_five_nearest_clauses_come_back_highest_similarity_first() -> None:
    clauses = [candidate(str(n), at_degrees(n * 10)) for n in range(8)]

    hits = rank([1.0, 0.0], clauses, 5)

    assert [h.clause_number for h in hits] == ["0", "1", "2", "3", "4"]
    assert [round(h.score, 3) for h in hits] == [1.0, 0.985, 0.940, 0.866, 0.766]
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_tc0139_fewer_clauses_than_k_all_come_back_and_none_gives_nothing() -> None:
    three = [candidate(str(n), at_degrees(n * 10)) for n in range(3)]

    assert len(rank([1.0, 0.0], three, 5)) == 3
    assert rank([1.0, 0.0], [], 5) == []


def test_a_vector_of_a_different_length_is_refused() -> None:
    import pytest

    with pytest.raises(ValueError, match="dimension"):
        rank([1.0, 0.0, 0.0], [candidate("1", [1.0, 0.0])], 5)


def test_equal_scores_keep_document_order() -> None:
    same = [candidate("2", [1.0, 0.0]), candidate("1", [1.0, 0.0])]

    assert [h.clause_number for h in rank([1.0, 0.0], same, 5)] == ["2", "1"]


def test_a_zero_vector_scores_zero_instead_of_dividing_by_zero() -> None:
    hits = rank([1.0, 0.0], [candidate("1", [0.0, 0.0])], 5)

    assert hits[0].score == 0.0
