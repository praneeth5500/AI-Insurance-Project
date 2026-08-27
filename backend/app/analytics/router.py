"""The client analytics endpoint.

Only events the registry marks `client_emittable` are accepted. Server-side
funnel steps — questionnaire completed, recommendation generated — are
recorded where they actually happen, so a browser cannot fabricate them.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.analytics import service
from app.analytics.events import UnknownEventError, definition_for
from app.analytics.schemas import TrackEventRequest, TrackEventResponse
from app.auth.dependencies import CurrentUser, DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", response_model=TrackEventResponse, summary="Record an interaction")
async def track(payload: TrackEventRequest, user: CurrentUser, db: DbSession) -> TrackEventResponse:
    """Record a client-side event.

    Returns 200 with `recorded: false` rather than an error for an event the
    client may not send. A failed measurement is not the reader's problem, and
    an error here would surface as a broken screen for something they cannot
    see or act on.
    """
    try:
        definition = definition_for(payload.name)
    except UnknownEventError:
        return TrackEventResponse(recorded=False)

    if not definition.client_emittable:
        return TrackEventResponse(recorded=False)

    await service.record(db, name=payload.name, user=user, properties=payload.properties)
    await db.commit()
    return TrackEventResponse(recorded=True)
