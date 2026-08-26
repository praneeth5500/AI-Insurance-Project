"""Prices the matching engine is allowed to use.

The budget dimension can only be evaluated against a price that is real,
current and annual. Everything else — no price, an expired quote, a stale
estimate, a monthly figure compared against a yearly budget — is a reason to
report "not enough verified data", not a reason to approximate.

Today this returns nothing for every product: the synthetic catalogue has no
price and no partner is integrated. The lookup exists anyway so the seam is
real and so the budget evaluator has one place to get a number from when there
finally is one.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pricing import service as pricing_service
from app.pricing.models import BILLING_PERIOD_YEAR, ProductPrice
from app.pricing.service import DisplayablePrice


async def annual_prices_inr(db: AsyncSession, references: list[str]) -> dict[str, int]:
    """Annual rupee amounts for the references that have a usable price.

    A reference with no usable price is simply absent from the result, which
    is what makes the budget dimension report a gap instead of a number.
    """
    if not references:
        return {}

    rows = list(
        (
            await db.execute(
                select(ProductPrice)
                .where(
                    ProductPrice.product_version_id.in_(references),
                    ProductPrice.billing_period == BILLING_PERIOD_YEAR,
                )
                .order_by(ProductPrice.generated_at.desc())
            )
        )
        .scalars()
        .all()
    )

    prices: dict[str, int] = {}
    for price in rows:
        # Ordered newest first, so the first usable price for a version wins.
        if price.product_version_id in prices:
            continue
        evaluated = pricing_service.evaluate(price)
        if isinstance(evaluated, DisplayablePrice):
            # Stored in paise; the questionnaire asks for rupees.
            prices[price.product_version_id] = evaluated.amount_minor // 100
    return prices
