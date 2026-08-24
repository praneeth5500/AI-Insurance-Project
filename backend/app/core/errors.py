"""The single API error shape from docs/08_API_CONTRACTS.md section 12.

Every error response — expected or not — is rendered as::

    {"error": {"code", "message", "retryable", "requestId"}}

Internal detail and stack traces never reach the client.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import log_fields
from app.core.request_context import get_request_id

logger = logging.getLogger(__name__)

GENERIC_ERROR_MESSAGE = "Something went wrong on our side."


class AppError(Exception):
    """Base class for errors that are safe to describe to a client.

    ``message`` is shown to the user, so it must be written in product voice
    and must never contain user input, policy text or internal detail.
    """

    code: str = "INTERNAL_ERROR"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    retryable: bool = False
    message: str = GENERIC_ERROR_MESSAGE

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message


class ServiceUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    retryable = True
    message = "The service is temporarily unavailable. Please try again shortly."


class ValidationFailedError(AppError):
    code = "VALIDATION_FAILED"
    http_status = 422  # constant name differs across Starlette versions
    retryable = False
    message = "Some of the information sent was not valid."


def error_body(code: str, message: str, *, retryable: bool) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "requestId": get_request_id(),
        }
    }


def error_response(code: str, message: str, *, http_status: int, retryable: bool) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=error_body(code, message, retryable=retryable),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so no route can leak a non-conforming error body."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("request_failed", extra=log_fields(error_code=exc.code))
        return error_response(
            exc.code,
            exc.message,
            http_status=exc.http_status,
            retryable=exc.retryable,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        # The validation detail is deliberately dropped: it echoes request
        # bodies, which may contain sensitive questionnaire answers.
        error = ValidationFailedError()
        logger.info("request_invalid", extra=log_fields(error_code=error.code))
        return error_response(
            error.code,
            error.message,
            http_status=error.http_status,
            retryable=error.retryable,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        message = _HTTP_STATUS_MESSAGES.get(exc.status_code, GENERIC_ERROR_MESSAGE)
        logger.info("request_rejected", extra=log_fields(error_code=code))
        return error_response(
            code,
            message,
            http_status=exc.status_code,
            retryable=exc.status_code >= 500,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "request_unhandled_error", exc_info=exc, extra=log_fields(error_code="INTERNAL_ERROR")
        )
        return error_response(
            "INTERNAL_ERROR",
            GENERIC_ERROR_MESSAGE,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=True,
        )


_HTTP_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}

_HTTP_STATUS_MESSAGES: dict[int, str] = {
    400: "That request could not be understood.",
    401: "Please sign in to continue.",
    403: "You do not have access to this.",
    404: "We could not find what you were looking for.",
    405: "That action is not supported here.",
    409: "That conflicts with something that already exists.",
    413: "That file or request is too large.",
    415: "That file type is not supported.",
    429: "Too many requests. Please wait a moment and try again.",
    503: "The service is temporarily unavailable. Please try again shortly.",
}
