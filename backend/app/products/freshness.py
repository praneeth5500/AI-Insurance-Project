"""When product data is too old to use.

docs/13_DECISIONS_AND_OPEN_ITEMS.md decides it: "Critical stale product data
excluded". docs/06_RECOMMENDATION_ENGINE.md section 4 makes stale critical
data a *hard* failure — the product leaves the match set rather than scoring
badly — and section 8 forbids turning unknown into a neutral score.

The window itself is not fixed anywhere in the specification, so it is
configuration with a documented default, raised in docs/PHASE_8_NOTES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.db.types import utcnow
from app.products.models import ProductFact, ProductVersion
from app.products.provenance import SYNTHETIC

#: How long a manually verified fact stays usable before it must be
#: re-checked. Deliberately short: insurance terms change, and a claim that
#: something was verified a year ago is not the same as it being true today.
DEFAULT_MAX_VERIFICATION_AGE = timedelta(days=180)


@dataclass(frozen=True)
class UsabilityResult:
    usable: bool
    reason: str | None = None


def version_usable(
    version: ProductVersion,
    *,
    now: datetime | None = None,
    max_verification_age: timedelta = DEFAULT_MAX_VERIFICATION_AGE,
) -> UsabilityResult:
    """Whether a product version may be offered to a user at all."""
    moment = now or utcnow()

    if not version.active:
        return UsabilityResult(False, "INACTIVE")
    if version.effective_from is not None and version.effective_from > moment:
        return UsabilityResult(False, "NOT_YET_EFFECTIVE")
    if version.effective_to is not None and version.effective_to <= moment:
        return UsabilityResult(False, "SUPERSEDED")

    # Synthetic data is not "verified", so verification age says nothing about
    # it. It is excluded from real matching by its source type instead.
    if version.source_type != SYNTHETIC and version.verified_at + max_verification_age <= moment:
        return UsabilityResult(False, "VERIFICATION_STALE")

    return UsabilityResult(True)


def critical_facts_usable(
    facts: list[ProductFact],
    *,
    required_keys: set[str],
    now: datetime | None = None,
    max_verification_age: timedelta = DEFAULT_MAX_VERIFICATION_AGE,
) -> UsabilityResult:
    """Whether every fact the engine must have is present and fresh.

    A missing critical fact is not a low score — it is a reason not to offer
    the product, because the alternative is presenting a match built on data
    we do not have.
    """
    moment = now or utcnow()
    by_key = {fact.fact_key: fact for fact in facts}

    missing = sorted(required_keys - set(by_key))
    if missing:
        return UsabilityResult(False, "CRITICAL_FACT_MISSING")

    for key in required_keys:
        fact = by_key[key]
        if fact.verified_at + max_verification_age <= moment:
            return UsabilityResult(False, "CRITICAL_FACT_STALE")

    return UsabilityResult(True)
