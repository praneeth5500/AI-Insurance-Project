"""Hard eligibility.

docs/06_RECOMMENDATION_ENGINE.md section 4 draws the line this module exists
to hold:

* a **hard failure** removes the product — the reader cannot buy it, so
  showing it as a match would waste their time and mislead them;
* a **preference mismatch** does not remove anything. A higher co-pay than
  someone wanted is a trade-off to explain, not a disqualification, and it is
  handled by the evaluators instead.

Stale or missing critical data is a hard failure too, not a low score. The
alternative is presenting a match built on data we do not have.

Every exclusion carries a reason and its evidence, so a run can always answer
"why wasn't this shown to me?".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.matching.evidence import Evidence, product_fact, rule, user_answer
from app.matching.profile import UserProfile
from app.products.facts import HealthFacts

EligibilityStatus = Literal["ELIGIBLE", "EXCLUDED"]

#: Why a product was not offered. These are internal codes; the reader sees
#: the grouped, plain-language wording in `EXCLUSION_REASON_LABELS`.
AGE_OUTSIDE_RANGE = "AGE_OUTSIDE_RANGE"
COMPOSITION_UNSUPPORTED = "COMPOSITION_UNSUPPORTED"
CHILDREN_EXCEEDED = "CHILDREN_EXCEEDED"
PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
CRITICAL_DATA_UNUSABLE = "CRITICAL_DATA_UNUSABLE"
NO_VERIFIED_FIT_DATA = "NO_VERIFIED_FIT_DATA"

#: What the reader is told, per reason. Deliberately non-judgemental and
#: non-specific about the product: an excluded option is not shown, so the
#: wording explains the *rule*, not the policy.
EXCLUSION_REASON_LABELS: dict[str, str] = {
    AGE_OUTSIDE_RANGE: "the age of someone to be covered is outside what the policy accepts",
    COMPOSITION_UNSUPPORTED: "the policy cannot be taken out for the people you want to cover",
    CHILDREN_EXCEEDED: "the policy covers fewer children than you asked for",
    PRODUCT_INACTIVE: "the policy is no longer on sale",
    CRITICAL_DATA_UNUSABLE: "we do not hold current enough verified data to match it properly",
    NO_VERIFIED_FIT_DATA: "we hold no verified detail to compare it on",
}


@dataclass(frozen=True)
class EligibilityResult:
    status: EligibilityStatus
    #: Empty when eligible. More than one reason can apply at once, and all of
    #: them are kept: fixing one would not make the product available.
    reasons: tuple[str, ...]
    evidence: tuple[Evidence, ...]

    @property
    def eligible(self) -> bool:
        return self.status == "ELIGIBLE"


def assess(facts: HealthFacts, profile: UserProfile) -> EligibilityResult:
    """Decide whether this product can be offered to this person at all."""
    reasons: list[str] = []
    evidence: list[Evidence] = []

    age = profile.oldest_person_age
    if age is not None:
        evidence.append(
            product_fact(
                "entry_age_range",
                f"{facts.entry_age_min}-{facts.entry_age_max}",
                f"Accepts applicants aged {facts.entry_age_min} to {facts.entry_age_max}.",
            )
        )
        evidence.append(
            user_answer("oldest_person_age", age, f"The oldest person to be covered is {age}.")
        )
        if age < facts.entry_age_min or age > facts.entry_age_max:
            reasons.append(AGE_OUTSIDE_RANGE)
            evidence.append(
                rule(
                    "entry_age",
                    "Everyone on the policy has to be within the entry age range, "
                    "so the oldest person decides.",
                )
            )

    if profile.cover_for is not None:
        evidence.append(
            user_answer(
                "cover_for",
                profile.cover_for,
                "Who the reader wants to cover.",
            )
        )
        if profile.cover_for not in facts.supported_compositions:
            reasons.append(COMPOSITION_UNSUPPORTED)
            evidence.append(
                product_fact(
                    "supported_compositions",
                    ", ".join(facts.supported_compositions),
                    "Who this policy can be taken out for.",
                )
            )

    if (
        profile.children_count is not None
        and facts.max_children is not None
        and profile.children_count > facts.max_children
    ):
        reasons.append(CHILDREN_EXCEEDED)
        evidence.append(
            product_fact(
                "max_children",
                facts.max_children,
                f"Covers at most {facts.max_children} children.",
            )
        )
        evidence.append(
            user_answer(
                "children_count",
                profile.children_count,
                f"{profile.children_count} children to cover.",
            )
        )

    return EligibilityResult(
        status="EXCLUDED" if reasons else "ELIGIBLE",
        reasons=tuple(reasons),
        evidence=tuple(evidence),
    )
