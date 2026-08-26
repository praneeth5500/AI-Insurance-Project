"""Product endpoints.

`docs/08_API_CONTRACTS.md` section 5 names the path
`/product-versions/{id}`. Product versions arrive in Phase 8; until then the
identifier is a synthetic product reference, so the path says `/products`.
Recorded in `docs/SPEC_ISSUES.md`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.products import service
from app.products.schemas import ProductDetailView, SaveResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{reference}", response_model=ProductDetailView, summary="One option in full")
async def get_product(
    reference: str, user: CurrentUser, db: DbSession, run: str = ""
) -> ProductDetailView:
    """`run` names the result set the reader came from.

    Fit is a judgement about a person, and it only exists inside a run. Given
    one, the page shows exactly what that run recorded — the same three
    strengths the match card headlined, in the same order. Without one it
    shows the policy's facts and says so.
    """
    detail = await service.get_detail(
        db, user=user, product_reference=reference, run_id=run or None
    )
    return ProductDetailView.of(detail)


@router.put("/{reference}/saved", response_model=SaveResponse, summary="Save an option")
async def save_product(reference: str, user: CurrentUser, db: DbSession) -> SaveResponse:
    saved = await service.save(db, user=user, product_reference=reference)
    return SaveResponse(reference=reference, saved=saved)


@router.delete("/{reference}/saved", response_model=SaveResponse, summary="Unsave an option")
async def unsave_product(reference: str, user: CurrentUser, db: DbSession) -> SaveResponse:
    saved = await service.unsave(db, user=user, product_reference=reference)
    return SaveResponse(reference=reference, saved=saved)
