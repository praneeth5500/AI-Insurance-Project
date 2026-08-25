"""Questionnaire endpoints (docs/08_API_CONTRACTS.md section 3).

`POST /questionnaire-sessions` resumes an in-progress draft rather than always
creating a new one, so returning to the flow continues where the user left off
instead of silently abandoning their answers.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser, DbSession
from app.questionnaires import service
from app.questionnaires.schemas import (
    CreateSessionRequest,
    SaveAnswerRequest,
    SessionView,
)

router = APIRouter(prefix="/questionnaire-sessions", tags=["questionnaire"])


@router.post(
    "",
    response_model=SessionView,
    status_code=status.HTTP_200_OK,
    summary="Start or resume a questionnaire draft",
)
async def create_session(
    payload: CreateSessionRequest, user: CurrentUser, db: DbSession
) -> SessionView:
    session = await service.start_or_resume(db, user=user, domain=payload.domain)
    state = await service.load_state(db, user=user, session_id=session.id)
    return SessionView.of(state)


@router.get("/{session_id}", response_model=SessionView, summary="Read a draft")
async def get_session(session_id: str, user: CurrentUser, db: DbSession) -> SessionView:
    state = await service.load_state(db, user=user, session_id=session_id)
    return SessionView.of(state)


@router.put(
    "/{session_id}/answers/{question_id}",
    response_model=SessionView,
    summary="Save one answer",
)
async def save_answer(
    session_id: str,
    question_id: str,
    payload: SaveAnswerRequest,
    user: CurrentUser,
    db: DbSession,
) -> SessionView:
    state = await service.save_answer(
        db, user=user, session_id=session_id, question_id=question_id, value=payload.value
    )
    return SessionView.of(state)


@router.post(
    "/{session_id}/complete",
    response_model=SessionView,
    summary="Submit the draft once every required answer exists",
)
async def complete_session(session_id: str, user: CurrentUser, db: DbSession) -> SessionView:
    state = await service.complete(db, user=user, session_id=session_id)
    return SessionView.of(state)
