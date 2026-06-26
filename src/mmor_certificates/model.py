"""Finite verification-domain data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
from typing import Any, Iterable, Sequence

from .rational import Q, fraction_json, q


@dataclass(frozen=True)
class Alternative:
    identifier: str
    objectives: tuple[int, ...]
    constraints: tuple[int, ...]
    decision: Any = None


@dataclass(frozen=True)
class FiniteInstance:
    identifier: str
    candidate_id: str
    alternatives: tuple[Alternative, ...]
    objective_scales: tuple[int, ...]
    constraint_scales: tuple[int, ...]
    family: str = "explicit"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.alternatives:
            raise ValueError("instance must contain at least one alternative")
        ids = [alt.identifier for alt in self.alternatives]
        if len(ids) != len(set(ids)):
            raise ValueError("alternative identifiers must be unique")
        if self.candidate_id not in ids:
            raise ValueError("candidate identifier is absent")
        p = len(self.objective_scales)
        m = len(self.constraint_scales)
        if p < 2:
            raise ValueError("at least two objectives are required")
        if any(scale <= 0 for scale in self.objective_scales + self.constraint_scales):
            raise ValueError("all scales must be positive")
        for alt in self.alternatives:
            if len(alt.objectives) != p or len(alt.constraints) != m:
                raise ValueError("alternative dimension mismatch")
        candidate = self.candidate
        if any(value != 0 for value in candidate.constraints):
            raise ValueError("candidate active-constraint differences must be zero")

    @property
    def p(self) -> int:
        return len(self.objective_scales)

    @property
    def m(self) -> int:
        return len(self.constraint_scales)

    @property
    def candidate(self) -> Alternative:
        return next(alt for alt in self.alternatives if alt.identifier == self.candidate_id)

    @property
    def challengers(self) -> tuple[Alternative, ...]:
        return tuple(alt for alt in self.alternatives if alt.identifier != self.candidate_id)

    def normalised_vectors(self, alternative: Alternative) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
        candidate = self.candidate
        d = tuple(
            Q(value - base, scale)
            for value, base, scale in zip(
                alternative.objectives, candidate.objectives, self.objective_scales
            )
        )
        h = tuple(
            Q(value, scale)
            for value, scale in zip(alternative.constraints, self.constraint_scales)
        )
        return d, h

    def matrices(self) -> tuple[list[list[Fraction]], list[list[Fraction]], list[str]]:
        d: list[list[Fraction]] = []
        h: list[list[Fraction]] = []
        ids: list[str] = []
        for alternative in self.challengers:
            d_row, h_row = self.normalised_vectors(alternative)
            d.append(list(d_row))
            h.append(list(h_row))
            ids.append(alternative.identifier)
        return d, h, ids

    def digest(self) -> str:
        payload = {
            "identifier": self.identifier,
            "candidate_id": self.candidate_id,
            "family": self.family,
            "objective_scales": self.objective_scales,
            "constraint_scales": self.constraint_scales,
            "alternatives": [
                {
                    "identifier": alt.identifier,
                    "objectives": alt.objectives,
                    "constraints": alt.constraints,
                    "decision": alt.decision,
                }
                for alt in self.alternatives
            ],
        }
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return "sha256:" + hashlib.sha256(data).hexdigest()

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "mmor-verification-instance-1.0",
            "identifier": self.identifier,
            "family": self.family,
            "candidate_id": self.candidate_id,
            "objective_scales": list(self.objective_scales),
            "constraint_scales": list(self.constraint_scales),
            "digest": self.digest(),
            "alternatives": [
                {
                    "identifier": alt.identifier,
                    "objectives": list(alt.objectives),
                    "constraints": list(alt.constraints),
                    "decision": alt.decision,
                }
                for alt in self.alternatives
            ],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class OracleResult:
    alternative_id: str
    score: Fraction
    decision: Any
    proof: dict[str, Any]


@dataclass(frozen=True)
class ParameterPair:
    weights: tuple[Fraction, ...]
    multipliers: tuple[Fraction, ...]

    @property
    def budget(self) -> Fraction:
        return sum(self.multipliers, Q(0))

    def to_json(self) -> dict[str, Any]:
        return {
            "weights": [fraction_json(v) for v in self.weights],
            "multipliers": [fraction_json(v) for v in self.multipliers],
            "budget": fraction_json(self.budget),
        }
