"""Pure ASGI middleware binding a request id and logging one line per request.

Not `BaseHTTPMiddleware`: that class breaks streaming responses and does not
propagate contextvars reliably.
"""

import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response, unhandled_response

log = structlog.get_logger()

REQUEST_ID_HEADER = "x-request-id"


class RequestIdMiddleware:
    """Accept or mint an `X-Request-Id`, bind it for logging, echo it back.

    Also the catch-all: an exception nothing else handled becomes the 500
    envelope here, while the request id is still bound.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = Headers(scope=scope).get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, method=scope["method"], path=scope["path"]
        )
        status = 500
        started = False
        start = time.perf_counter()

        async def send_with_id(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                status = int(message["status"])
                started = True
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            if started:
                raise  # the client already has a status; nothing left to map
            await unhandled_response(exc)(scope, receive, send_with_id)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            log.info("request", status=status, duration_ms=duration_ms)
            structlog.contextvars.clear_contextvars()


class UploadLimitMiddleware:
    """Refuse an oversized upload from its Content-Length, before any of the body is read.

    FastAPI parses a multipart body before the route runs, and Starlette spools file parts to disk
    without a cap, so a size check inside the route comes too late. Browsers and curl always send
    Content-Length for a form upload; a chunked upload with no length is refused with 411.
    """

    def __init__(self, app: ASGIApp, *, path: str, max_bytes: int) -> None:
        self.app = app
        self.path = path
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.path:
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length")
        if declared is None or not declared.isdigit():
            await error_response(411, "length_required", "The upload needs a Content-Length")(
                scope, receive, send
            )
        elif int(declared) > self.max_bytes:
            await error_response(413, "upload_too_large", "File is larger than 5 MB")(
                scope, receive, send
            )
        else:
            await self.app(scope, receive, send)
