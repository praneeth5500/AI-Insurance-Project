"""Recommendation errors, in the standard envelope."""

from __future__ import annotations

from app.core.errors import AppError


class RecommendationRunNotFoundError(AppError):
    """Also raised for another user's run, so ids cannot be probed."""

    code = "RECOMMENDATION_RUN_NOT_FOUND"
    http_status = 404
    retryable = False
    message = "We couldn't find those matched options."


class QuestionnaireNotCompleteError(AppError):
    code = "QUESTIONNAIRE_NOT_COMPLETE"
    http_status = 409
    retryable = False
    message = "Finish and submit your answers before we look for matched options."


class TooManyComparisonsError(AppError):
    """docs/01_PRODUCT_SPEC.md section 2.7: up to 3 policies."""

    code = "TOO_MANY_COMPARISONS"
    http_status = 422
    retryable = False
    message = "You can compare up to 3 options at a time."


class TooFewComparisonsError(AppError):
    code = "TOO_FEW_COMPARISONS"
    http_status = 422
    retryable = False
    message = "Choose at least 2 options to compare."


class ComparisonOptionNotInRunError(AppError):
    """A comparison can only contain options from the run it belongs to."""

    code = "COMPARISON_OPTION_NOT_IN_RUN"
    http_status = 422
    retryable = False
    message = "One of those options isn't part of these matched results."
