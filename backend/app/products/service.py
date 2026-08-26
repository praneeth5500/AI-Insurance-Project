"""Product detail and saving.

The detail screen shows two different things and keeps them apart:

* the policy's **facts**, stated from what is recorded about it;
* the **fit** for this reader, which only exists inside a recommendation run.

So the fit comes from the run the reader arrived from, read back rather than
recomputed. A run is immutable, so opening an option from a result set months
later shows what that result set actually said — not what today's engine would
say about today's catalogue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_fields
from app.products.catalogue import SyntheticProduct, get_product
from app.products.errors import ProductNotFoundError
from app.products.models import SavedProduct
from app.products.sections import PolicySectionView, build_policy_sections
from app.users.models import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductFitEntry:
    """One dimension's judgement, as a run recorded it."""

    factor: str
    label: str
    note: str


@dataclass(frozen=True)
class ProductDetail:
    product: SyntheticProduct
    sections: list[PolicySectionView]
    saved: bool
    #: Empty when the reader did not arrive from a run. The page then states
    #: the policy's facts and says plainly that no personal assessment applies,
    #: rather than inventing a user-independent "fit".
    fits: list[ProductFitEntry]
    highlights: list[str]


async def is_saved(db: AsyncSession, *, user: User, product_reference: str) -> bool:
    result = await db.execute(
        select(SavedProduct).where(
            SavedProduct.user_id == user.id,
            SavedProduct.product_reference == product_reference,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_detail(
    db: AsyncSession, *, user: User, product_reference: str, run_id: str | None = None
) -> ProductDetail:
    product = get_product(product_reference)
    if product is None:
        raise ProductNotFoundError

    fits: list[ProductFitEntry] = []
    highlights: list[str] = []
    if run_id:
        # Imported here rather than at module scope: the recommendation
        # service already reads products, and a module-level import both ways
        # would be a cycle.
        from app.recommendations import service as recommendation_service

        candidate = await recommendation_service.candidate_in_run(
            db, user=user, run_id=run_id, product_reference=product_reference
        )
        if candidate is not None:
            payload = candidate.reason_summary_json
            fits = [
                ProductFitEntry(factor=entry["factor"], label=entry["label"], note=entry["note"])
                for entry in payload.get("fits", [])
            ]
            highlights = list(payload.get("highlightFactors", []))

    return ProductDetail(
        product=product,
        sections=build_policy_sections(product.facts),
        saved=await is_saved(db, user=user, product_reference=product_reference),
        fits=fits,
        highlights=highlights,
    )


async def save(db: AsyncSession, *, user: User, product_reference: str) -> bool:
    """Save an option. Idempotent — saving twice leaves one row."""
    if get_product(product_reference) is None:
        raise ProductNotFoundError

    if not await is_saved(db, user=user, product_reference=product_reference):
        db.add(SavedProduct(user_id=user.id, product_reference=product_reference))
        await db.commit()
        logger.info(
            "product_saved",
            extra=log_fields(event="product_saved", user_id=user.id, resource_type="saved_product"),
        )
    return True


async def unsave(db: AsyncSession, *, user: User, product_reference: str) -> bool:
    """Remove a saved option. Removing what was never saved is not an error."""
    await db.execute(
        delete(SavedProduct).where(
            SavedProduct.user_id == user.id,
            SavedProduct.product_reference == product_reference,
        )
    )
    await db.commit()
    return False


async def list_saved(db: AsyncSession, *, user: User) -> list[str]:
    result = await db.execute(
        select(SavedProduct.product_reference)
        .where(SavedProduct.user_id == user.id)
        .order_by(SavedProduct.created_at.desc())
    )
    return list(result.scalars().all())
