"""Structured health product facts.

Phase 5 gave every demo product a hand-written fit label — "co-pay: STRONG".
That was authored copy for a UX review, not something the system worked out,
and an engine that reads labels is not an engine.

Phase 9 replaces those labels with the *facts* a label would have to be
derived from: what the co-pay actually is, how long the wait for existing
conditions actually runs, whether room charges are capped. The evaluators in
`app.matching` turn those facts into labels against a specific person's
answers, which is the only way a label like "strong" can mean anything —
a 10% co-pay is a trade-off for someone who said they would rather not pay a
share, and unremarkable for someone who said a small share is fine.

Two properties matter more than the schema itself:

* **`None` means "not recorded", never "zero" and never "average".**
  docs/06_RECOMMENDATION_ENGINE.md section 8 forbids silently converting
  unknown into a neutral score. Every optional field here is a field an
  evaluator will report as UNVERIFIED rather than guess at.
* **The same shape carries synthetic and verified facts.** These are parsed
  out of a provider's `facts` dict, so a demo product and a manually verified
  product version reach the engine through one code path (Phase 8's
  `ProviderProduct`). The engine cannot tell them apart, and does not need
  to — provenance travels alongside and decides what may be shown.

There is deliberately no premium field. CLAUDE.md is unconditional on that,
and price lives in `app.pricing` as a state with a source and a timestamp.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

#: How a policy treats hospital room charges.
RoomRule = Literal["ANY_ROOM", "SINGLE_PRIVATE", "CAPPED_PERCENT", "CAPPED_AMOUNT"]

#: Where cashless treatment works.
CashlessScope = Literal["ANY_HOSPITAL", "NETWORK_ONLY"]

#: Who a policy can be taken out for. Matches the questionnaire's `cover_for`
#: answers, so eligibility is a set membership test rather than a translation
#: table nobody maintains.
Composition = Literal["just_me", "me_spouse", "me_family", "my_parents"]


class HealthFacts(BaseModel):
    """The facts the health engine can evaluate.

    Required fields are the ones without which the product cannot honestly be
    offered at all — see `CRITICAL_FACT_KEYS`. Everything else is optional,
    and its absence is reported, not filled in.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    # -- Eligibility. Missing any of these excludes the product. -------------
    entry_age_min: int = Field(ge=0, le=120)
    entry_age_max: int = Field(ge=0, le=120)
    supported_compositions: tuple[Composition, ...] = Field(min_length=1)
    #: Rupees. The options a buyer can choose between.
    sum_insured_options_inr: tuple[int, ...] = Field(min_length=1)

    # -- Cover ---------------------------------------------------------------
    max_children: int | None = Field(default=None, ge=0)
    restoration: bool | None = None

    # -- What you pay on a claim --------------------------------------------
    #: Share of each claim the policyholder pays, as a percentage.
    copay_percent: int | None = Field(default=None, ge=0, le=100)
    #: Some policies only apply the co-pay above a given age.
    copay_applies_above_age: int | None = Field(default=None, ge=0, le=120)
    deductible_inr: int | None = Field(default=None, ge=0)

    # -- Waiting periods -----------------------------------------------------
    #: Months before a pre-existing condition is covered.
    ped_waiting_months: int | None = Field(default=None, ge=0, le=120)
    specific_treatment_waiting_months: int | None = Field(default=None, ge=0, le=120)
    initial_waiting_days: int | None = Field(default=None, ge=0, le=365)

    # -- Hospital and room ---------------------------------------------------
    room_rule: RoomRule | None = None
    #: Only meaningful when `room_rule` is CAPPED_PERCENT.
    room_cap_percent: int | None = Field(default=None, ge=0, le=100)
    cashless_scope: CashlessScope | None = None
    #: A national count. It says nothing about any particular pincode, and the
    #: evaluator's evidence says so out loud.
    network_hospital_count: int | None = Field(default=None, ge=0)

    # -- Limits and exclusions ----------------------------------------------
    sublimit_count: int | None = Field(default=None, ge=0)
    sublimit_treatments: tuple[str, ...] = ()
    notable_exclusion_count: int | None = Field(default=None, ge=0)

    @property
    def max_sum_insured_inr(self) -> int:
        return max(self.sum_insured_options_inr)

    @property
    def min_sum_insured_inr(self) -> int:
        return min(self.sum_insured_options_inr)


#: The facts a product cannot be matched without.
#:
#: docs/06_RECOMMENDATION_ENGINE.md section 4 makes "critical matching data
#: unavailable" a hard failure. These four decide whether the product applies
#: to this person at all; without them any match would be a guess about
#: eligibility, which is worse than showing nothing.
CRITICAL_FACT_KEYS: frozenset[str] = frozenset(
    {
        "entry_age_min",
        "entry_age_max",
        "supported_compositions",
        "sum_insured_options_inr",
    }
)


class FactsUnusableError(ValueError):
    """The recorded facts cannot be read as a health product."""


def parse_health_facts(raw: dict[str, Any]) -> HealthFacts:
    """Read a provider's fact dict into the typed shape.

    Raises rather than returning a partially populated object: a product whose
    eligibility facts do not parse is excluded upstream, and quietly dropping
    the unreadable fields would turn a data problem into a wrong match.
    """
    try:
        return HealthFacts.model_validate(raw)
    except ValidationError as exc:
        raise FactsUnusableError(str(exc)) from exc
