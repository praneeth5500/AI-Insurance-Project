"""The insurance product provider interface.

docs/04_BACKEND_ARCHITECTURE.md section 3 fixes the shape and the rule:
"Do not couple product logic to one vendor." The partner API itself is
undecided (docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 5), so only the
interface and two local implementations exist here.

`get_quote` deliberately raises in every implementation. A quote is a real
premium from a real insurer; returning anything else — an estimate, a range,
a placeholder — would be inventing a price, which CLAUDE.md forbids outright.
Failing loudly means a caller cannot accidentally ship a fabricated number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.catalogue import all_products, get_product
from app.products.facts import CRITICAL_FACT_KEYS
from app.products.freshness import critical_facts_usable, version_usable
from app.products.models import InsuranceProduct, Insurer, ProductFact, ProductVersion
from app.products.provenance import SYNTHETIC, SourceType


@dataclass(frozen=True)
class ProviderProduct:
    """What every provider returns, whatever its source.

    Provenance is part of the shape, not an optional extra: a consumer can
    always tell whether it is holding a demo product or a verified one.
    """

    reference: str
    insurer_name: str
    product_name: str
    domain: str
    source_type: SourceType
    version_label: str
    facts: dict[str, Any]
    #: Absent for synthetic products, which were never verified.
    verified_at_iso: str | None = None
    source_name: str | None = None
    source_reference: str | None = None


class QuoteNotAvailableError(RuntimeError):
    """Raised instead of returning a price we do not have."""


class InsuranceProductProvider(Protocol):
    """docs/04_BACKEND_ARCHITECTURE.md section 3."""

    source_type: SourceType

    async def list_products(self, *, domain: str) -> list[ProviderProduct]: ...

    async def get_product(self, *, reference: str) -> ProviderProduct | None: ...

    async def get_quote(self, *, reference: str, request: dict[str, Any]) -> Any: ...


class SyntheticCatalogueProvider:
    """The demo catalogue, behind the same interface as real data.

    Exists so the seam is real: everything downstream reads products through a
    provider, and swapping in verified data is a configuration change rather
    than a rewrite.
    """

    source_type: SourceType = SYNTHETIC

    async def list_products(self, *, domain: str) -> list[ProviderProduct]:
        if domain != "HEALTH":
            return []
        return [self._convert(product) for product in all_products()]

    async def get_product(self, *, reference: str) -> ProviderProduct | None:
        product = get_product(reference)
        return self._convert(product) if product else None

    async def get_quote(self, *, reference: str, request: dict[str, Any]) -> Any:
        raise QuoteNotAvailableError(
            "Synthetic products have no price. A quote can only come from an insurer."
        )

    @staticmethod
    def _convert(product: Any) -> ProviderProduct:
        return ProviderProduct(
            reference=product.id,
            insurer_name=product.insurer_name,
            product_name=product.product_name,
            domain="HEALTH",
            source_type=SYNTHETIC,
            version_label=product.catalogue_version,
            # The structured facts themselves, in the same shape a verified
            # version records them, so both reach the engine identically.
            facts=product.facts.model_dump(),
            verified_at_iso=None,
            source_name=None,
            source_reference=None,
        )


class VerifiedCatalogueProvider:
    """Products imported from verified sources.

    Only returns versions that pass the freshness rules — stale critical data
    is excluded rather than shown with a caveat
    (docs/13_DECISIONS_AND_OPEN_ITEMS.md).
    """

    source_type: SourceType = "MANUALLY_VERIFIED"

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_products(self, *, domain: str) -> list[ProviderProduct]:
        rows = (
            await self._db.execute(
                select(ProductVersion, InsuranceProduct, Insurer)
                .join(InsuranceProduct, ProductVersion.product_id == InsuranceProduct.id)
                .join(Insurer, InsuranceProduct.insurer_id == Insurer.id)
                .where(
                    InsuranceProduct.domain == domain,
                    ProductVersion.active.is_(True),
                    Insurer.active.is_(True),
                )
            )
        ).all()

        products: list[ProviderProduct] = []
        for version, product, insurer in rows:
            if not version_usable(version).usable:
                continue
            if not await self._critical_facts_usable(version):
                continue
            products.append(await self._convert(version, product, insurer))
        return products

    async def get_product(self, *, reference: str) -> ProviderProduct | None:
        row = (
            await self._db.execute(
                select(ProductVersion, InsuranceProduct, Insurer)
                .join(InsuranceProduct, ProductVersion.product_id == InsuranceProduct.id)
                .join(Insurer, InsuranceProduct.insurer_id == Insurer.id)
                .where(ProductVersion.id == reference)
            )
        ).first()
        if row is None:
            return None

        version, product, insurer = row
        if not version_usable(version).usable:
            return None
        if not await self._critical_facts_usable(version):
            return None
        return await self._convert(version, product, insurer)

    async def get_quote(self, *, reference: str, request: dict[str, Any]) -> Any:
        raise QuoteNotAvailableError(
            "No insurance partner is integrated yet, so no quote can be produced. "
            "See open item 5 in docs/13_DECISIONS_AND_OPEN_ITEMS.md."
        )

    async def _critical_facts_usable(self, version: ProductVersion) -> bool:
        """A version missing a fact the engine must have is not offered.

        docs/06_RECOMMENDATION_ENGINE.md section 4 makes missing or stale
        critical data a hard failure. Enforced here, at the seam, so no
        consumer can reach a version the engine could only guess about.
        """
        facts = list(
            (
                await self._db.execute(
                    select(ProductFact).where(ProductFact.product_version_id == version.id)
                )
            )
            .scalars()
            .all()
        )
        return critical_facts_usable(facts, required_keys=set(CRITICAL_FACT_KEYS)).usable

    async def _convert(
        self, version: ProductVersion, product: InsuranceProduct, insurer: Insurer
    ) -> ProviderProduct:
        facts = (
            (
                await self._db.execute(
                    select(ProductFact).where(ProductFact.product_version_id == version.id)
                )
            )
            .scalars()
            .all()
        )
        return ProviderProduct(
            reference=version.id,
            insurer_name=insurer.name,
            product_name=product.name,
            domain=product.domain,
            source_type=version.source_type,  # type: ignore[arg-type]
            version_label=version.version_label,
            facts={fact.fact_key: fact.value_json for fact in facts},
            verified_at_iso=version.verified_at.isoformat(),
            source_name=version.source_name,
            source_reference=version.source_reference,
        )
