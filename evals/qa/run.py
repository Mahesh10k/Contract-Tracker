"""Run the Q&A eval over the 6 golden contracts and the 10 golden questions (US-02-002).

Retrieval is ranked in memory with the same cosine maths pgvector uses (app/retrieval/rank.py), so
the eval needs the embedding model but no database. Model replies come from the reply cache; a
miss offline fails and names the questions, it never calls live (Q-016). `--live` fills the cache
from OpenRouter and records spend in the llm_calls ledger, counted against the day's budget.
Each line `top1 <id> <score> answerable=<bool>` is what the floor spike reads (Q-017).
"""

import argparse
import asyncio
import sys
import tomllib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import anyio
import httpx

from app.core.config import QA_SIMILARITY_FLOOR, get_settings
from app.core.errors import DomainError
from app.db.repositories.llm_calls import LlmCallLedger
from app.db.session import make_engine, make_session_factory
from app.llm.cache import ReplyCache
from app.llm.gateway import Gateway, InvalidReplyError, MissingApiKeyError
from app.qa.service import Answer, AnswerParser, answer_from_hits, refusal
from app.retrieval.embedder import MODEL_NAME, Embedder, SentenceTransformerEmbedder
from app.retrieval.rank import Candidate, rank
from app.retrieval.service import TOP_K
from app.retrieval.text import embedding_text
from evals.contracts.golden import load_answer_key
from evals.extraction.run import MemoryLedger, clauses_of
from evals.qa.golden import Question, load_questions
from evals.qa.graders import QAThresholds, Result, gate, score

HERE = Path(__file__).parent
QUESTIONS = Path("data/golden_questions.json")
KEY_PATH = Path("data/answer_key.json")
MODEL = "anthropic/claude-haiku-4.5"


def missing_model_message(model_dir: Path) -> str | None:
    """Offline runs load the saved model only; None when it is there, else how to get it."""
    if (model_dir / MODEL_NAME.replace("/", "--")).exists():
        return None
    return (
        f"embedding model not found in {model_dir}/; the offline eval never downloads it. "
        "Run make fetch-model once."
    )


def load_thresholds(path: Path = HERE / "thresholds.toml") -> QAThresholds:
    """Allowed misses per metric, kept in one file."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))["allowed_misses"]
    return QAThresholds(int(data["recall"]), int(data["answer"]), int(data["refusal"]))


def golden_candidates(embedder: Embedder) -> list[Candidate]:
    """The golden clauses with their vectors, embedded the way the app embeds them."""
    key = load_answer_key(KEY_PATH)
    pieces = [
        (entry["title"], c.number, c.heading, c.body)
        for cid, entry in key["contracts"].items()
        for c in clauses_of(cid).values()
    ]
    vectors = embedder.embed_documents([embedding_text(*p) for p in pieces])
    return [Candidate(*p, v) for p, v in zip(pieces, vectors, strict=True)]


async def run(
    *,
    embedder: Embedder,
    gateway: AnswerParser,
    floor: float,
    questions: list[Question] | None = None,
) -> tuple[int, list[str]]:
    """Grade every golden question; return the exit code and the report lines."""
    qs = questions or load_questions(QUESTIONS)
    candidates = await anyio.to_thread.run_sync(golden_candidates, embedder)
    results: list[Result] = []
    missing: list[str] = []
    failed: list[str] = []
    lines: list[str] = []
    for q in qs:
        query = await anyio.to_thread.run_sync(embedder.embed_query, q.question)
        hits = rank(query, candidates, TOP_K)
        lines.append(f"top1 {q.id} {hits[0].score:.3f} answerable={q.answerable}")
        try:
            answer: Answer = await answer_from_hits(q.question, hits, gateway, floor)
        except MissingApiKeyError:
            missing.append(q.id)
            continue
        except InvalidReplyError:
            answer = refusal()
        except DomainError as exc:
            failed.append(f"{q.id}: {exc.message}")
            continue
        results.append(Result(q, hits, answer))
    if missing:
        return 1, [f"cache miss: {', '.join(missing)} (run make eval-live)"]
    if failed:
        return 1, failed
    ok, report = gate(score(results), load_thresholds())
    lines = [*report, *lines, f"floor {floor}"]
    for r in results:
        if r.question.answerable == r.answer.refused:
            top3 = [(h.contract_title, h.clause_number) for h in r.hits[:3]]
            lines.append(f"miss: {r.question.id} retrieved={top3} answer={r.answer.text!r}")
    lines.append("eval passed" if ok else "eval FAILED")
    return (0 if ok else 1), lines


def write_last_run(lines: list[str]) -> None:
    """Keep the latest report beside the eval."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(f"- {line}" for line in lines)
    (HERE / "last-run.md").write_text(
        f"# Q&A eval, last run\n\nRun: {stamp}, prompt answer_question v1, model {MODEL}, "
        f"embeddings {MODEL_NAME}\n\n{body}\n",
        encoding="utf-8",
    )


async def _main(live: bool) -> int:
    settings = get_settings() if live else None
    if settings is None and (problem := missing_model_message(Path("models"))):
        sys.stdout.write(f"cache miss: {problem}\n")
        return 1
    embedder = SentenceTransformerEmbedder(
        settings.embedding_model_dir if settings else Path("models")
    )
    if settings is None:
        # Offline never reaches the network: a request here is a bug, not a call (Q-016).
        offline = httpx.MockTransport(lambda _: httpx.Response(599))
        async with httpx.AsyncClient(transport=offline) as client:
            gateway = Gateway(
                client=client,
                cache=ReplyCache(Path("llm_cache")),
                ledger=MemoryLedger(),
                model=MODEL,
                api_key=None,
                budget_stop_usd=Decimal("1.80"),
                run_id=uuid.uuid4(),
            )
            code, lines = await run(embedder=embedder, gateway=gateway, floor=QA_SIMILARITY_FLOOR)
    else:
        engine = make_engine(settings)
        try:
            async with make_session_factory(engine)() as session, httpx.AsyncClient() as client:
                gateway = Gateway(
                    client=client,
                    cache=ReplyCache(settings.llm_cache_dir),
                    ledger=LlmCallLedger(session, since=settings.llm_budget_since),
                    model=settings.llm_model,
                    api_key=settings.openrouter_api_key,
                    budget_stop_usd=settings.llm_budget_stop_usd,
                    run_id=uuid.uuid4(),
                )
                code, lines = await run(
                    embedder=embedder, gateway=gateway, floor=settings.qa_similarity_floor
                )
                await session.commit()
        finally:
            await engine.dispose()
    sys.stdout.write("\n".join(lines) + "\n")
    if not lines[0].startswith("cache miss"):
        write_last_run(lines)
    return code


def main(argv: list[str] | None = None) -> int:
    """`python -m evals.qa.run [--live]`."""
    parser = argparse.ArgumentParser(description="Q&A eval over the golden questions.")
    parser.add_argument("--live", action="store_true", help="call OpenRouter on a cache miss")
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.live))


if __name__ == "__main__":
    sys.exit(main())
