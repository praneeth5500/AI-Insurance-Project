"""Request-id and access-log middleware."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import log_fields
from app.core.request_context import new_request_id, set_request_id

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

CallNext = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, echo it back, and log one line per request.

    Only the allow-listed fields are logged — never query strings, bodies or
    headers, any of which can carry sensitive answers.
    """

    def __init__(self, app: Callable[..., object], slow_request_threshold_ms: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        request_id = new_request_id()
        set_request_id(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_completed",
                extra=log_fields(
                    event="request_completed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    latency_ms=latency_ms,
                ),
            )
            raise

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id

        level = logging.INFO
        if response.status_code >= 500 or latency_ms >= self._slow_request_threshold_ms:
            level = logging.WARNING
        logger.log(
            level,
            "request_completed",
            extra=log_fields(
                event="request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
            ),
        )
        return response
