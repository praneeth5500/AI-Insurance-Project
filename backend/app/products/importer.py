"""The manual verified-data importer.

docs/11_BUILD_PLAN.md Phase 8 ends with a warning rather than a requirement:
**"Do not scrape random websites into production data."** This module is how
that warning is enforced.

Nothing reaches the canonical catalogue without:

* a `sourceType` of MANUALLY_VERIFIED or PARTNER_API — synthetic data is
  refused outright, so a demo product can never be laundered into the real
  catalogue;
* a source name and a source reference — *which document, and where in it*;
* a `verifiedAt` timestamp that is not in the future;
* a `verifiedBy` — the person who checked it. A verified claim that cannot be
  traced to a human is not verified.

Every rejection names the field and the record, because an import that fails
silently on one product is worse than one that fails loudly on all of them.

Import is idempotent by (product, versionLabel): re-importing the same version
replaces its facts rather than duplicating them. Terms that have changed
belong in a **new version**, never an edit — a recommendation made last month
was made against last month's terms
(docs/04_BACKEND_ARCHITECTURE.md section 9).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_fields
from app.db.types import utcnow
from app.products.models import InsuranceProduct, Insurer, ProductFact, ProductVersion

logger = logging.getLogger(__name__)

#: The only origins allowed into the canonical catalogue.
IMPORTABLE_SOURCE_TYPES = frozenset({"MANUALLY_VERIFIED", "PARTNER_API"})

PLACEHOLDER_MARKERS = ("REPLACE_ME", "TODO", "XXX", "CHANGEME")


class ImportError_(ValueError):
    """A refusal to import, with the reason a human needs to fix it."""


class FactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str = Field(alias="factKey", min_length=1)
    value: dict[str, object] | list[object] | str | int | float | bool
    critical_for_matching: bool = Field(alias="criticalForMatching", default=False)
    source_reference: str | None = Field(alias="sourceReference", default=None)
    source_page: int | None = Field(alias="sourcePage", default=None)

    @field_validator("fact_key")
    @classmethod
    def _no_placeholder_key(cls, value: str) -> str:
        _reject_placeholder(value, "factKey")
        return value


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    insurer_name: str = Field(alias="insurerName", min_length=1)
    product_name: str = Field(alias="productName", min_length=1)
    domain: str
    version_label: str = Field(alias="versionLabel", min_length=1)
    uin_or_reference: str | None = Field(alias="uinOrReference", default=None)
    effective_from: datetime | None = Field(alias="effectiveFrom", default=None)
    effective_to: datetime | None = Field(alias="effectiveTo", default=None)

    source_type: str = Field(alias="sourceType")
    source_name: str = Field(alias="sourceName", min_length=1)
    source_reference: str = Field(alias="sourceReference", min_length=1)
    verified_at: datetime = Field(alias="verifiedAt")
    verified_by: str = Field(alias="verifiedBy", min_length=1)

    facts: list[FactInput] = Field(default_factory=list)

    @field_validator("source_type")
    @classmethod
    def _importable_source(cls, value: str) -> str:
        if value not in IMPORTABLE_SOURCE_TYPES:
            raise ValueError(
                f"sourceType must be one of {sorted(IMPORTABLE_SOURCE_TYPES)}; "
                f"got {value!r}. Synthetic data belongs in the demo catalogue, "
                "not the verified one."
            )
        return value

    @field_validator("domain")
    @classmethod
    def _known_domain(cls, value: str) -> str:
        if value not in ("HEALTH", "MOTOR"):
            raise ValueError(f"domain must be HEALTH or MOTOR; got {value!r}")
        return value

    @field_validator(
        "insurer_name",
        "product_name",
        "version_label",
        "source_name",
        "source_reference",
        "verified_by",
    )
    @classmethod
    def _no_placeholder(cls, value: str) -> str:
        _reject_placeholder(value, "value")
        return value


def _reject_placeholder(value: str, field_name: str) -> None:
    """A template that was never filled in must not import.

    The shipped template is full of REPLACE_ME, so running the importer
    against it fails rather than creating a catalogue of placeholders.
    """
    upper = value.upper()
    if any(marker in upper for marker in PLACEHOLDER_MARKERS):
        raise ValueError(
            f"{field_name} still contains a template placeholder ({value!r}). "
            "Fill the template in before importing."
        )


class ImportFile(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    versions: list[VersionInput]


@dataclass
class ImportReport:
    inserted_versions: int = 0
    replaced_versions: int = 0
    inserted_facts: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_file(payload: object) -> ImportFile:
    """Parse and validate, refusing the whole file if any record is wrong."""
    try:
        parsed = ImportFile.model_validate(payload)
    except Exception as error:  # pydantic raises its own type
        raise ImportError_(str(error)) from error

    if not parsed.versions:
        raise ImportError_("The file contains no product versions.")

    now = utcnow()
    for index, version in enumerate(parsed.versions):
        prefix = f"versions[{index}] ({version.insurer_name} / {version.product_name})"
        if version.verified_at > now:
            raise ImportError_(f"{prefix}: verifiedAt is in the future.")
        if (
            version.effective_to is not None
            and version.effective_from is not None
            and version.effective_to <= version.effective_from
        ):
            raise ImportError_(f"{prefix}: effectiveTo is not after effectiveFrom.")
        keys = [fact.fact_key for fact in version.facts]
        if len(keys) != len(set(keys)):
            raise ImportError_(f"{prefix}: duplicate factKey in the same version.")

    return parsed


async def import_versions(db: AsyncSession, payload: object) -> ImportReport:
    """Validate, then write. Nothing is written unless everything validates."""
    parsed = validate_file(payload)
    report = ImportReport()

    for version_input in parsed.versions:
        insurer = await _get_or_create_insurer(db, version_input.insurer_name)
        product = await _get_or_create_product(db, insurer, version_input)

        existing = (
            await db.execute(
                select(ProductVersion).where(
                    ProductVersion.product_id == product.id,
                    ProductVersion.version_label == version_input.version_label,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            version = ProductVersion(
                product_id=product.id,
                version_label=version_input.version_label,
                uin_or_reference=version_input.uin_or_reference,
                effective_from=version_input.effective_from,
                effective_to=version_input.effective_to,
                active=True,
                source_type=version_input.source_type,
                source_name=version_input.source_name,
                source_reference=version_input.source_reference,
                verified_at=version_input.verified_at,
                verified_by=version_input.verified_by,
            )
            db.add(version)
            await db.flush()
            report.inserted_versions += 1
        else:
            # Re-verifying the same version updates its provenance; the terms
            # themselves are identified by the version label, so a change of
            # terms must arrive as a new label.
            existing.source_name = version_input.source_name
            existing.source_reference = version_input.source_reference
            existing.verified_at = version_input.verified_at
            existing.verified_by = version_input.verified_by
            existing.uin_or_reference = version_input.uin_or_reference
            existing.effective_from = version_input.effective_from
            existing.effective_to = version_input.effective_to
            await db.execute(
                delete(ProductFact).where(ProductFact.product_version_id == existing.id)
            )
            version = existing
            report.replaced_versions += 1

        for fact in version_input.facts:
            db.add(
                ProductFact(
                    product_version_id=version.id,
                    fact_key=fact.fact_key,
                    value_json={"value": fact.value},
                    critical_for_matching=fact.critical_for_matching,
                    source_reference=fact.source_reference or version_input.source_reference,
                    source_page=fact.source_page,
                    verified_at=version_input.verified_at,
                )
            )
            report.inserted_facts += 1

    await db.commit()
    # Counts only: product terms are not log material.
    logger.info(
        "product_import_completed",
        extra=log_fields(event="product_import_completed", resource_type="product_version"),
    )
    return report


async def _get_or_create_insurer(db: AsyncSession, name: str) -> Insurer:
    insurer = (await db.execute(select(Insurer).where(Insurer.name == name))).scalar_one_or_none()
    if insurer is None:
        insurer = Insurer(name=name, active=True)
        db.add(insurer)
        await db.flush()
    return insurer


async def _get_or_create_product(
    db: AsyncSession, insurer: Insurer, version_input: VersionInput
) -> InsuranceProduct:
    product = (
        await db.execute(
            select(InsuranceProduct).where(
                InsuranceProduct.insurer_id == insurer.id,
                InsuranceProduct.name == version_input.product_name,
            )
        )
    ).scalar_one_or_none()
    if product is None:
        product = InsuranceProduct(
            insurer_id=insurer.id,
            domain=version_input.domain,
            name=version_input.product_name,
        )
        db.add(product)
        await db.flush()
    return product
