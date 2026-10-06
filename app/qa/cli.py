"""`make embed` and `make ask`: embed the clauses once, then ask a question from the terminal."""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import make_engine, make_session_factory
from app.retrieval.embedder import SentenceTransformerEmbedder
from app.retrieval.service import embed_missing
from app.ui.service import UiService


async def _embed() -> int:
    settings = get_settings()
    engine = make_engine(settings)
    try:
        async with make_session_factory(engine)() as session, session.begin():
            count = await embed_missing(
                session, SentenceTransformerEmbedder(settings.embedding_model_dir)
            )
    finally:
        await engine.dispose()
    sys.stdout.write(f"embedded {count} clauses\n")
    return 0


async def _ask(question: str) -> int:
    settings = get_settings()
    engine = make_engine(settings)
    try:
        service = UiService(settings, make_session_factory(engine))
        answer = await service.ask(question)
    except DomainError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return 1
    finally:
        await engine.dispose()
    sys.stdout.write(f"{answer.text}\n")
    for c in answer.citations:
        sys.stdout.write(f"  [{c.contract_title}, {c.clause_number}] {c.clause_text}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """`python -m app.qa.cli embed` or `python -m app.qa.cli ask "<question>"`."""
    parser = argparse.ArgumentParser(description="Embed clauses and ask questions.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("embed", help="embed every clause that has no vector yet")
    ask = sub.add_parser("ask", help="answer one question with cited clauses")
    ask.add_argument("question")
    args = parser.parse_args(argv)
    return asyncio.run(_embed() if args.command == "embed" else _ask(args.question))


if __name__ == "__main__":
    sys.exit(main())
