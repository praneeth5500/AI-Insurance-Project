"""The real data domain layer (docs/11_BUILD_PLAN.md Phase 8)."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import utcnow
from app.pricing.models import ProductPrice
from app.pricing.service import DisplayablePrice, SuppressedPrice, evaluate
from app.products.freshness import (
    DEFAULT_MAX_VERIFICATION_AGE,
    critical_facts_usable,
    version_usable,
)
from app.products.importer import ImportError_, import_versions, validate_file
from app.products.models import Insurer, ProductFact, ProductVersion
from app.products.provider import (
    QuoteNotAvailableError,
    SyntheticCatalogueProvider,
    VerifiedCatalogueProvider,
)

NOW = utcnow()


def version_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "insurerName": "Example Assurance",
        "productName": "Health Plan",
        "domain": "HEALTH",
        "versionLabel": "2026-04 wording",
        "uinOrReference": "UIN-EXAMPLE-001",
        "sourceType": "MANUALLY_VERIFIED",
        "sourceName": "Policy wording v3.pdf",
        "sourceReference": "Section 4.2, page 11",
        "verifiedAt": (NOW - timedelta(days=1)).isoformat(),
        "verifiedBy": "A Reviewer",
        "facts": [
            {
                "factKey": "ped_waiting_period",
                "value": {"months": 36},
                "criticalForMatching": True,
                "sourcePage": 11,
            }
        ],
    }
    payload.update(overrides)
    return payload


def file_payload(**overrides: object) -> dict[str, object]:
    return {"versions": [version_payload(**overrides)]}


# ------------------------------------------------------------- the importer --


def test_a_file_without_provenance_is_refused() -> None:
    """Phase 8: "Do not scrape random websites into production data"."""
    for missing in ("sourceName", "sourceReference", "verifiedAt", "verifiedBy"):
        payload = file_payload()
        del payload["versions"][0][missing]  # type: ignore[index]

        with pytest.raises(ImportError_) as raised:
            validate_file(payload)

        assert missing in str(raised.value)


def test_synthetic_data_cannot_be_imported_as_verified() -> None:
    """A demo product must never be laundered into the real catalogue."""
    with pytest.raises(ImportError_, match="sourceType"):
        validate_file(file_payload(sourceType="SYNTHETIC"))


def test_a_partner_source_is_importable() -> None:
    parsed = validate_file(file_payload(sourceType="PARTNER_API"))

    assert parsed.versions[0].source_type == "PARTNER_API"


def test_verification_cannot_be_dated_in_the_future() -> None:
    with pytest.raises(ImportError_, match="future"):
        validate_file(file_payload(verifiedAt=(NOW + timedelta(days=1)).isoformat()))


def test_an_unfilled_template_is_refused() -> None:
    """The shipped template is placeholders, so it cannot import as-is."""
    with pytest.raises(ImportError_, match="placeholder"):
        validate_file(file_payload(insurerName="REPLACE_ME — the insurer's name"))


def test_the_shipped_template_does_not_import() -> None:
    template = json.loads(
        (Path(__file__).parent.parent / "examples" / "products.template.json").read_text()
    )
    payload = {key: value for key, value in template.items() if not key.startswith("_")}

    with pytest.raises(ImportError_):
        validate_file(payload)


def test_an_empty_file_is_refused() -> None:
    with pytest.raises(ImportError_, match="no product versions"):
        validate_file({"versions": []})


def test_unknown_fields_are_refused_rather_than_ignored() -> None:
    """A typo in a provenance field must fail, not silently drop the value."""
    with pytest.raises(ImportError_):
        validate_file(file_payload(verifiedByy="A Reviewer"))


def test_duplicate_fact_keys_are_refused() -> None:
    facts = [
        {"factKey": "copay", "value": {"percent": 0}},
        {"factKey": "copay", "value": {"percent": 10}},
    ]

    with pytest.raises(ImportError_, match="duplicate"):
        validate_file(file_payload(facts=facts))


def test_an_unknown_domain_is_refused() -> None:
    with pytest.raises(ImportError_, match="domain"):
        validate_file(file_payload(domain="TRAVEL"))


async def test_import_writes_the_version_with_full_provenance(db: AsyncSession) -> None:
    report = await import_versions(db, file_payload())

    assert report.inserted_versions == 1
    assert report.inserted_facts == 1

    version = (await db.execute(select(ProductVersion))).scalar_one()
    assert version.source_type == "MANUALLY_VERIFIED"
    assert version.source_name == "Policy wording v3.pdf"
    assert version.source_reference == "Section 4.2, page 11"
    assert version.verified_by == "A Reviewer"


async def test_critical_facts_are_flagged_and_dated(db: AsyncSession) -> None:
    """docs/12_BETA_CHECKLIST.md: critical real-product facts have a
    verified timestamp."""
    await import_versions(db, file_payload())

    fact = (await db.execute(select(ProductFact))).scalar_one()
    assert fact.critical_for_matching is True
    assert fact.verified_at is not None
    assert fact.source_page == 11


async def test_re_importing_the_same_version_replaces_rather_than_duplicates(
    db: AsyncSession,
) -> None:
    await import_versions(db, file_payload())
    report = await import_versions(db, file_payload())

    assert report.replaced_versions == 1
    assert len((await db.execute(select(ProductVersion))).scalars().all()) == 1
    assert len((await db.execute(select(ProductFact))).scalars().all()) == 1


async def test_a_new_version_label_creates_a_new_version(db: AsyncSession) -> None:
    """Changed terms are a new version, never an edit."""
    await import_versions(db, file_payload())
    await import_versions(db, file_payload(versionLabel="2026-10 wording"))

    versions = (await db.execute(select(ProductVersion))).scalars().all()
    assert len(versions) == 2
    assert len((await db.execute(select(Insurer))).scalars().all()) == 1


async def test_nothing_is_written_when_any_record_is_invalid(db: AsyncSession) -> None:
    payload = {"versions": [version_payload(), version_payload(sourceType="SYNTHETIC")]}

    with pytest.raises(ImportError_):
        await import_versions(db, payload)

    assert (await db.execute(select(ProductVersion))).scalars().all() == []


# ------------------------------------------------------------- freshness ----


def _version(**overrides: object) -> ProductVersion:
    version = ProductVersion(
        product_id="prd_1",
        version_label="v1",
        active=True,
        source_type="MANUALLY_VERIFIED",
        source_name="doc",
        source_reference="page 1",
        verified_at=NOW - timedelta(days=1),
        verified_by="A Reviewer",
    )
    for key, value in overrides.items():
        setattr(version, key, value)
    return version


def test_a_recently_verified_version_is_usable() -> None:
    assert version_usable(_version(), now=NOW).usable is True


def test_a_stale_version_is_excluded_not_downgraded() -> None:
    """docs/13_DECISIONS_AND_OPEN_ITEMS.md: critical stale data is excluded."""
    stale = _version(verified_at=NOW - DEFAULT_MAX_VERIFICATION_AGE - timedelta(days=1))

    result = version_usable(stale, now=NOW)

    assert result.usable is False
    assert result.reason == "VERIFICATION_STALE"


def test_an_inactive_version_is_excluded() -> None:
    assert version_usable(_version(active=False), now=NOW).reason == "INACTIVE"


def test_a_superseded_version_is_excluded() -> None:
    superseded = _version(effective_to=NOW - timedelta(days=1))

    assert version_usable(superseded, now=NOW).reason == "SUPERSEDED"


def test_a_version_not_yet_in_effect_is_excluded() -> None:
    future = _version(effective_from=NOW + timedelta(days=1))

    assert version_usable(future, now=NOW).reason == "NOT_YET_EFFECTIVE"


def test_a_missing_critical_fact_excludes_the_product() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 8: unknown is never neutral."""
    result = critical_facts_usable([], required_keys={"copay"}, now=NOW)

    assert result.usable is False
    assert result.reason == "CRITICAL_FACT_MISSING"


def test_a_stale_critical_fact_excludes_the_product() -> None:
    fact = ProductFact(
        product_version_id="pv_1",
        fact_key="copay",
        value_json={"value": 0},
        critical_for_matching=True,
        verified_at=NOW - DEFAULT_MAX_VERIFICATION_AGE - timedelta(days=1),
    )

    result = critical_facts_usable([fact], required_keys={"copay"}, now=NOW)

    assert result.reason == "CRITICAL_FACT_STALE"


# ---------------------------------------------------------------- pricing ---


def _price(**overrides: object) -> ProductPrice:
    price = ProductPrice(
        product_version_id="pv_1",
        status="INDICATIVE",
        amount=1200000,
        currency="INR",
        billing_period="YEAR",
        source_type="PARTNER_API",
        source_name="Partner quote engine",
        generated_at=NOW - timedelta(days=1),
    )
    for key, value in overrides.items():
        setattr(price, key, value)
    return price


def test_a_missing_price_is_explained_not_blank() -> None:
    result = evaluate(None)

    assert isinstance(result, SuppressedPrice)
    assert result.reason == "NO_PRICE_RECORDED"
    assert "never from us" in result.explanation


def test_a_displayable_price_carries_state_source_and_timestamp() -> None:
    """docs/05_DATA_MODEL.md section 5: never display a price without them."""
    result = evaluate(_price())

    assert isinstance(result, DisplayablePrice)
    assert result.status == "INDICATIVE"
    assert result.source_name == "Partner quote engine"
    assert result.generated_at_iso


def test_an_indicative_price_is_never_called_final() -> None:
    result = evaluate(_price())

    assert isinstance(result, DisplayablePrice)
    assert result.label == "Indicative premium"
    assert "before underwriting" in result.explanation
    assert "final" not in result.label.lower()


def test_an_expired_quote_is_not_shown() -> None:
    result = evaluate(_price(status="QUOTED", valid_until=NOW - timedelta(hours=1)))

    assert isinstance(result, SuppressedPrice)
    assert result.reason == "EXPIRED"


def test_a_stale_estimate_is_not_shown() -> None:
    """An old estimate is worse than none: it looks current."""
    result = evaluate(_price(generated_at=NOW - timedelta(days=400)))

    assert isinstance(result, SuppressedPrice)
    assert result.reason == "STALE"


def test_an_unknown_price_state_is_not_guessed_at() -> None:
    result = evaluate(_price(status="ESTIMATED_SOMEHOW"))

    assert isinstance(result, SuppressedPrice)
    assert result.reason == "UNKNOWN_PRICE_STATE"


def test_unknown_tax_status_stays_unknown() -> None:
    result = evaluate(_price())

    assert isinstance(result, DisplayablePrice)
    assert result.taxes_included is None


# --------------------------------------------------------------- providers --


async def test_the_synthetic_provider_reports_its_own_source_type() -> None:
    provider = SyntheticCatalogueProvider()

    products = await provider.list_products(domain="HEALTH")

    assert len(products) == 10
    assert all(product.source_type == "SYNTHETIC" for product in products)
    assert all(product.verified_at_iso is None for product in products)


async def test_the_synthetic_provider_has_no_products_for_motor() -> None:
    assert await SyntheticCatalogueProvider().list_products(domain="MOTOR") == []


async def test_no_provider_will_invent_a_quote() -> None:
    """CLAUDE.md: never invent a premium. Failing loudly beats a placeholder."""
    with pytest.raises(QuoteNotAvailableError):
        await SyntheticCatalogueProvider().get_quote(reference="sp_meridian_core", request={})


async def test_the_verified_provider_returns_imported_products(
    db: AsyncSession,
) -> None:
    await import_versions(db, file_payload())

    products = await VerifiedCatalogueProvider(db).list_products(domain="HEALTH")

    assert len(products) == 1
    assert products[0].source_type == "MANUALLY_VERIFIED"
    assert products[0].verified_at_iso is not None
    assert products[0].source_name == "Policy wording v3.pdf"
    assert products[0].facts["ped_waiting_period"] == {"value": {"months": 36}}


async def test_the_verified_provider_excludes_stale_versions(db: AsyncSession) -> None:
    await import_versions(
        db,
        file_payload(
            verifiedAt=(NOW - DEFAULT_MAX_VERIFICATION_AGE - timedelta(days=1)).isoformat()
        ),
    )

    assert await VerifiedCatalogueProvider(db).list_products(domain="HEALTH") == []


async def test_the_verified_provider_will_not_quote_either(db: AsyncSession) -> None:
    with pytest.raises(QuoteNotAvailableError, match="open item 5"):
        await VerifiedCatalogueProvider(db).get_quote(reference="pv_1", request={})


async def test_the_verified_provider_keeps_domains_apart(db: AsyncSession) -> None:
    await import_versions(db, file_payload())

    assert await VerifiedCatalogueProvider(db).list_products(domain="MOTOR") == []
