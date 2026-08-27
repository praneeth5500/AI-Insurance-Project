"""Feedback endpoint."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser, DbSession
from app.feedback import service
from app.feedback.schemas import FeedbackView, SubmitFeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackView,
    status_code=status.HTTP_201_CREATED,
    summary="Tell us what you thought",
)
async def submit(payload: SubmitFeedbackRequest, user: CurrentUser, db: DbSession) -> FeedbackView:
    return FeedbackView.of(
        await service.submit(
            db,
            user=user,
            context_type=payload.context_type,
            context_id=payload.context_id,
            rating=payload.rating,
            comment=payload.comment,
        )
    )
