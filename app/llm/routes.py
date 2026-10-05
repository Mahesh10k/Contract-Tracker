"""Model prices and call limits for the gateway (ADR-0002).

Prices are OpenRouter's list for anthropic/claude-haiku-4.5 as fetched on
2026-10-01 (docs/genai/contracttracker-solution.md section 5), in USD per
million tokens. They are a fallback only: the cost OpenRouter reports in
`usage.cost` always wins.
"""

import json
from decimal import Decimal

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_S = 60.0
PER_MILLION = Decimal(1_000_000)
PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "anthropic/claude-haiku-4.5": (Decimal("1.00"), Decimal("5.00")),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Cost of a call from its token counts and the price table."""
    price_in, price_out = PRICES[model]
    total = (input_tokens * price_in + output_tokens * price_out) / PER_MILLION
    return total.quantize(Decimal("0.000001"))


def estimate_cost_usd(model: str, body: dict[str, object]) -> Decimal:
    """Upper-bound cost for an attempt with no reported usage: the request's input tokens.

    Four characters per token is a common rough rate for English; the minimum
    of one micro-dollar keeps a live call from ever being recorded at zero.
    """
    input_tokens = len(json.dumps(body)) // 4
    return max(cost_usd(model, input_tokens, 0), Decimal("0.000001"))
