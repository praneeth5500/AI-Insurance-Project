"""Recommendation endpoints (docs/08_API_CONTRACTS.md section 4)."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.recommendations import service
from app.recommendations.schemas import (
    ComparisonView,
    CreateComparisonRequest,
    CreateRunRequest,
    RunView,
    UpdatePrioritiesRequest,
)

router = APIRouter(prefix="/recommendation-runs", tags=["recommendations"])

#: docs/08_API_CONTRACTS.md section 6 puts comparisons at their own path.
comparison_router = APIRouter(prefix="/comparisons", tags=["recommendations"])


@router.post("", response_model=RunView, summary="Produce a match set")
async def create_run(payload: CreateRunRequest, user: CurrentUser, db: DbSession) -> RunView:
    """Returns the finished set directly.

    The contract allows a PROCESSING status for an asynchronous engine. The
    prototype ordering is deterministic and immediate, so reporting PROCESSING
    would describe work that is not happening. The response shape still
    carries `status`, so an asynchronous Phase 9 engine needs no contract
    change.
    """
    result = await service.create_run(
        db, user=user, questionnaire_session_id=payload.questionnaire_session_id
    )
    return RunView.of(result)


@router.get("/{run_id}", response_model=RunView, summary="Read a match set")
async def get_run(run_id: str, user: CurrentUser, db: DbSession) -> RunView:
    return RunView.of(await service.get_run(db, user=user, run_id=run_id))


@router.patch(
    "/{run_id}/priorities",
    response_model=RunView,
    summary="Re-order a match set against changed priorities",
)
async def update_priorities(
    run_id: str, payload: UpdatePrioritiesRequest, user: CurrentUser, db: DbSession
) -> RunView:
    result, previous_order = await service.update_priorities(
        db, user=user, run_id=run_id, priorities=payload.priorities
    )
    current_order = [candidate.product_reference for candidate in result.candidates]
    moved = [
        reference
        for index, reference in enumerate(current_order)
        if index >= len(previous_order) or previous_order[index] != reference
    ]
    return RunView.of(result, reordered=moved)


@comparison_router.post("", response_model=ComparisonView, summary="Compare 2 or 3 options")
async def create_comparison(
    payload: CreateComparisonRequest, user: CurrentUser, db: DbSession
) -> ComparisonView:
    result = await service.compare(
        db,
        user=user,
        run_id=payload.recommendation_run_id,
        product_references=payload.product_references,
    )
    return ComparisonView.of(result)
