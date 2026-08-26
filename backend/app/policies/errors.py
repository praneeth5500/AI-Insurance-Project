"""Policy upload errors, mapped to the single API error envelope."""

from __future__ import annotations

from app.core.errors import AppError


class PolicyNotFoundError(AppError):
    code = "POLICY_NOT_FOUND"
    http_status = 404
    message = "We couldn't find that policy."


class DocumentNotFoundError(AppError):
    code = "DOCUMENT_NOT_FOUND"
    http_status = 404
    message = "We couldn't find that document."


class UploadRejectedError(AppError):
    code = "UPLOAD_REJECTED"
    http_status = 422
    message = "We couldn't accept that file."


class TooManyDocumentsError(AppError):
    code = "TOO_MANY_DOCUMENTS"
    http_status = 422
    message = "That policy already has as many documents as we can attach to it."


class PolicyDecoderDisabledError(AppError):
    code = "FEATURE_UNAVAILABLE"
    http_status = 404
    message = "Understanding an existing policy isn't part of this beta yet."
