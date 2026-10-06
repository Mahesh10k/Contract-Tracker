"""Q&A eval: golden file, graders, gate and the offline harness (US-02-002, TC-0153 to TC-0157)."""

import json
from pathlib import Path

import pytest

from app.llm.gateway import LLMRequest, MissingApiKeyError, Parsed
from app.qa.schema import AnswerReply, CitationRef
from app.qa.service import REFUSAL, Answer, AnsweredCitation
from app.retrieval.rank import Hit
from evals.qa.golden import Expected, Question, load_questions
from evals.qa.graders import (
    QAThresholds,
    Result,
    answer_correct,
    gate,
    recall_hit,
    refusal_correct,
    score,
)
from evals.qa.run import run
from tests.retrieval.fakes import FakeEmbedder

GOLDEN = Path("data/golden_questions.json")
EXPECT = Expected(contract="Supply Agreement 08", clause="8", answer_contains_any=["california"])
LIMITS = QAThresholds(recall_misses=1, answer_misses=1, refusal_misses=1)


def hit(contract: str, clause: str, score_: float = 0.8) -> Hit:
    return Hit(contract, clause, "Heading", "body", score_)


def answered(text: str, contract: str = "Supply Agreement 08", clause: str = "8") -> Answer:
    return Answer(text, [AnsweredCitation(contract, clause, "body")], False)


def question(i: int, expected: Expected | None) -> Question:
    return Question(
        id=f"q{i:02d}",
        question=f"Question {i}?",
        answerable=expected is not None,
        expected=expected,
    )


def test_tc0157_the_golden_file_has_seven_answerable_and_three_unanswerable_questions() -> None:
    questions = load_questions(GOLDEN)

    assert (len(questions), sum(q.answerable for q in questions)) == (10, 7)
    assert len({q.question for q in questions}) == 10
    assert all((q.expected is None) != q.answerable for q in questions)


def test_a_question_naming_a_clause_that_does_not_exist_is_refused_at_load(tmp_path: Path) -> None:
    bad = [
        {
            "id": "q01",
            "question": "Q?",
            "answerable": True,
            "expected": {
                "contract": "Supply Agreement 08",
                "clause": "99",
                "answer_contains_any": ["x"],
            },
        }
    ]
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(bad))

    with pytest.raises(ValueError, match=r"q01.*99"):
        load_questions(path)


def test_tc0153_recall_counts_only_the_expected_contract_and_clause_pair() -> None:
    assert (
        recall_hit(EXPECT, [hit("Lease Agreement 01", "8"), hit("Supply Agreement 08", "8")])
        is True
    )
    assert (
        recall_hit(EXPECT, [hit("Lease Agreement 01", "8"), hit("Supply Agreement 08", "4")])
        is False
    )


def test_tc0154_an_answer_needs_the_value_and_the_expected_clause() -> None:
    right = answered("It is governed by the laws of the State of California.")
    wrong_clause = answered("California law.", clause="4")
    wrong_value = answered("The laws of England and Wales.")

    assert [answer_correct(EXPECT, a) for a in (right, wrong_clause, wrong_value)] == [
        True,
        False,
        False,
    ]
    assert answer_correct(EXPECT, Answer(REFUSAL, [], True)) is False


def test_tc0155_refusal_accuracy_counts_wrong_refusals_and_wrong_answers() -> None:
    refused = Answer(REFUSAL, [], True)
    cases = [
        (question(1, EXPECT), answered("California.")),
        (question(2, EXPECT), refused),
        (question(3, None), refused),
        (question(4, None), answered("Yes.")),
    ]

    verdicts = [refusal_correct(q, a) for q, a in cases]

    assert verdicts == [True, False, True, False]


def test_scores_are_hits_over_totals_and_the_gate_names_a_metric_under_its_threshold() -> None:
    qs = [question(i, EXPECT) for i in range(1, 8)] + [question(i, None) for i in range(8, 11)]
    ok = answered("California.")
    results = [Result(q, [hit("Supply Agreement 08", "8", 0.9)], ok) for q in qs[:7]] + [
        Result(q, [hit("Lease Agreement 01", "1", 0.2)], Answer(REFUSAL, [], True)) for q in qs[7:]
    ]
    perfect = score(results)
    # three answerable questions retrieve the wrong clause and are refused
    broken = [
        Result(r.question, [hit("Lease Agreement 01", "1")], Answer(REFUSAL, [], True))
        if i < 3
        else r
        for i, r in enumerate(results)
    ]

    passed, lines = gate(perfect, LIMITS)
    failed, bad_lines = gate(score(broken), LIMITS)

    assert (perfect.recall, perfect.answer, perfect.refusal) == ((7, 7), (7, 7), (10, 10))
    assert passed is True
    assert failed is False
    assert "recall@5 4/7 over allowed misses 1" in bad_lines
    assert "recall@5 7/7" in lines


def test_gate_fails_on_zero_questions() -> None:
    ok, lines = gate(score([]), LIMITS)

    assert ok is False
    assert "0 questions" in lines


class ScriptedGateway:
    """A model that answers every question from the golden file, as a perfect one would."""

    def __init__(self, questions: list[Question]) -> None:
        self.by_text = {q.question: q for q in questions}
        self.calls = 0

    async def parse(self, req: LLMRequest, schema: type[AnswerReply]) -> Parsed[AnswerReply]:
        self.calls += 1
        asked = req.system.split("<question>\n", 1)[1].split("\n</question>", 1)[0]
        q = self.by_text[asked]
        e = q.expected
        reply = (
            AnswerReply(answerable=False, answer="", citations=[])
            if e is None
            else AnswerReply(
                answerable=True,
                answer=e.answer_contains_any[0],
                citations=[CitationRef(contract=e.contract, clause=e.clause)],
            )
        )
        return Parsed(value=reply, cache_hit=False)


class EmptyCacheGateway:
    async def parse(self, req: LLMRequest, schema: type[AnswerReply]) -> Parsed[AnswerReply]:
        raise MissingApiKeyError("OPENROUTER_API_KEY is not set; cannot make a live call")


async def test_the_harness_prints_the_three_metrics_and_each_questions_top_score() -> None:
    questions = load_questions(GOLDEN)

    code, lines = await run(embedder=FakeEmbedder(), gateway=ScriptedGateway(questions), floor=0.0)

    assert any(line.startswith("recall@5 ") for line in lines)
    assert any(line.startswith("answer accuracy ") for line in lines)
    assert any(line.startswith("refusal accuracy ") for line in lines)
    assert sum(line.startswith("top1 ") for line in lines) == 10
    assert code in (0, 1)
    assert lines[-1] in ("eval passed", "eval FAILED")


async def test_a_question_under_the_floor_never_reaches_the_model() -> None:
    questions = load_questions(GOLDEN)
    gateway = ScriptedGateway(questions)

    await run(embedder=FakeEmbedder(), gateway=gateway, floor=2.0)

    assert gateway.calls == 0


async def test_an_empty_cache_with_no_key_fails_naming_the_questions_and_never_calls_live() -> None:
    code, lines = await run(embedder=FakeEmbedder(), gateway=EmptyCacheGateway(), floor=0.0)

    assert code == 1
    assert lines[0].startswith("cache miss: q01, q02")
    assert "make eval-live" in lines[0]
