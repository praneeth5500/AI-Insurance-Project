"""'What we learned about you'.

docs/01_PRODUCT_SPEC.md section 2.5: "A synthesis, not a raw form dump."

Built deterministically from the structured answers. No LLM is involved:
docs/11_BUILD_PLAN.md Phase 9 says AI explanation comes only after the
structured output is correct, and a synthesis that could hallucinate a detail
about someone's own answers would be worse than no synthesis at all.

Every line is derived from an answer the user actually gave. Nothing is
inferred, and a missing answer produces no line rather than a guess.
"""

from __future__ import annotations

from typing import Any

from app.matching.factors import FACTOR_LABELS, PRIORITY_TO_FACTOR

COVER_FOR_PHRASES: dict[str, str] = {
    "just_me": "cover for yourself",
    "me_spouse": "cover for you and your spouse",
    "me_family": "cover for you and your family",
    "my_parents": "cover for your parents",
}

PRIORITY_PHRASES: dict[str, str] = {
    "lower_premium": "keeping the premium down",
    "low_copay": "not paying a share of each claim",
    "short_waiting_periods": "short waiting periods",
    "hospital_flexibility": "flexibility about which hospital you use",
    "broad_coverage": "broad coverage",
    "fewer_sublimits": "fewer separate treatment limits",
}


def _sentence_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def build_decision_profile(answers: dict[str, Any]) -> list[str]:
    """Short statements summarising what the person told us.

    Returned as separate lines rather than a paragraph so the UI can render
    them as a list and a reader can check each one against what they answered.
    """
    lines: list[str] = []

    cover_for = answers.get("cover_for")
    if isinstance(cover_for, str) and cover_for in COVER_FOR_PHRASES:
        age = answers.get("applicant_age")
        phrase = COVER_FOR_PHRASES[cover_for]
        lines.append(
            f"You're looking for {phrase}, and you're {age}."
            if isinstance(age, int)
            else f"You're looking for {phrase}."
        )

    if answers.get("has_employer_cover") == "yes":
        lines.append(
            "You already have cover through an employer, which usually ends when the job does."
        )
    elif answers.get("has_employer_cover") == "no":
        lines.append("You don't have cover through an employer.")

    if answers.get("has_personal_cover") is True:
        lines.append("You already have a policy of your own.")

    if answers.get("broad_health_conditions") == "yes":
        # Stated back only as the user framed it. No condition, no diagnosis.
        lines.append(
            "Someone to be covered has an ongoing condition, so waiting periods matter more here."
        )

    if answers.get("waiting_period_sensitivity") == "as_soon_as_possible":
        lines.append("You'd like cover to start fully as soon as possible.")

    if answers.get("copay_tolerance") == "prefer_none":
        lines.append("You'd rather not pay a share of each claim.")

    if answers.get("room_preference") == "private_room":
        lines.append("You'd want a private hospital room, which room limits can affect.")

    priorities = answers.get("priorities")
    if isinstance(priorities, list) and priorities:
        phrases = [PRIORITY_PHRASES[p] for p in priorities if p in PRIORITY_PHRASES]
        if phrases:
            lines.append(f"What matters most to you: {_sentence_list(phrases)}.")

    return lines


def priority_factor_labels(priorities: list[str]) -> list[str]:
    """Human labels for the fit dimensions the user's priorities point at."""
    return [
        FACTOR_LABELS[factor]
        for priority in priorities
        if (factor := PRIORITY_TO_FACTOR.get(priority)) is not None and factor in FACTOR_LABELS
    ]
