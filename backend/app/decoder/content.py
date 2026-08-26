"""What each extracted fact means, in plain language.

`docs/07_POLICY_DECODER_AI.md` section 6 fixes the shape of every fact card:

    Plain language title
    What it means: ...
    Example: ...
    Important conditions: ...
    Technical term: ...
    Source: Page X · Clause Y

and one rule that shapes all of it — *explain technical language without
hiding the technical term*. A reader who learns what "co-payment" means is
better off than one shown a friendlier word they will never see again on their
insurer's website.

## Why this is authored, not generated

This is the **explanation layer** (section 3), and section 3's rule is that it
must never become the source of truth. Authored templates make that structural:
they are written once, reviewed once, and cannot vary between readers or drift
between runs. Nothing here is stored against a policy — it is composed at
render time from the fact and its clause, so an explanation can never outlive
or contradict the fact it explains.

The value in each sentence comes from the extracted fact. The wording around
it does not depend on the document at all, which is exactly why it is safe.

## Examples

Every example is a labelled hypothetical about policies in general, never a
statement about this policy — the same rule the product detail screen follows.
An example that used this policy's own numbers would become an unverified
claim about what the reader will be paid.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.extraction.facts import (
    FACT_COPAY_PERCENT,
    FACT_INITIAL_WAITING_DAYS,
    FACT_PED_WAITING_MONTHS,
    FACT_ROOM_RENT_PERCENT,
    FACT_SPECIFIC_WAITING_MONTHS,
    FACT_SUM_INSURED_INR,
)

#: The decoder's sections, verbatim from docs/01_PRODUCT_SPEC.md section 3.4.
SECTION_YOUR_COVER = "your-cover"
SECTION_YOUR_COSTS = "your-costs"
SECTION_BEFORE_COVER_STARTS = "before-cover-starts"
SECTION_IMPORTANT_LIMITS = "important-limits"
SECTION_NOT_COVERED = "not-covered"
SECTION_AT_CLAIM_TIME = "at-claim-time"
SECTION_POLICY_DETAILS = "policy-details"

SECTION_ORDER: tuple[tuple[str, str], ...] = (
    (SECTION_YOUR_COVER, "Your Cover"),
    (SECTION_YOUR_COSTS, "Your Costs"),
    (SECTION_BEFORE_COVER_STARTS, "Before Cover Starts"),
    (SECTION_IMPORTANT_LIMITS, "Important Limits"),
    (SECTION_NOT_COVERED, "Not Covered"),
    (SECTION_AT_CLAIM_TIME, "At Claim Time"),
    (SECTION_POLICY_DETAILS, "Policy Details"),
)


@dataclass(frozen=True)
class FactContent:
    """The authored half of a fact card."""

    section: str
    #: Plain-language title. What the reader is actually looking for.
    title: str
    #: The technical term, kept rather than replaced.
    technical_term: str
    #: A hypothetical about policies in general. Never about this policy.
    example: str
    #: What the reader should still check for themselves. Always present:
    #: a card with nothing to watch for encourages more trust than an
    #: extracted number deserves.
    conditions: str


CONTENT: dict[str, FactContent] = {
    FACT_SUM_INSURED_INR: FactContent(
        section=SECTION_YOUR_COVER,
        title="How much this policy will pay",
        technical_term="Sum insured",
        example=(
            "If a policy has ₹5 lakh of cover and a hospital stay comes to ₹7 lakh, the policy "
            "pays up to ₹5 lakh and the remaining ₹2 lakh is yours to pay."
        ),
        conditions=(
            "This is the total for a policy year, and on a family policy it is usually shared "
            "between everyone covered unless your schedule says otherwise."
        ),
    ),
    FACT_COPAY_PERCENT: FactContent(
        section=SECTION_YOUR_COSTS,
        title="The share of each claim you pay",
        technical_term="Co-payment",
        example=(
            "If a policy has a 10% co-payment and a bill comes to ₹1 lakh, you pay ₹10,000 and "
            "the insurer pays the rest — on every claim, not just the first."
        ),
        conditions=(
            "Some policies apply a co-payment only above a certain age, or only for certain "
            "treatments. Check whether yours applies to every claim."
        ),
    ),
    FACT_ROOM_RENT_PERCENT: FactContent(
        section=SECTION_IMPORTANT_LIMITS,
        title="What the policy pays towards your hospital room",
        technical_term="Room rent limit",
        example=(
            "If a policy caps room rent at 1% of ₹5 lakh, that is ₹5,000 a day. Choosing a "
            "₹10,000 room can mean the insurer scales down what it pays on the whole bill, not "
            "just the room — so a ₹2 lakh bill might be settled at around ₹1 lakh."
        ),
        conditions=(
            "This is one of the most expensive limits to discover at the hospital. Ask your "
            "insurer what happens to the rest of the bill if you exceed the room cap."
        ),
    ),
    FACT_PED_WAITING_MONTHS: FactContent(
        section=SECTION_BEFORE_COVER_STARTS,
        title="How long before existing conditions are covered",
        technical_term="Pre-existing disease waiting period",
        example=(
            "If a policy waits 36 months before covering an existing condition, a claim for that "
            "condition in year 2 would not be paid, even though the policy is active and the "
            "premiums are up to date."
        ),
        conditions=(
            "This usually requires continuous cover — a lapse can restart the clock. What counts "
            "as pre-existing is defined in the policy and is worth reading."
        ),
    ),
    FACT_INITIAL_WAITING_DAYS: FactContent(
        section=SECTION_BEFORE_COVER_STARTS,
        title="The wait before the policy pays anything",
        technical_term="Initial waiting period",
        example=(
            "With a 30-day initial waiting period, illness treatment in the first month is not "
            "covered. Accidents are normally the exception and are covered from day one."
        ),
        conditions=(
            "Check whether accidents are excluded from this wait in your policy — most policies "
            "exclude them, but not all."
        ),
    ),
    FACT_SPECIFIC_WAITING_MONTHS: FactContent(
        section=SECTION_BEFORE_COVER_STARTS,
        title="How long before certain named treatments are covered",
        technical_term="Specific disease waiting period",
        example=(
            "A policy might wait 24 months before covering cataract surgery or a hernia repair, "
            "even for someone with no history of either."
        ),
        conditions=(
            "The list of named treatments is in the policy wording. It usually includes common "
            "planned procedures, so it is worth checking against anything you expect to need."
        ),
    ),
}


def describe_value(fact_key: str, value: dict[str, Any] | None) -> str | None:
    """The extracted value as a sentence.

    Returns None when there is no value — the card then shows its unknown
    state rather than a sentence built around a blank.
    """
    if value is None:
        return None

    if fact_key == FACT_SUM_INSURED_INR:
        amount = value.get("amount")
        if not isinstance(amount, int):
            return None
        return f"This policy covers up to {_rupees(amount)}."

    if fact_key == FACT_COPAY_PERCENT:
        percent = value.get("percent")
        if percent == 0:
            return "You pay no share of a claim: the policy pays the full covered amount."
        return f"You pay {_number(percent)}% of each claim, and the policy pays the rest."

    if fact_key == FACT_ROOM_RENT_PERCENT:
        return (
            f"Room charges are covered up to {_number(value.get('percent'))}% of the cover "
            "amount per day."
        )

    if fact_key in (FACT_PED_WAITING_MONTHS, FACT_SPECIFIC_WAITING_MONTHS):
        months = value.get("months")
        if not isinstance(months, int):
            return None
        return f"You would wait {_months(months)} from the start of the policy."

    if fact_key == FACT_INITIAL_WAITING_DAYS:
        days = value.get("days")
        if not isinstance(days, int):
            return None
        return f"Nothing is covered for the first {days} days, other than accidents."

    return None


def _rupees(amount: int) -> str:
    if amount >= 10_000_000:
        return f"₹{amount / 10_000_000:g} crore"
    return f"₹{amount / 100_000:g} lakh"


def _number(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _months(months: int) -> str:
    if months % 12 == 0 and months >= 12:
        years = months // 12
        return f"{years} year{'s' if years > 1 else ''} ({months} months)"
    return f"{months} months"
