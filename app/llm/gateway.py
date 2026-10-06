"""The gateway: every model call goes through `Gateway.parse` (ADR-0001, ADR-0009).

Order of checks, each before any spend: kill switch, reply cache (a replay
costs nothing, so it works even after the budget stop), budget stop
(USD 9, Q-007), API key. Then at most two attempts: a timeout, a 429, a 5xx
or a reply that fails the schema (REQ-038) is retried once; a 400 is our
bug and is never retried. The budget is checked again before the retry.
Every attempt writes one ledger record; an attempt with no reported usage
(including a 200 that is not JSON or has no choices) is recorded at an
upper-bound estimate, so spend can be over-counted but never under-counted.
Logs carry no prompt or reply text.
"""

import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import anyio
import httpx
import structlog
from pydantic import BaseModel, SecretStr, ValidationError

from app.core.errors import DomainError
from app.llm.cache import ReplyCache, cache_key
from app.llm.routes import (
    MIN_COST_USD,
    OPENROUTER_URL,
    TIMEOUT_S,
    cost_usd,
    estimate_cost_usd,
)

log = structlog.get_logger()


class BudgetReachedError(DomainError):
    """Recorded spend has reached the stop; no call is made (Q-007)."""

    status_code = 402
    code = "llm_budget_reached"


class FeatureDisabledError(DomainError):
    """The feature's kill switch is on (LLM_KILL_<FEATURE>=1)."""

    status_code = 503
    code = "llm_feature_disabled"


class MissingApiKeyError(DomainError):
    """A live call is needed and OPENROUTER_API_KEY is not set."""

    status_code = 503
    code = "llm_key_missing"


class GatewayFailedError(DomainError):
    """Both attempts failed; the message names why."""

    status_code = 502
    code = "llm_failed"


@dataclass(frozen=True)
class LLMRequest:
    """One structured-output call: the prompt by name and version, and its two messages."""

    feature: str
    prompt_name: str
    prompt_version: str
    system: str
    user: str
    max_tokens: int


@dataclass(frozen=True)
class CallRecord:
    """One attempt as the llm_calls ledger stores it."""

    run_id: uuid.UUID
    prompt_name: str
    prompt_version: str
    model_id: str
    cache_key: str
    cache_hit: bool
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class Ledger(Protocol):
    """Where spend is read and attempts are recorded (llm_calls in production)."""

    async def spent_usd(self) -> Decimal: ...

    async def record(self, call: CallRecord) -> None: ...


@dataclass(frozen=True)
class Parsed[T: BaseModel]:
    """A validated reply and whether it came from the cache."""

    value: T
    cache_hit: bool


class _RetryableError(Exception):
    """An attempt failed in a way worth one more try; `reason` is user-facing."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Gateway:
    """The one door for model calls."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        cache: ReplyCache,
        ledger: Ledger,
        model: str,
        api_key: SecretStr | None,
        budget_stop_usd: Decimal,
        run_id: uuid.UUID,
    ) -> None:
        self.client = client
        self.cache = cache
        self.ledger = ledger
        self.model = model
        self.api_key = api_key
        self.budget_stop_usd = budget_stop_usd
        self.run_id = run_id

    async def parse[T: BaseModel](self, req: LLMRequest, schema: type[T]) -> Parsed[T]:
        """Return `schema` filled by the model for `req`, from the cache when possible."""
        if os.environ.get(f"LLM_KILL_{req.feature.upper()}") == "1":
            raise FeatureDisabledError(
                f"{req.feature} is switched off (LLM_KILL_{req.feature.upper()})"
            )
        body = self._body(req, schema)
        key = cache_key(f"{req.prompt_name}@{req.prompt_version}", self.model, body)
        cached = await anyio.to_thread.run_sync(self.cache.get, key)
        if cached is not None:
            await self._record(
                req, key, cache_hit=True, tokens=(0, 0), cost=Decimal(0), status="cache"
            )
            return Parsed(value=schema.model_validate_json(str(cached["content"])), cache_hit=True)
        if await self.ledger.spent_usd() >= self.budget_stop_usd:
            raise BudgetReachedError("LLM budget reached")
        if self.api_key is None:
            raise MissingApiKeyError("OPENROUTER_API_KEY is not set; cannot make a live call")
        reason = ""
        for attempt in (1, 2):
            if attempt == 2 and await self.ledger.spent_usd() >= self.budget_stop_usd:
                raise BudgetReachedError("LLM budget reached")
            try:
                content = await self._attempt(req, key, body, attempt, self.api_key)
                value = schema.model_validate_json(content)
            except _RetryableError as exc:
                reason = exc.reason
                continue
            except ValidationError:
                reason = "reply did not match the schema"
                continue
            await anyio.to_thread.run_sync(self.cache.put, key, {"content": content})
            return Parsed(value=value, cache_hit=False)
        raise GatewayFailedError(f"{req.feature.capitalize()} failed: {reason}")

    def _body(self, req: LLMRequest, schema: type[BaseModel]) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": req.system},
                {"role": "user", "content": req.user},
            ],
            "max_tokens": req.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
            "usage": {"include": True},
        }

    async def _attempt(
        self,
        req: LLMRequest,
        key: str,
        body: dict[str, object],
        attempt: int,
        api_key: SecretStr,
    ) -> str:
        """One HTTP call; returns the reply text or raises _RetryableError or GatewayFailedError."""
        estimate = estimate_cost_usd(self.model, body)
        try:
            response = await self.client.post(
                OPENROUTER_URL,
                json=body,
                headers={"Authorization": f"Bearer {api_key.get_secret_value()}"},
                timeout=TIMEOUT_S,
            )
        except httpx.TimeoutException as exc:
            await self._record(
                req,
                key,
                cache_hit=False,
                tokens=(0, 0),
                cost=estimate,
                status="timeout",
                attempt=attempt,
            )
            raise _RetryableError("model timed out") from exc
        except httpx.TransportError as exc:
            await self._record(
                req,
                key,
                cache_hit=False,
                tokens=(0, 0),
                cost=estimate,
                status="unreachable",
                attempt=attempt,
            )
            raise _RetryableError("model unreachable") from exc
        if response.status_code == 429 or response.status_code >= 500:
            await self._record(
                req,
                key,
                cache_hit=False,
                tokens=(0, 0),
                cost=estimate,
                status=str(response.status_code),
                attempt=attempt,
            )
            raise _RetryableError(f"model unavailable ({response.status_code})")
        if response.status_code >= 400:
            await self._record(
                req,
                key,
                cache_hit=False,
                tokens=(0, 0),
                cost=estimate,
                status=str(response.status_code),
                attempt=attempt,
            )
            status = response.status_code
            raise GatewayFailedError(
                f"{req.feature.capitalize()} failed: model request rejected ({status})"
            )
        try:
            data = response.json()
        except ValueError:
            data = {}
        usage = (data.get("usage") if isinstance(data, dict) else None) or {}
        tokens = (int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
        reported = usage.get("cost")
        if reported is not None:
            cost = Decimal(str(reported))
        elif tokens != (0, 0):
            cost = cost_usd(self.model, *tokens)
        else:
            cost = estimate
        await self._record(
            req,
            key,
            cache_hit=False,
            tokens=tokens,
            cost=max(cost, MIN_COST_USD),
            status="200",
            attempt=attempt,
        )
        try:
            choice = data["choices"][0]
            content = str(choice["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise _RetryableError("reply did not match the schema") from exc
        if choice.get("finish_reason") != "stop":
            raise _RetryableError("reply did not match the schema")
        return content

    async def _record(
        self,
        req: LLMRequest,
        key: str,
        *,
        cache_hit: bool,
        tokens: tuple[int, int],
        cost: Decimal,
        status: str,
        attempt: int = 0,
    ) -> None:
        await self.ledger.record(
            CallRecord(
                run_id=self.run_id,
                prompt_name=req.prompt_name,
                prompt_version=req.prompt_version,
                model_id=self.model,
                cache_key=key,
                cache_hit=cache_hit,
                input_tokens=tokens[0],
                output_tokens=tokens[1],
                cost_usd=cost,
            )
        )
        log.info(
            "llm_call",
            feature=req.feature,
            prompt=f"{req.prompt_name}@{req.prompt_version}",
            model=self.model,
            status=status,
            attempt=attempt,
            cache_hit=cache_hit,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            cost_usd=str(cost),
        )
