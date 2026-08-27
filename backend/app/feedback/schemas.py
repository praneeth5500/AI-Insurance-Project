"""Feedback payloads."""

from __future__ import annotations

from datetime import datetime

from app.core.schema import ApiModel
from app.feedback.models import Feedback


class SubmitFeedbackRequest(ApiModel):
    context_type: str
    context_id: str | None = None
    #: 1 for helpful, -1 for not. Null when only a comment was left.
    rating: int | None = None
    comment: str | None = None


class FeedbackView(ApiModel):
    id: str
    context_type: str
    rating: int | None
    created_at: datetime

    @classmethod
    def of(cls, entry: Feedback) -> FeedbackView:
        return cls(
            id=entry.id,
            context_type=entry.context_type,
            rating=entry.rating,
            # The comment is not echoed back. It is written for a human to
            # read, not for the client to re-render.
            created_at=entry.created_at,
        )
