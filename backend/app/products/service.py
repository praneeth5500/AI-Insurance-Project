"""Product detail and saving."""

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
class ProductDetail:
    product: SyntheticProduct
    sections: list[PolicySectionView]
    saved: bool


async def is_saved(db: AsyncSession, *, user: User, product_reference: str) -> bool:
    result = await db.execute(
        select(SavedProduct).where(
            SavedProduct.user_id == user.id,
            SavedProduct.product_reference == product_reference,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_detail(db: AsyncSession, *, user: User, product_reference: str) -> ProductDetail:
    product = get_product(product_reference)
    if product is None:
        raise ProductNotFoundError

    return ProductDetail(
        product=product,
        sections=build_policy_sections(product),
        saved=await is_saved(db, user=user, product_reference=product_reference),
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
