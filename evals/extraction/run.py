"""Run the extraction eval over the 6 golden contracts (US-02-001).

Offline (no key): every reply must come from the reply cache; a miss fails the
run and names the contracts, it never calls live (Q-016). `--live` uses the
key from the environment and records spend in the llm_calls ledger, so the
USD 2 day budget (ADR-0014) counts it. Requests are built by the app's own
build_request from the same PDF text ingestion stores, so the cache keys match.
"""

import argparse
import asyncio
import json
import sys
import tomllib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from pydantic import SecretStr

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.repositories.llm_calls import LlmCallLedger
from app.db.session import make_engine, make_session_factory
from app.domain.contracts import StoredClause
from app.extraction.schema import FieldReply, FieldsV2
from app.extraction.service import REPLY_SCHEMA, build_request
from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import split_pages
from app.llm.cache import ReplyCache
from app.llm.gateway import (
    CallRecord,
    Gateway,
    InvalidReplyError,
    Ledger,
    MissingApiKeyError,
)
from evals.contracts.golden import AnswerKey, load_answer_key
from evals.extraction.graders import Thresholds, gate, score

HERE = Path(__file__).parent
CONTRACTS = Path("data/contracts")
KEY_PATH = Path("data/answer_key.json")
MODEL = "anthropic/claude-haiku-4.5"


class MemoryLedger:
    """Spend for one offline run: cache hits cost nothing."""

    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    async def spent_usd(self) -> Decimal:
        return sum((r.cost_usd for r in self.records), Decimal(0))

    async def record(self, call: CallRecord) -> None:
        self.records.append(call)


def load_thresholds(path: Path = HERE / "thresholds.toml") -> Thresholds:
    """Allowed misses per field and the grounding floor, kept in one file."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Thresholds(
        allowed_misses={k: int(v) for k, v in data["allowed_misses"].items()},
        grounding_min=float(data["grounding_min"]),
    )


def clauses_of(contract_id: str) -> dict[str, StoredClause]:
    """The clauses ingestion would store for a golden contract."""
    pdf = read_pdf((CONTRACTS / f"{contract_id}.pdf").read_bytes())
    return {
        c.number: StoredClause(uuid.uuid4(), c.number, c.heading, c.body)
        for c in split_pages(pdf.pages)
    }


def _null_reply() -> dict[str, FieldReply]:
    empty = FieldReply(value=None, quote=None, clause_id=None)
    return dict.fromkeys(FieldsV2.model_fields, empty)


@dataclass
class Collected:
    """Replies per golden contract, and the contracts that missed, failed or were unreadable."""

    replies: dict[str, dict[str, FieldReply]] = field(default_factory=dict)
    clauses: dict[str, dict[str, StoredClause]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


async def _collect(gateway: Gateway, key: AnswerKey) -> Collected:
    got = Collected()
    for cid, entry in key["contracts"].items():
        got.clauses[cid] = clauses_of(cid)
        request = build_request(entry["title"], list(got.clauses[cid].values()))
        try:
            parsed = await gateway.parse(request, REPLY_SCHEMA)
        except MissingApiKeyError:
            got.missing.append(cid)
            continue
        except InvalidReplyError:
            got.invalid.append(cid)
            got.replies[cid] = _null_reply()
            continue
        except DomainError as exc:
            got.failed.append(f"{cid}: {exc.message}")
            continue
        got.replies[cid] = {n: getattr(parsed.value.fields, n) for n in FieldsV2.model_fields}
    return got


async def run(
    *,
    client: httpx.AsyncClient,
    cache_dir: Path,
    api_key: SecretStr | None,
    ledger: Ledger | None = None,
    key: AnswerKey | None = None,
    budget_stop_usd: Decimal = Decimal("1.80"),
) -> tuple[int, list[str]]:
    """Grade every golden contract; return the exit code and the report lines."""
    key = key or load_answer_key(KEY_PATH)
    led = ledger or MemoryLedger()
    gateway = Gateway(
        client=client,
        cache=ReplyCache(cache_dir),
        ledger=led,
        model=MODEL,
        api_key=api_key,
        budget_stop_usd=budget_stop_usd,
        run_id=uuid.uuid4(),
    )
    got = await _collect(gateway, key)
    if got.missing:
        return 1, [f"cache miss: {', '.join(got.missing)} (run make eval-live)"]
    if got.failed:
        return 1, got.failed
    result = score(key, got.replies, got.clauses)
    ok, lines = gate(result, load_thresholds())
    if got.invalid:
        lines.append(f"invalid replies (held for review): {', '.join(got.invalid)}")
    spent = await led.spent_usd()
    lines.append(f"spend this run: USD {spent:.4f}")
    lines.extend(f"miss: {m}" for m in result.misses)
    lines.append("eval passed" if ok else "eval FAILED")
    return (0 if ok else 1), lines


def write_last_run(lines: list[str]) -> None:
    """Keep the latest report beside the eval (read by prompt-registry `improve`)."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(f"- {line}" for line in lines)
    (HERE / "last-run.md").write_text(
        f"# Extraction eval, last run\n\nRun: {stamp}, prompt extract_fields v2, "
        f"model {MODEL}\n\n{body}\n",
        encoding="utf-8",
    )


async def _main(live: bool) -> int:
    settings = get_settings() if live else None
    if settings is None:
        # Offline never reaches the network: a request here is a bug, not a call (Q-016).
        offline = httpx.MockTransport(lambda _: httpx.Response(599))
        async with httpx.AsyncClient(transport=offline) as client:
            code, lines = await run(client=client, cache_dir=Path("llm_cache"), api_key=None)
    else:
        engine = make_engine(settings)
        try:
            async with make_session_factory(engine)() as session, httpx.AsyncClient() as client:
                code, lines = await run(
                    client=client,
                    cache_dir=settings.llm_cache_dir,
                    api_key=settings.openrouter_api_key,
                    ledger=LlmCallLedger(session, since=settings.llm_budget_since),
                    budget_stop_usd=settings.llm_budget_stop_usd,
                )
                await session.commit()
        finally:
            await engine.dispose()
    sys.stdout.write("\n".join(lines) + "\n")
    if not lines[0].startswith("cache miss"):
        write_last_run(lines)
        (HERE / "last-run.json").write_text(
            json.dumps({"code": code, "lines": lines}, indent=2) + "\n"
        )
    return code


def main(argv: list[str] | None = None) -> int:
    """`python -m evals.extraction.run [--live]`."""
    parser = argparse.ArgumentParser(description="Extraction eval over the 6 golden contracts.")
    parser.add_argument("--live", action="store_true", help="call OpenRouter on a cache miss")
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.live))


if __name__ == "__main__":
    sys.exit(main())
