"""Response headers that reduce the blast radius of a mistake.

None of these fix a vulnerability on their own; each one narrows what a
vulnerability elsewhere could do. `docs/11_BUILD_PLAN.md` Phase 16 asks for a
security review, and headers are the cheapest part of it.

The API serves JSON and streams private documents. It never serves a page, so
its policy can be far stricter than a site's: nothing here is meant to be
framed, embedded, or loaded as script.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

#: A content-security policy for an API that renders nothing. `default-src
#: 'none'` means a response that somehow reached a browser as a document
#: could not load anything at all.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds the headers every response should carry.

    `Strict-Transport-Security` is only sent outside local development, where
    there is no TLS to insist on and setting it would poison the developer's
    browser for `localhost`.
    """

    def __init__(self, app: Callable[..., Awaitable[None]], *, is_local: bool) -> None:
        super().__init__(app)
        self._is_local = is_local

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Never let a browser second-guess a declared type. This is what stops
        # an uploaded file being executed as script.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", API_CSP)
        # Do not leak the path of a private document in a Referer header.
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # This API has no use for any of them.
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )

        if not self._is_local:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response
