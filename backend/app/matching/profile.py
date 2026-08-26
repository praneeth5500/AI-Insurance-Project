"""The reader, as the engine sees them.

A typed view over the questionnaire answers, so an evaluator reads
`profile.copay_tolerance` rather than digging a string out of a dict and
hoping. Everything is optional except the answers the questionnaire marks
required, because an unanswered question is a real state — and one the
evaluators are expected to report rather than fill in.

Nothing here is inferred. If the reader did not say it, the field is None and
the dimension that needed it says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: docs/01_PRODUCT_SPEC.md section 2.3: the cover bands, in rupees.
#: `None` for "I'm not sure yet" — a target we do not have, not a target of 0.
DESIRED_COVER_TARGETS_INR: dict[str, int | None] = {
    "up_to_5l": 500_000,
    "5l_to_10l": 1_000_000,
    "10l_to_25l": 2_500_000,
    "above_25l": 2_500_001,
    "not_sure": None,
}


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


@dataclass(frozen=True)
class UserProfile:
    applicant_age: int | None = None
    spouse_age: int | None = None
    oldest_parent_age: int | None = None
    children_count: int | None = None
    cover_for: str | None = None
    #: "yes" / "no" / "prefer_not_to_say". Optional and sensitive: the
    #: questionnaire never asks what the condition is.
    broad_health_conditions: str | None = None
    desired_cover: str | None = None
    approximate_budget_inr: int | None = None
    room_preference: str | None = None
    copay_tolerance: str | None = None
    waiting_period_sensitivity: str | None = None
    priorities: list[str] = field(default_factory=list)

    @property
    def oldest_person_age(self) -> int | None:
        """The age eligibility actually turns on.

        A policy's entry age has to admit everyone on it, so the oldest person
        on the policy decides — and only the people who are actually on it. A
        reader buying cover for their parents is not covered themselves, so
        their own age must not exclude a senior product; children are not
        aged-checked here because no product in the fixture set gates on them
        and inventing a rule would be worse than omitting one.
        """
        covered: tuple[int | None, ...]
        if self.cover_for == "my_parents":
            covered = (self.oldest_parent_age,)
        elif self.cover_for == "just_me":
            covered = (self.applicant_age,)
        elif self.cover_for in ("me_spouse", "me_family"):
            covered = (self.applicant_age, self.spouse_age)
        else:
            # No answer yet: fall back to everyone we know about, which is the
            # conservative reading.
            covered = (self.applicant_age, self.spouse_age, self.oldest_parent_age)

        ages = [age for age in covered if age is not None]
        return max(ages) if ages else None

    @property
    def desired_cover_target_inr(self) -> int | None:
        if self.desired_cover is None:
            return None
        return DESIRED_COVER_TARGETS_INR.get(self.desired_cover)

    @property
    def has_existing_condition(self) -> bool:
        """Only a plain yes counts.

        "I'd rather not say" is not a no. It leaves the waiting-period
        evaluator with less to go on, and the evidence records that.
        """
        return self.broad_health_conditions == "yes"


def build_profile(answers: dict[str, Any]) -> UserProfile:
    """Read the stored questionnaire answers into the typed view."""
    chosen = answers.get("priorities")
    priorities = (
        [item for item in chosen if isinstance(item, str)] if isinstance(chosen, list) else []
    )

    return UserProfile(
        applicant_age=_as_int(answers.get("applicant_age")),
        spouse_age=_as_int(answers.get("spouse_age")),
        oldest_parent_age=_as_int(answers.get("oldest_parent_age")),
        children_count=_as_int(answers.get("children_count")),
        cover_for=_as_str(answers.get("cover_for")),
        broad_health_conditions=_as_str(answers.get("broad_health_conditions")),
        desired_cover=_as_str(answers.get("desired_cover")),
        approximate_budget_inr=_as_int(answers.get("approximate_budget")),
        room_preference=_as_str(answers.get("room_preference")),
        copay_tolerance=_as_str(answers.get("copay_tolerance")),
        waiting_period_sensitivity=_as_str(answers.get("waiting_period_sensitivity")),
        priorities=priorities,
    )
