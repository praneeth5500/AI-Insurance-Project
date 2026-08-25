"""Database access for the questionnaire."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.questionnaires.models import (
    STATUS_IN_PROGRESS,
    QuestionnaireAnswer,
    QuestionnaireSession,
)


async def get_session_for_user(
    db: AsyncSession, *, session_id: str, user_id: str
) -> QuestionnaireSession | None:
    """Scoped to the owner, so one user can never read another's answers."""
    result = await db.execute(
        select(QuestionnaireSession).where(
            QuestionnaireSession.id == session_id,
            QuestionnaireSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_active_session(
    db: AsyncSession, *, user_id: str, domain: str, version: str
) -> QuestionnaireSession | None:
    """The user's in-progress draft for this questionnaire version.

    Version-scoped on purpose: a draft answered against an older question set
    must not be silently resumed against a newer one.
    """
    result = await db.execute(
        select(QuestionnaireSession)
        .where(
            QuestionnaireSession.user_id == user_id,
            QuestionnaireSession.domain == domain,
            QuestionnaireSession.questionnaire_version == version,
            QuestionnaireSession.status == STATUS_IN_PROGRESS,
        )
        .order_by(QuestionnaireSession.started_at.desc())
    )
    return result.scalars().first()


async def list_answers(db: AsyncSession, *, session_id: str) -> list[QuestionnaireAnswer]:
    result = await db.execute(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.session_id == session_id)
    )
    return list(result.scalars().all())


async def get_answer(
    db: AsyncSession, *, session_id: str, question_id: str
) -> QuestionnaireAnswer | None:
    result = await db.execute(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.session_id == session_id,
            QuestionnaireAnswer.question_id == question_id,
        )
    )
    return result.scalar_one_or_none()
