"""`python -m app.extraction.cli [NAME...]` (US-00-002): extract the 10 fields per contract.

NAME is the PDF's file name without `.pdf`; none means every stored
contract. Exit codes: 0 every contract extracted; 1 a contract failed or the
budget is reached. Spend is recorded in its own session and committed even
when the contract's extraction fails, so a failed run still counts against
the USD 9 stop (Q-007). Re-run the command to retry a failed contract.
"""

import argparse
import asyncio
import sys
import uuid
from collections.abc import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.db.repositories import contracts as contract_repo
from app.db.repositories.llm_calls import LlmCallLedger
from app.db.session import make_engine, make_session_factory
from app.extraction import service
from app.llm.cache import ReplyCache
from app.llm.gateway import BudgetReachedError, Gateway, InvalidReplyError


async def run(
    names: list[str],
    factory: async_sessionmaker[AsyncSession],
    gateway_for: Callable[[AsyncSession], Gateway],
) -> int:
    """Extract each named contract and print what happened; return the exit code."""
    async with factory() as session:
        ids = (
            [await contract_repo.find_by_source_stem(session, n) for n in names]
            if names
            else await contract_repo.all_contract_ids(session)
        )
    code = 0
    for name, contract_id in zip(names or [""] * len(ids), ids, strict=True):
        if contract_id is None:
            sys.stderr.write(f"{name}.pdf: no contract loaded from this file\n")
            code = 1
            continue
        try:
            result = await extract_one(factory, gateway_for, contract_id)
            async with factory() as session:
                label = await contract_repo.source_name(session, contract_id)
            sys.stdout.write(
                f"{label}: {result.accepted} accepted, {result.needs_review} need review\n"
            )
        except BudgetReachedError as exc:
            sys.stderr.write(f"{exc.message}\n")
            return 1
        except DomainError as exc:
            async with factory() as session:
                label = await contract_repo.source_name(session, contract_id)
            sys.stderr.write(f"{label}: {exc.message}\n")
            code = 1
    return code


async def extract_one(
    factory: async_sessionmaker[AsyncSession],
    gateway_for: Callable[[AsyncSession], Gateway],
    contract_id: uuid.UUID,
) -> service.ExtractionResult:
    """Extract one contract: the call commits its spend on its own, then the rows are stored."""
    async with factory() as session:
        prepared = await service.prepare(session, contract_id)
    async with factory() as ledger_session:
        gateway = gateway_for(ledger_session)
        reply: service.Reply | None
        try:
            reply = (await gateway.parse(prepared.request, service.REPLY_SCHEMA)).value
        except InvalidReplyError:
            reply = None
        finally:
            await ledger_session.commit()
    async with factory() as session, session.begin():
        if reply is None:
            rows = service.invalid_reply_rows()
            result = await service.store_rows(session, prepared, rows, model_id=gateway.model)
        else:
            result = await service.store(session, prepared, reply, model_id=gateway.model)
    return result


def gateway_factory(
    settings: Settings, client: httpx.AsyncClient, run_id: uuid.UUID
) -> Callable[[AsyncSession], Gateway]:
    """Gateways that record spend in the ledger session given, with the day's budget stop."""

    def gateway_for(ledger_session: AsyncSession) -> Gateway:
        return Gateway(
            client=client,
            cache=ReplyCache(settings.llm_cache_dir),
            ledger=LlmCallLedger(ledger_session, since=settings.llm_budget_since),
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            budget_stop_usd=settings.llm_budget_stop_usd,
            run_id=run_id,
        )

    return gateway_for


async def _main(names: list[str]) -> int:
    settings = get_settings()
    engine = make_engine(settings)
    run_id = uuid.uuid4()
    try:
        async with httpx.AsyncClient() as client:
            gateway_for = gateway_factory(settings, client, run_id)
            return await run(names, make_session_factory(engine), gateway_for)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and extract the contracts."""
    parser = argparse.ArgumentParser(
        description="Extract the 5 fields (prompt v2) from stored contracts."
    )
    parser.add_argument("names", nargs="*", help="PDF file names without .pdf; none means all")
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.names))


if __name__ == "__main__":
    sys.exit(main())
