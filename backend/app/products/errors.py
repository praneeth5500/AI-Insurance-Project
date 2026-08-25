"""Product errors, in the standard envelope."""

from __future__ import annotations

from app.core.errors import AppError


class ProductNotFoundError(AppError):
    code = "PRODUCT_NOT_FOUND"
    http_status = 404
    retryable = False
    message = "We couldn't find that option."
