"""Decoder endpoints.

Behind the same feature flag as upload, and scoped to the policy's owner by
the service — there is no version of this that can decode someone else's
document.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.decoder import service
from app.decoder.schemas import DecoderView
from app.policies.dependencies import DecoderEnabled

router = APIRouter(prefix="/policies", tags=["decoder"], dependencies=[DecoderEnabled])


@router.get("/{policy_id}/decoded", response_model=DecoderView, summary="Read a policy")
async def decoded_policy(policy_id: str, user: CurrentUser, db: DbSession) -> DecoderView:
    return DecoderView.of(await service.decode(db, user=user, policy_id=policy_id))
