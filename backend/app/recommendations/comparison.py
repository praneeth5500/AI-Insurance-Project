"""Comparing up to three options.

docs/02_UX_UI_SPEC.md section 10 sets the order, and it is the whole design:

    Biggest differences  ->  Your priorities  ->  All details

That order exists because a comparison is only useful when it leads with what
actually separates the options. The same section says "Avoid giant feature
matrices", so everything after the differences is progressive disclosure
rather than a wall of cells.

Nothing here scores or ranks. It reports where authored fit labels differ and
by how much, which is a statement about the data, not a judgement about which
policy is better.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.matching.factors import FACTOR_LABELS, PRIORITY_TO_FACTOR

#: How far apart two fit labels are. Ordering only — never shown to a user,
#: and never combined into a total.
_LABEL_POSITION: dict[str, int] = {
    "STRONG": 4,
    "GOOD": 3,
    "TRADE_OFF": 2,
    "NEEDS_ATTENTION": 1,
    # Unknown is not a point on the scale, so a dimension where one option is
    # unverified is treated as a meaningful difference rather than a small one.
    "UNVERIFIED": 0,
}

#: How many dimensions lead the comparison. Enough to be useful, few enough
#: that the reader is not back in a matrix.
MAX_DIFFERENCES = 4


@dataclass(frozen=True)
class DimensionComparison:
    """One fit dimension across the selected options."""

    factor: str
    label: str
    #: product reference -> fit label
    values: dict[str, str]
    #: product reference -> the note explaining that label
    notes: dict[str, str]
    #: True when the options do not all share the same label here.
    differs: bool
    #: True when this dimension is one the user said mattered.
    is_priority: bool
    #: Internal only: how far apart the labels are. Never serialised.
    spread: int


def _spread(values: dict[str, str]) -> int:
    positions = [_LABEL_POSITION.get(label, 0) for label in values.values()]
    return max(positions) - min(positions) if positions else 0


def build_dimensions(
    fits_by_product: dict[str, dict[str, tuple[str, str]]],
    priorities: list[str],
) -> list[DimensionComparison]:
    """One entry per fit dimension, in the catalogue's own order."""
    priority_factors = {
        factor
        for priority in priorities
        if (factor := PRIORITY_TO_FACTOR.get(priority)) is not None
    }

    dimensions: list[DimensionComparison] = []
    for factor, label in FACTOR_LABELS.items():
        values: dict[str, str] = {}
        notes: dict[str, str] = {}
        for reference, fits in fits_by_product.items():
            entry = fits.get(factor)
            if entry is None:
                continue
            values[reference], notes[reference] = entry

        if not values:
            continue

        dimensions.append(
            DimensionComparison(
                factor=factor,
                label=label,
                values=values,
                notes=notes,
                differs=len(set(values.values())) > 1,
                is_priority=factor in priority_factors,
                spread=_spread(values),
            )
        )
    return dimensions


def biggest_differences(dimensions: list[DimensionComparison]) -> list[DimensionComparison]:
    """The dimensions that most separate these options.

    Ranked by how far apart the labels are, with a dimension the user said
    mattered breaking ties — so a difference they care about outranks an
    equally large one they did not mention. Ties then fall back to catalogue
    order, which keeps the result stable between requests.
    """
    order = {dimension.factor: index for index, dimension in enumerate(dimensions)}
    differing = [dimension for dimension in dimensions if dimension.differs]
    differing.sort(
        key=lambda dimension: (
            -dimension.spread,
            0 if dimension.is_priority else 1,
            order[dimension.factor],
        )
    )
    return differing[:MAX_DIFFERENCES]


def priority_dimensions(dimensions: list[DimensionComparison]) -> list[DimensionComparison]:
    """The dimensions the user's priorities point at.

    Included whether or not they differ: "all three are strong here" is a
    useful answer to "does my priority separate these?", and hiding it would
    leave the reader wondering.
    """
    return [dimension for dimension in dimensions if dimension.is_priority]
