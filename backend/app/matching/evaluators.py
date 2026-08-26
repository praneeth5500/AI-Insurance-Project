"""Fit evaluators.

One function per dimension. Each takes the product's facts and the reader's
answers and returns a `FitResult`: a label, an internal 0..1 score, and the
evidence that produced both.

Three rules hold across every evaluator, and the tests check all three:

1. **Unknown is never average.** A missing fact returns `UNVERIFIED` with a
   `DATA_GAP` evidence entry and `normalized_score=None`, which drops the
   dimension out of the weighting entirely rather than scoring it 0.5
   (docs/06_RECOMMENDATION_ENGINE.md section 8).
2. **Fit is relative to the reader.** A 10% co-pay is a trade-off for someone
   who said they would rather not pay a share and unremarkable for someone who
   said a small share is fine. The same product legitimately gets different
   labels for different people, which is the whole point.
3. **The thresholds are visible.** Every band is a named constant in this
   file with the rule recorded as evidence. They are product-test parameters,
   not insurance truth — docs/06_RECOMMENDATION_ENGINE.md section 6 — and
   they are versioned by `SCORING_VERSION`.

No LLM participates. CLAUDE.md: the model never generates the ranking.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.matching import factors
from app.matching.evidence import Evidence, data_gap, product_fact, rule, user_answer
from app.matching.factors import FitLabel
from app.matching.profile import UserProfile
from app.products.facts import HealthFacts


@dataclass(frozen=True)
class FitResult:
    """docs/06_RECOMMENDATION_ENGINE.md section 7."""

    factor_key: str
    label: FitLabel
    #: 0..1, internal only. Never serialised to a client
    #: (docs/01_PRODUCT_SPEC.md section 2.5 forbids a consumer score).
    normalized_score: float | None
    #: The one-line explanation shown under "Why this matches you".
    note: str
    evidence: tuple[Evidence, ...]

    @property
    def has_data(self) -> bool:
        return self.normalized_score is not None


def _unverified(factor_key: str, key: str, note: str) -> FitResult:
    """The honest outcome when a fact was never recorded."""
    return FitResult(
        factor_key=factor_key,
        label="UNVERIFIED",
        normalized_score=None,
        note=note,
        evidence=(data_gap(key, note),),
    )


# --------------------------------------------------------------- coverage --


def evaluate_coverage(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """Does the cover on offer reach what the reader said they wanted?

    Adequacy needs a target. Someone who answered "I'm not sure yet" has not
    given one, so this reports a gap rather than inventing a level of cover
    that would be right for them.
    """
    target = profile.desired_cover_target_inr
    if target is None:
        return _unverified(
            factors.COVERAGE,
            "desired_cover",
            "You haven't said how much cover you're aiming for, so there's nothing to "
            "measure this against yet.",
        )

    available = facts.max_sum_insured_inr
    evidence = [
        product_fact(
            "sum_insured_options_inr",
            available,
            f"Highest cover available is ₹{available // 100_000} lakh.",
        ),
        user_answer("desired_cover", profile.desired_cover, "The cover level you're aiming for."),
        rule("coverage_band", "Compares the highest cover on offer against your target."),
    ]

    ratio = available / target
    if ratio >= 2.0:
        return FitResult(
            factors.COVERAGE,
            "STRONG",
            1.0,
            "Offers well above the cover you're aiming for.",
            tuple(evidence),
        )
    if ratio >= 1.0:
        return FitResult(
            factors.COVERAGE,
            "GOOD",
            0.8,
            "Reaches the cover you're aiming for.",
            tuple(evidence),
        )
    if ratio >= 0.6:
        return FitResult(
            factors.COVERAGE,
            "TRADE_OFF",
            0.4,
            "Tops out below the cover you're aiming for.",
            tuple(evidence),
        )
    return FitResult(
        factors.COVERAGE,
        "NEEDS_ATTENTION",
        0.1,
        "The most cover available here is well below what you're aiming for.",
        tuple(evidence),
    )


# ------------------------------------------------------------------ co-pay --

#: Co-pay bands, in percent.
COPAY_SMALL = 10
COPAY_LARGE = 20


def evaluate_copay(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """What share of each claim the reader would pay, against what they'll accept."""
    if facts.copay_percent is None:
        return _unverified(
            factors.COPAY,
            "copay_percent",
            "We don't hold a verified co-pay figure for this option.",
        )

    percent = facts.copay_percent
    evidence: list[Evidence] = [
        product_fact("copay_percent", percent, f"Co-pay of {percent}% on each claim.")
    ]

    # Some policies only apply the co-pay above a given age. If the reader is
    # below it there is nothing to pay today — but it is still worth saying,
    # because it will apply later.
    applies_above = facts.copay_applies_above_age
    age = profile.applicant_age
    if applies_above is not None:
        evidence.append(
            product_fact(
                "copay_applies_above_age",
                applies_above,
                f"The co-pay applies from age {applies_above}.",
            )
        )
        if age is not None and age < applies_above:
            evidence.append(user_answer("applicant_age", age, f"You are {age}, below that age."))
            return FitResult(
                factors.COPAY,
                "GOOD",
                0.75,
                f"No co-pay at your age, but {percent}% starts applying from {applies_above}.",
                tuple(evidence),
            )

    if percent == 0:
        return FitResult(
            factors.COPAY,
            "STRONG",
            1.0,
            "No share of the bill is passed back to you on a standard claim.",
            tuple(evidence),
        )

    tolerance = profile.copay_tolerance
    if tolerance is not None:
        evidence.append(
            user_answer("copay_tolerance", tolerance, "What you said about sharing a claim.")
        )
    evidence.append(
        rule(
            "copay_band",
            f"Up to {COPAY_SMALL}% counts as a small share; "
            f"above {COPAY_LARGE}% is treated as substantial.",
        )
    )

    if tolerance == "prefer_none":
        if percent <= COPAY_SMALL:
            return FitResult(
                factors.COPAY,
                "TRADE_OFF",
                0.35,
                f"You'd rather not share a claim, and this one asks for {percent}%.",
                tuple(evidence),
            )
        return FitResult(
            factors.COPAY,
            "NEEDS_ATTENTION",
            0.1,
            f"You'd rather not share a claim, and this one asks for {percent}% of every one.",
            tuple(evidence),
        )

    if tolerance == "small_share_ok":
        if percent <= COPAY_SMALL:
            return FitResult(
                factors.COPAY,
                "GOOD",
                0.8,
                f"A {percent}% share of each claim, which is the small share you said was fine.",
                tuple(evidence),
            )
        if percent <= COPAY_LARGE:
            return FitResult(
                factors.COPAY,
                "TRADE_OFF",
                0.45,
                f"A {percent}% share of each claim — more than a small share.",
                tuple(evidence),
            )
        return FitResult(
            factors.COPAY,
            "NEEDS_ATTENTION",
            0.15,
            f"You pay {percent}% of every claim, well above a small share.",
            tuple(evidence),
        )

    # "I'm not sure", or unanswered. Judge the co-pay on its own size and say
    # plainly what it means, rather than assuming how they feel about it.
    if percent <= COPAY_SMALL:
        return FitResult(
            factors.COPAY,
            "GOOD",
            0.7,
            f"You would pay {percent}% of each claim.",
            tuple(evidence),
        )
    if percent <= COPAY_LARGE:
        return FitResult(
            factors.COPAY,
            "TRADE_OFF",
            0.4,
            f"You would pay {percent}% of each claim, which adds up on a large bill.",
            tuple(evidence),
        )
    return FitResult(
        factors.COPAY,
        "NEEDS_ATTENTION",
        0.15,
        f"You would pay {percent}% of every claim.",
        tuple(evidence),
    )


# --------------------------------------------------------- waiting periods --

#: Waiting-period bands for pre-existing conditions, in months.
WAIT_SHORT = 12
WAIT_TYPICAL = 24
WAIT_LONG = 36


def evaluate_waiting_periods(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """How long before existing conditions are covered, against how much that matters."""
    months = facts.ped_waiting_months
    if months is None:
        return _unverified(
            factors.WAITING_PERIODS,
            "ped_waiting_months",
            "We don't hold a verified waiting period for existing conditions here.",
        )

    evidence: list[Evidence] = [
        product_fact(
            "ped_waiting_months",
            months,
            f"Existing conditions are covered after {months} months.",
        )
    ]

    # Two things make the wait matter more: an existing condition to wait for,
    # and having said cover needs to start soon.
    urgent = profile.waiting_period_sensitivity == "as_soon_as_possible"
    relaxed = profile.waiting_period_sensitivity == "not_a_concern"
    if profile.waiting_period_sensitivity is not None:
        evidence.append(
            user_answer(
                "waiting_period_sensitivity",
                profile.waiting_period_sensitivity,
                "How soon you said you need cover to start fully.",
            )
        )
    if profile.has_existing_condition:
        evidence.append(
            user_answer(
                "broad_health_conditions",
                "yes",
                "Someone to be covered has an ongoing condition, so this wait applies to them.",
            )
        )
    elif profile.broad_health_conditions == "prefer_not_to_say":
        # Not a "no". The wait is judged as if it could apply.
        evidence.append(
            data_gap(
                "broad_health_conditions",
                "You chose not to say whether an existing condition applies, so this is "
                "judged as though it might.",
            )
        )

    stricter = urgent or profile.has_existing_condition
    evidence.append(
        rule(
            "waiting_band",
            f"Under {WAIT_SHORT} months is short and over {WAIT_LONG} is long; "
            "the bands tighten when a wait actually applies to you.",
        )
    )

    if relaxed and not profile.has_existing_condition:
        # They said it is not a concern and nothing is waiting on it.
        label: FitLabel = "GOOD" if months > WAIT_LONG else "STRONG"
        score = 0.75 if months > WAIT_LONG else 0.95
        return FitResult(
            factors.WAITING_PERIODS,
            label,
            score,
            f"Existing conditions wait {months} months, which you said isn't a concern.",
            tuple(evidence),
        )

    if months <= WAIT_SHORT:
        return FitResult(
            factors.WAITING_PERIODS,
            "STRONG",
            1.0,
            f"Among the shortest waits here — {months} months for existing conditions.",
            tuple(evidence),
        )
    if months <= WAIT_TYPICAL:
        return FitResult(
            factors.WAITING_PERIODS,
            "GOOD" if not stricter else "TRADE_OFF",
            0.75 if not stricter else 0.5,
            f"Existing conditions are covered after {months} months.",
            tuple(evidence),
        )
    if months <= WAIT_LONG:
        return FitResult(
            factors.WAITING_PERIODS,
            "TRADE_OFF",
            0.4 if not stricter else 0.3,
            f"A {months}-month wait before existing conditions are covered.",
            tuple(evidence),
        )
    return FitResult(
        factors.WAITING_PERIODS,
        "NEEDS_ATTENTION",
        0.15 if not stricter else 0.05,
        f"A long wait — {months} months before existing conditions are covered.",
        tuple(evidence),
    )


# --------------------------------------------------- hospital flexibility --


def evaluate_hospital_flexibility(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """Room rules, against the kind of room the reader said they'd want."""
    room_rule = facts.room_rule
    if room_rule is None:
        return _unverified(
            factors.HOSPITAL_FLEXIBILITY,
            "room_rule",
            "We don't hold verified room rules for this option.",
        )

    preference = profile.room_preference
    evidence: list[Evidence] = []
    if preference is not None:
        evidence.append(
            user_answer("room_preference", preference, "The kind of room you said you'd want.")
        )

    if room_rule == "ANY_ROOM":
        evidence.append(
            product_fact("room_rule", room_rule, "No cap on the room category you can use.")
        )
        return FitResult(
            factors.HOSPITAL_FLEXIBILITY,
            "STRONG",
            1.0,
            "No restriction on the room you choose.",
            tuple(evidence),
        )

    if room_rule == "SINGLE_PRIVATE":
        evidence.append(product_fact("room_rule", room_rule, "Covers up to a single private room."))
        if preference == "private_room":
            return FitResult(
                factors.HOSPITAL_FLEXIBILITY,
                "STRONG",
                0.95,
                "Covers a single private room, which is what you said you'd want.",
                tuple(evidence),
            )
        return FitResult(
            factors.HOSPITAL_FLEXIBILITY,
            "GOOD",
            0.85,
            "Covers up to a single private room.",
            tuple(evidence),
        )

    # Capped, by percentage or by amount.
    cap = facts.room_cap_percent
    detail = (
        f"Room charges are capped at {cap}% of the cover amount per day."
        if room_rule == "CAPPED_PERCENT" and cap is not None
        else "Room charges are capped."
    )
    evidence.append(product_fact("room_rule", room_rule, detail))
    evidence.append(
        rule(
            "room_cap",
            "A capped room rate can reduce what is paid on the whole bill, not just the room.",
        )
    )

    if preference == "private_room":
        return FitResult(
            factors.HOSPITAL_FLEXIBILITY,
            "NEEDS_ATTENTION",
            0.15,
            "You said you'd want a private room, and room charges here are capped — "
            "which can cut what's paid on the rest of the bill too.",
            tuple(evidence),
        )
    if preference == "shared_is_fine":
        return FitResult(
            factors.HOSPITAL_FLEXIBILITY,
            "GOOD",
            0.75,
            "Room charges are capped, which matters less given a shared room suits you.",
            tuple(evidence),
        )
    return FitResult(
        factors.HOSPITAL_FLEXIBILITY,
        "TRADE_OFF",
        0.45,
        "Room charges are capped, so a more expensive room reduces what is paid overall.",
        tuple(evidence),
    )


# ----------------------------------------------------------------- network --

#: Network size bands, in hospitals.
NETWORK_WIDE = 6000
NETWORK_MODERATE = 3000


def evaluate_network(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """Where cashless treatment works.

    The hospital count is a national figure. It is not checked against the
    reader's pincode, and the evidence says so rather than implying a local
    guarantee we cannot make.
    """
    scope = facts.cashless_scope
    if scope is None:
        return _unverified(
            factors.NETWORK,
            "cashless_scope",
            "We don't hold verified network detail for this option.",
        )

    evidence: list[Evidence] = [
        product_fact("cashless_scope", scope, "Where cashless treatment is available.")
    ]

    if scope == "ANY_HOSPITAL":
        return FitResult(
            factors.NETWORK,
            "STRONG",
            1.0,
            "Cashless treatment is not limited to a network of hospitals.",
            tuple(evidence),
        )

    count = facts.network_hospital_count
    if count is None:
        return _unverified(
            factors.NETWORK,
            "network_hospital_count",
            "Cashless treatment is network-only and we don't hold a verified network size.",
        )

    evidence.append(
        product_fact("network_hospital_count", count, f"Around {count:,} hospitals in the network.")
    )
    evidence.append(
        rule(
            "network_scope",
            "This is a national count. We have not checked it against your area.",
        )
    )

    if count >= NETWORK_WIDE:
        return FitResult(
            factors.NETWORK,
            "GOOD",
            0.8,
            f"Cashless treatment works across roughly {count:,} hospitals nationally.",
            tuple(evidence),
        )
    if count >= NETWORK_MODERATE:
        return FitResult(
            factors.NETWORK,
            "TRADE_OFF",
            0.45,
            f"A moderate network of around {count:,} hospitals, and cashless only works inside it.",
            tuple(evidence),
        )
    return FitResult(
        factors.NETWORK,
        "NEEDS_ATTENTION",
        0.15,
        f"A small network of around {count:,} hospitals, and cashless only works inside it.",
        tuple(evidence),
    )


# --------------------------------------------------------------- sublimits --


def evaluate_sublimits(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """Separate caps on individual treatments."""
    count = facts.sublimit_count
    if count is None:
        return _unverified(
            factors.SUBLIMITS,
            "sublimit_count",
            "We don't hold a verified list of treatment caps for this option.",
        )

    named = ", ".join(facts.sublimit_treatments)
    evidence: list[Evidence] = [
        product_fact(
            "sublimit_count",
            count,
            f"{count} treatments carry their own cap." if count else "No separate treatment caps.",
        )
    ]
    if named:
        evidence.append(
            product_fact("sublimit_treatments", named, f"Capped treatments include {named}.")
        )
    evidence.append(
        rule("sublimit_band", "Fewer separate caps means fewer surprises on a specific claim.")
    )

    if count == 0:
        return FitResult(
            factors.SUBLIMITS,
            "STRONG",
            1.0,
            "No separate caps on individual treatments.",
            tuple(evidence),
        )
    if count <= 2:
        return FitResult(
            factors.SUBLIMITS,
            "GOOD",
            0.75,
            f"Only {count} treatment{'s' if count > 1 else ''} carry their own cap.",
            tuple(evidence),
        )
    if count <= 4:
        return FitResult(
            factors.SUBLIMITS,
            "TRADE_OFF",
            0.4,
            f"{count} treatments have their own separate caps.",
            tuple(evidence),
        )
    return FitResult(
        factors.SUBLIMITS,
        "NEEDS_ATTENTION",
        0.15,
        f"{count} treatments carry their own caps, so a specific claim can be limited.",
        tuple(evidence),
    )


# -------------------------------------------------------------- exclusions --


def evaluate_exclusions(facts: HealthFacts, profile: UserProfile) -> FitResult:
    """How much is carved out of the cover."""
    count = facts.notable_exclusion_count
    if count is None:
        return _unverified(
            factors.EXCLUSIONS,
            "notable_exclusion_count",
            "We don't hold a verified exclusions list for this option.",
        )

    evidence = (
        product_fact("notable_exclusion_count", count, f"{count} notable exclusions are recorded."),
        rule(
            "exclusion_band", "Counts the exclusions worth a reader's attention, not every clause."
        ),
    )

    if count <= 3:
        return FitResult(
            factors.EXCLUSIONS,
            "STRONG",
            0.95,
            f"A short exclusions list — {count} worth knowing about.",
            evidence,
        )
    if count <= 5:
        return FitResult(
            factors.EXCLUSIONS,
            "GOOD",
            0.7,
            f"{count} exclusions worth reading before you buy.",
            evidence,
        )
    if count <= 7:
        return FitResult(
            factors.EXCLUSIONS,
            "TRADE_OFF",
            0.4,
            f"A longer exclusions list than most — {count} worth checking.",
            evidence,
        )
    return FitResult(
        factors.EXCLUSIONS,
        "NEEDS_ATTENTION",
        0.15,
        f"{count} notable exclusions, which is a lot to check against your own situation.",
        evidence,
    )


# ------------------------------------------------------------------ budget --


def evaluate_budget(
    facts: HealthFacts, profile: UserProfile, *, annual_premium_inr: int | None = None
) -> FitResult:
    """Where the price sits against the reader's budget.

    `annual_premium_inr` comes from a real, in-date price record and is
    `None` for every product today: the synthetic catalogue has no price, and
    no partner is integrated. That is not a gap to paper over — CLAUDE.md
    forbids inventing a premium outright — so this dimension reports it and
    drops out of the weighting.
    """
    if annual_premium_inr is None:
        return _unverified(
            factors.BUDGET,
            "annual_premium_inr",
            "No confirmed price is available for this option, so there is nothing to "
            "compare against your budget. Prices come from the insurer, never from us.",
        )

    budget = profile.approximate_budget_inr
    if budget is None or budget <= 0:
        return _unverified(
            factors.BUDGET,
            "approximate_budget",
            "You haven't given a budget, so there's nothing to measure the price against.",
        )

    evidence = (
        product_fact("annual_premium_inr", annual_premium_inr, "The price on record for a year."),
        user_answer("approximate_budget", budget, "What you said you'd like to spend a year."),
        rule("budget_band", "Compares the price on record against the budget you gave."),
    )

    ratio = annual_premium_inr / budget
    if ratio <= 0.8:
        return FitResult(factors.BUDGET, "STRONG", 1.0, "Comfortably inside your budget.", evidence)
    if ratio <= 1.0:
        return FitResult(factors.BUDGET, "GOOD", 0.8, "Within the budget you gave.", evidence)
    if ratio <= 1.25:
        return FitResult(
            factors.BUDGET, "TRADE_OFF", 0.4, "A little above the budget you gave.", evidence
        )
    return FitResult(
        factors.BUDGET,
        "NEEDS_ATTENTION",
        0.1,
        "Well above the budget you gave.",
        evidence,
    )


#: Every dimension, in the order a reader meets them.
EVALUATORS = (
    evaluate_coverage,
    evaluate_copay,
    evaluate_waiting_periods,
    evaluate_hospital_flexibility,
    evaluate_network,
    evaluate_sublimits,
    evaluate_exclusions,
)
