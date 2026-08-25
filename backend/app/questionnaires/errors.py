"""Questionnaire errors, in the standard envelope."""

from __future__ import annotations

from app.core.errors import AppError


class QuestionnaireSessionNotFoundError(AppError):
    """Also raised when the session belongs to someone else.

    Answering "not found" rather than "forbidden" avoids confirming that
    another user's session id exists.
    """

    code = "QUESTIONNAIRE_SESSION_NOT_FOUND"
    http_status = 404
    retryable = False
    message = "We couldn't find those answers."


class QuestionNotFoundError(AppError):
    code = "QUESTION_NOT_FOUND"
    http_status = 404
    retryable = False
    message = "That question isn't part of this questionnaire."


class QuestionNotApplicableError(AppError):
    code = "QUESTION_NOT_APPLICABLE"
    http_status = 409
    retryable = False
    message = "That question doesn't apply based on your earlier answers."


class SessionAlreadyCompletedError(AppError):
    code = "QUESTIONNAIRE_ALREADY_COMPLETED"
    http_status = 409
    retryable = False
    message = "These answers have already been submitted."


class InvalidAnswerError(AppError):
    code = "INVALID_ANSWER"
    http_status = 422
    retryable = False
    message = "That answer isn't valid for this question."


class QuestionnaireIncompleteError(AppError):
    code = "QUESTIONNAIRE_INCOMPLETE"
    http_status = 409
    retryable = False
    message = "Some required questions still need an answer."
