"""The canonical product catalogue, and saved options.

The catalogue tables follow docs/05_DATA_MODEL.md section 4. Nothing is
imported into them by this phase: they are the destination for manually
verified data and, later, for a partner integration. The synthetic catalogue
in `catalogue.py` stays separate and is never written here — a demo product
must never be able to masquerade as a verified one.

Saved options.

`docs/11_BUILD_PLAN.md` Phase 7 asks for "save", but `docs/05_DATA_MODEL.md`
defines no table for it — recorded in `docs/SPEC_ISSUES.md`.

Kept as thin as possible: who saved what, and when. It deliberately does not
copy any product detail, so a saved option can never drift out of step with
the catalogue it points at.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column


class SavedProduct(Base):
    __tablename__ = "saved_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sv"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: The synthetic product reference. Becomes a product_version_id in Phase 8.
    product_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (
        # Saving twice is the same as saving once.
        UniqueConstraint("user_id", "product_reference", name="uq_saved_user_product"),
    )


class Insurer(Base):
    """docs/05_DATA_MODEL.md section 4."""

    __tablename__ = "insurers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ins"))
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    #: Identifier in a partner system, once one is integrated.
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())


class InsuranceProduct(Base):
    """A product line. Its terms live on versions, never here."""

    __tablename__ = "insurance_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("prd"))
    insurer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("insurers.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("insurer_id", "name", name="uq_product_insurer_name"),
        Index("ix_insurance_products_domain", "domain"),
    )


class ProductVersion(Base):
    """One version of a product's terms.

    Terms change. A recommendation made last month was made against the terms
    that applied then, so versions are never edited in place — a change is a
    new version (docs/04_BACKEND_ARCHITECTURE.md section 9).

    Provenance is not optional: `source_type`, `source_name`, `source_reference`
    and `verified_at` are all NOT NULL, so a version cannot exist without a
    record of where its facts came from and who checked them.
    """

    __tablename__ = "product_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pv"))
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("insurance_products.id", ondelete="CASCADE"), nullable=False
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    #: The regulator's unique identification number, or the insurer's own
    #: reference for this wording.
    uin_or_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effective_from: Mapped[datetime | None] = timestamp_column(nullable=True)
    effective_to: Mapped[datetime | None] = timestamp_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #: SYNTHETIC | MANUALLY_VERIFIED | PARTNER_API
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Which document or system this came from.
    source_name: Mapped[str] = mapped_column(String(300), nullable=False)
    #: Where inside it — a page, a clause, an endpoint.
    source_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    #: When a human last checked this against the source.
    verified_at: Mapped[datetime] = timestamp_column(nullable=False)
    #: Who checked it. Not in the logical model; added so a verified claim can
    #: be traced to a person (docs/SPEC_ISSUES.md).
    verified_by: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("product_id", "version_label", name="uq_version_product_label"),
        Index("ix_product_versions_active", "product_id", "active"),
    )


class ProductFact(Base):
    """One fact about one product version.

    `critical_for_matching` is the important flag: a critical fact that is
    missing or stale removes the product from matching rather than being
    treated as neutral (docs/06_RECOMMENDATION_ENGINE.md sections 4 and 8).
    """

    __tablename__ = "product_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pf"))
    product_version_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False
    )
    fact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    #: The comparable form, once the engine knows how to normalise this key.
    normalized_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    critical_for_matching: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_reference: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified_at: Mapped[datetime] = timestamp_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("product_version_id", "fact_key", name="uq_fact_version_key"),
    )
