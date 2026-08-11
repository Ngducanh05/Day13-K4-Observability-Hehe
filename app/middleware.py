from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

_CORRELATION_ID_RE = re.compile(r"^req-[0-9a-fA-F]{8}$")


def _resolve_correlation_id(request: Request) -> str:
    incoming = request.headers.get("x-request-id", "").strip()
    if _CORRELATION_ID_RE.fullmatch(incoming):
        return incoming
    return f"req-{uuid.uuid4().hex[:8]}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        correlation_id = _resolve_correlation_id(request)
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            clear_contextvars()
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.2f}"

        clear_contextvars()
        return response
