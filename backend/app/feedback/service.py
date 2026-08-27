"""Recording beta feedback."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import FEEDBACK_SUBMITTED
from app.core.errors import AppError
from app.core.logging import log_fields
from app.feedback.models import CONTEXT_TYPES, RATING_HELPFUL, RATING_NOT_HELPFUL, Feedback
from app.users.models import User

logger = logging.getLogger(__name__)

#: Long enough for a real complaint, short enough not to become a place
#: people paste a policy document.
MAX_COMMENT_LENGTH = 2000


class FeedbackRejectedError(AppError):
    code = "FEEDBACK_REJECTED"
    http_status = 422
    message = "We couldn't record that feedback."


async def submit(
    db: AsyncSession,
    *,
    user: User,
    context_type: str,
    context_id: str | None = None,
    rating: int | None = None,
    comment: str | None = None,
) -> Feedback:
    """Store one piece of feedback, and count that it happened.

    The comment goes to the feedback table; the analytics event carries only
    the context and the rating. Free text has one home, and it is not the
    funnel.
    """
    if context_type not in CONTEXT_TYPES:
        raise FeedbackRejectedError("That feedback context isn't one we recognise.")
    if rating is not None and rating not in (RATING_HELPFUL, RATING_NOT_HELPFUL):
        raise FeedbackRejectedError("A rating has to be helpful or not helpful.")

    cleaned = (comment or "").strip()[:MAX_COMMENT_LENGTH] or None
    if rating is None and cleaned is None:
        raise FeedbackRejectedError("Tell us either whether it helped, or what you thought.")

    entry = Feedback(
        user_id=user.id,
        context_type=context_type,
        context_id=context_id,
        rating=rating,
        comment=cleaned,
    )
    db.add(entry)

    await analytics.record_safely(
        db,
        name=FEEDBACK_SUBMITTED,
        user=user,
        # Deliberately not the comment.
        properties={"context_type": context_type, "rating": rating},
    )
    await db.commit()

    logger.info(
        "feedback_submitted",
        extra=log_fields(
            event="feedback_submitted",
            user_id=user.id,
            resource_type="feedback",
            resource_id=entry.id,
        ),
    )
    return entry


async def recent(db: AsyncSession, *, limit: int = 50) -> list[Feedback]:
    """Everything people have said, newest first. For the founder to read."""
    return list(
        (await db.execute(select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)))
        .scalars()
        .all()
    )
