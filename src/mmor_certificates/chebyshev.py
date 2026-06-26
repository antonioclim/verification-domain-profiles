"""Exact admissible intervals for augmented weighted Chebyshev certificates."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .rational import Q, fraction_json


@dataclass(frozen=True)
class ChebyshevInterval:
    lower: Fraction
    upper: Fraction | None
    weights: tuple[Fraction, ...]
    reference: tuple[Fraction, ...]
    conservative_upper: Fraction | None

    def contains_strict(self, rho: Fraction) -> bool:
        if rho <= self.lower:
            return False
        return self.upper is None or rho < self.upper

    def to_json(self) -> dict:
        return {
            "lower": fraction_json(self.lower),
            "upper": None if self.upper is None else fraction_json(self.upper),
            "weights": [fraction_json(v) for v in self.weights],
            "reference": [fraction_json(v) for v in self.reference],
            "conservative_upper": None
            if self.conservative_upper is None
            else fraction_json(self.conservative_upper),
        }


def dominated(outcomes: Sequence[Sequence[Fraction]], candidate: int) -> bool:
    y0 = outcomes[candidate]
    for index, other in enumerate(outcomes):
        if index == candidate:
            continue
        if all(a <= b for a, b in zip(other, y0)) and any(a < b for a, b in zip(other, y0)):
            return True
    return False


def tailored_interval(
    outcomes: Sequence[Sequence[int | Fraction]], candidate: int
) -> ChebyshevInterval:
    y = [tuple(Fraction(v) for v in row) for row in outcomes]
    if not y or not (0 <= candidate < len(y)):
        raise ValueError("invalid finite image or candidate index")
    p = len(y[0])
    if any(len(row) != p for row in y):
        raise ValueError("outcome dimension mismatch")
    if dominated(y, candidate):
        raise ValueError("tailored completeness requires a nondominated candidate")
    y0 = y[candidate]
    minima = [min(row[i] for row in y) for i in range(p)]
    reference = tuple(minima[i] - 1 for i in range(p))
    weights = tuple(Q(1) / (y0[i] - reference[i]) for i in range(p))

    def base(row: Sequence[Fraction]) -> Fraction:
        return max(weights[i] * (row[i] - reference[i]) for i in range(p))

    def total(row: Sequence[Fraction]) -> Fraction:
        return sum((row[i] - reference[i] for i in range(p)), Q(0))

    base0 = base(y0)
    total0 = total(y0)
    lower = Q(0)
    upper: Fraction | None = None
    gaps: list[Fraction] = []
    total_diffs: list[Fraction] = []
    for index, row in enumerate(y):
        if index == candidate:
            continue
        a = base(row) - base0
        b = total(row) - total0
        if a <= 0:
            raise AssertionError("tailored weights should give a positive base gap")
        gaps.append(a)
        total_diffs.append(abs(b))
        if b > 0:
            lower = max(lower, -a / b)
        elif b < 0:
            bound = a / (-b)
            upper = bound if upper is None else min(upper, bound)
    conservative: Fraction | None
    delta = min(gaps) if gaps else None
    delta0 = max(total_diffs) if total_diffs else Q(0)
    if delta is None:
        conservative = None
    elif delta0 == 0:
        conservative = None
    else:
        conservative = delta / delta0
    return ChebyshevInterval(
        lower=max(Q(0), lower),
        upper=upper,
        weights=weights,
        reference=reference,
        conservative_upper=conservative,
    )


def value(
    outcome: Sequence[int | Fraction],
    weights: Sequence[Fraction],
    reference: Sequence[Fraction],
    rho: Fraction,
) -> Fraction:
    row = tuple(Fraction(v) for v in outcome)
    base = max(w * (v - r) for w, v, r in zip(weights, row, reference))
    augmentation = rho * sum((v - r for v, r in zip(row, reference)), Q(0))
    return base + augmentation


def verify_candidate(
    outcomes: Sequence[Sequence[int | Fraction]], candidate: int, interval: ChebyshevInterval, rho: Fraction
) -> tuple[bool, Fraction]:
    y0_value = value(outcomes[candidate], interval.weights, interval.reference, rho)
    gaps = [
        value(row, interval.weights, interval.reference, rho) - y0_value
        for index, row in enumerate(outcomes)
        if index != candidate
    ]
    return (all(gap >= 0 for gap in gaps), min(gaps) if gaps else Q(0))
