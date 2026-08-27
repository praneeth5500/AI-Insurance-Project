"""Claims readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.claims import service
from app.claims.schemas import ChecklistView, UpdateItemRequest
from app.policies.dependencies import DecoderEnabled

router = APIRouter(prefix="/policies", tags=["claims"], dependencies=[DecoderEnabled])


@router.get(
    "/{policy_id}/claims-checklist",
    response_model=ChecklistView,
    summary="Your claims checklist for this policy",
)
async def checklist(policy_id: str, user: CurrentUser, db: DbSession) -> ChecklistView:
    return ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))


@router.patch(
    "/{policy_id}/claims-checklist/{item_id}",
    response_model=ChecklistView,
    summary="Tick an item off, or note something against it",
)
async def update_item(
    policy_id: str,
    item_id: str,
    payload: UpdateItemRequest,
    user: CurrentUser,
    db: DbSession,
) -> ChecklistView:
    return ChecklistView.of(
        await service.update_item(
            db,
            user=user,
            policy_id=policy_id,
            item_id=item_id,
            completed=payload.completed,
            note=payload.note,
        )
    )
