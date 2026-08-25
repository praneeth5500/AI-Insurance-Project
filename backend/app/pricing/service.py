"""Deciding whether a price may be shown, and how.

docs/12_BETA_CHECKLIST.md turns four separate rules into one question: *is
this price safe to put on a screen?*

* every displayed premium has a state, a source and a timestamp;
* an indicative price is never described as final;
* no invented range;
* no misleading "from ₹X" on a personalised result.

The answer is computed here rather than in a template, so a screen cannot
accidentally render a price the rules forbid.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.db.types import utcnow
from app.pricing.models import STATUS_FINAL, STATUS_INDICATIVE, STATUS_QUOTED, ProductPrice

#: Wording for each state. An indicative figure is never called a premium
#: without the qualifier that makes it honest.
STATE_LABELS: dict[str, str] = {
    STATUS_INDICATIVE: "Indicative premium",
    STATUS_QUOTED: "Quoted premium",
    STATUS_FINAL: "Confirmed premium",
}

STATE_EXPLANATIONS: dict[str, str] = {
    STATUS_INDICATIVE: (
        "An estimate from before underwriting. The amount you are actually offered can differ."
    ),
    STATUS_QUOTED: "A formal quote from the insurer, valid for a limited time.",
    STATUS_FINAL: "The confirmed amount for issuing this policy.",
}

#: How long an indicative figure stays showable. Not fixed by the
#: specification — see docs/PHASE_8_NOTES.md.
DEFAULT_INDICATIVE_MAX_AGE = timedelta(days=30)


@dataclass(frozen=True)
class DisplayablePrice:
    """A price that has passed every rule, with the context it must carry."""

    status: str
    label: str
    explanation: str
    amount_minor: int
    currency: str
    billing_period: str
    generated_at_iso: str
    source_type: str
    source_name: str
    taxes_included: bool | None
    fees_included: bool | None
    valid_until_iso: str | None
    assumptions: dict[str, object] | None


@dataclass(frozen=True)
class SuppressedPrice:
    """No price may be shown, and why — never silently blank."""

    reason: str
    explanation: str


NO_PRICE = SuppressedPrice(
    reason="NO_PRICE_RECORDED",
    explanation=(
        "No price has been recorded for this option. Prices come from the insurer, never from us."
    ),
)


def evaluate(
    price: ProductPrice | None, *, indicative_max_age: timedelta = DEFAULT_INDICATIVE_MAX_AGE
) -> DisplayablePrice | SuppressedPrice:
    """Decide whether this price may be displayed."""
    if price is None:
        return NO_PRICE

    now = utcnow()

    if price.status not in STATE_LABELS:
        # An unrecognised state is never guessed at.
        return SuppressedPrice(
            reason="UNKNOWN_PRICE_STATE",
            explanation="We can't confirm what this price represents, so we're not showing it.",
        )

    if price.valid_until is not None and price.valid_until <= now:
        return SuppressedPrice(
            reason="EXPIRED",
            explanation=("This quote has expired. A current price has to come from the insurer."),
        )

    if price.status == STATUS_INDICATIVE and price.generated_at + indicative_max_age <= now:
        # An old estimate is worse than no estimate: it looks current.
        return SuppressedPrice(
            reason="STALE",
            explanation=("This estimate is too old to be useful, so we're not showing it."),
        )

    return DisplayablePrice(
        status=price.status,
        label=STATE_LABELS[price.status],
        explanation=STATE_EXPLANATIONS[price.status],
        amount_minor=price.amount,
        currency=price.currency,
        billing_period=price.billing_period,
        generated_at_iso=price.generated_at.isoformat(),
        source_type=price.source_type,
        source_name=price.source_name,
        taxes_included=price.taxes_included,
        fees_included=price.fees_included,
        valid_until_iso=price.valid_until.isoformat() if price.valid_until else None,
        assumptions=dict(price.assumptions_json) if price.assumptions_json else None,
    )
