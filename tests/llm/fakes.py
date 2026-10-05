"""Test helpers for the gateway: an in-memory ledger and recorded OpenRouter replies."""

import json
from collections.abc import Mapping
from decimal import Decimal

from app.llm.gateway import CallRecord


class InMemoryLedger:
    """The gateway's ledger without a database: spend starts at `spent`."""

    def __init__(self, spent: str = "0") -> None:
        self.start = Decimal(spent)
        self.records: list[CallRecord] = []

    async def spent_usd(self) -> Decimal:
        return self.start + sum((r.cost_usd for r in self.records), Decimal(0))

    async def record(self, call: CallRecord) -> None:
        self.records.append(call)


def chat_reply(
    content: Mapping[str, object] | str,
    *,
    cost: float | None = 0.0135,
    prompt_tokens: int = 6000,
    completion_tokens: int = 1500,
    finish_reason: str = "stop",
) -> dict[str, object]:
    """An OpenRouter chat completion body as the API returns it."""
    usage: dict[str, object] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    if cost is not None:
        usage["cost"] = cost
    text = content if isinstance(content, str) else json.dumps(content)
    return {
        "id": "gen-test",
        "model": "anthropic/claude-haiku-4.5",
        "choices": [{"finish_reason": finish_reason, "message": {"content": text}}],
        "usage": usage,
    }
