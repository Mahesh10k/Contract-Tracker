"""Graders for the Q&A eval, all by code (Q-011): no LLM judge.

recall@5: the expected contract and clause are among the 5 retrieved. Answer accuracy: the answer
holds the expected value AND cites the expected clause, so a right-sounding answer with the wrong
source does not count. Refusal accuracy: answerable questions answered and unanswerable ones
refused, counted together over all 10, so both wrong refusals and wrong answers cost a point.
"""

from dataclasses import dataclass

from app.qa.service import Answer
from app.retrieval.rank import Hit
from evals.qa.golden import Expected, Question


@dataclass(frozen=True)
class QAThresholds:
    """Allowed misses per metric: with 7 and 10 questions, counts say more than percentages."""

    recall_misses: int
    answer_misses: int
    refusal_misses: int


@dataclass(frozen=True)
class Result:
    """One question with what was retrieved and what the owner would have seen."""

    question: Question
    hits: list[Hit]
    answer: Answer


@dataclass(frozen=True)
class QAScore:
    """Correct and total per metric."""

    recall: tuple[int, int]
    answer: tuple[int, int]
    refusal: tuple[int, int]


def recall_hit(expected: Expected, hits: list[Hit]) -> bool:
    """True when the expected (contract, clause) pair is among the hits."""
    return any(
        (h.contract_title, h.clause_number) == (expected.contract, expected.clause) for h in hits
    )


def answer_correct(expected: Expected, answer: Answer) -> bool:
    """True when the answer states the value and cites the expected clause."""
    if answer.refused:
        return False
    text = answer.text.casefold()
    says_it = any(s.casefold() in text for s in expected.answer_contains_any)
    cites_it = any(
        (c.contract_title, c.clause_number) == (expected.contract, expected.clause)
        for c in answer.citations
    )
    return says_it and cites_it


def refusal_correct(question: Question, answer: Answer) -> bool:
    """Answerable questions should be answered, unanswerable ones refused."""
    return answer.refused != question.answerable


def score(results: list[Result]) -> QAScore:
    """Count each metric over the questions it applies to."""
    answerable = [r for r in results if r.question.expected is not None]
    return QAScore(
        recall=(
            sum(recall_hit(r.question.expected, r.hits) for r in answerable if r.question.expected),
            len(answerable),
        ),
        answer=(
            sum(
                answer_correct(r.question.expected, r.answer)
                for r in answerable
                if r.question.expected
            ),
            len(answerable),
        ),
        refusal=(sum(refusal_correct(r.question, r.answer) for r in results), len(results)),
    )


def gate(result: QAScore, limits: QAThresholds) -> tuple[bool, list[str]]:
    """Report lines, and whether every metric is within its allowed misses."""
    if result.refusal[1] == 0:
        return False, ["0 questions"]
    ok, lines = True, []
    for name, (right, total), allowed in (
        ("recall@5", result.recall, limits.recall_misses),
        ("answer accuracy", result.answer, limits.answer_misses),
        ("refusal accuracy", result.refusal, limits.refusal_misses),
    ):
        line = f"{name} {right}/{total}"
        if total - right > allowed:
            ok = False
            line += f" over allowed misses {allowed}"
        lines.append(line)
    return ok, lines
