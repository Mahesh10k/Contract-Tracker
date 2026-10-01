"""`python -m app.ingestion.cli FILE... [--type lease|vendor|service]` (US-00-001).

Exit codes: 0 every file stored or already stored; 1 a file was refused;
2 a file needs --type. Each file is its own transaction, so one bad file
does not undo the others.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import make_engine, make_session_factory
from app.ingestion.service import CONTRACT_TYPES, ContractTypeRequiredError, ingest_file


async def run(
    paths: list[Path], contract_type: str | None, factory: async_sessionmaker[AsyncSession]
) -> int:
    """Load each file and print what happened; return the exit code."""
    code = 0
    for path in paths:
        try:
            async with factory() as session, session.begin():
                result = await ingest_file(session, path, contract_type)
        except ContractTypeRequiredError as exc:
            sys.stderr.write(f"{path.name}: {exc.message}\n")
            code = max(code, 2)
            continue
        except DomainError as exc:
            sys.stderr.write(f"{path.name}: {exc.message}\n")
            code = max(code, 1)
            continue
        verb = "Loaded" if result.created else "Already loaded as"
        sys.stdout.write(f"{path.name}: {verb} {result.title}\n")
    return code


async def _main(paths: list[Path], contract_type: str | None) -> int:
    engine = make_engine(get_settings())
    try:
        return await run(paths, contract_type, make_session_factory(engine))
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and load the files."""
    parser = argparse.ArgumentParser(description="Load contract PDFs as contracts and clauses.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--type", choices=CONTRACT_TYPES, dest="contract_type")
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.files, args.contract_type))


if __name__ == "__main__":
    sys.exit(main())
