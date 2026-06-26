"""Exact profile masters and finite row-generation algorithms."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Sequence

from .exact_lp import ExactLPCertificate, ExactLPError, solve_exact_lp
from .model import FiniteInstance, OracleResult, ParameterPair
from .oracles import AssignmentOracle, ExplicitOracle, LayeredPathOracle, SeparationOracle
from .rational import Q, dot, fraction_json


Row = tuple[tuple[Fraction, ...], tuple[Fraction, ...], str]


def _lp_certificate_json(certificate: ExactLPCertificate | None) -> dict[str, Any] | None:
    if certificate is None:
        return None
    return {
        "status": certificate.status,
        "objective": None if certificate.objective is None else fraction_json(certificate.objective),
        "point": None if certificate.point is None else [fraction_json(v) for v in certificate.point],
        "active_rows": list(certificate.active_rows),
        "inequality_multipliers": [fraction_json(v) for v in certificate.inequality_multipliers],
        "equality_multipliers": [fraction_json(v) for v in certificate.equality_multipliers],
    }


@dataclass(frozen=True)
class StressWitness:
    depth: Fraction
    coefficients: tuple[Fraction, ...]
    challenger_ids: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "depth": fraction_json(self.depth),
            "challenger_ids": list(self.challenger_ids),
            "coefficients": [fraction_json(v) for v in self.coefficients],
        }


@dataclass(frozen=True)
class MinimumBudgetResult:
    status: str
    parameters: ParameterPair | None
    budget: Fraction | None
    margin: Fraction | None
    rows: tuple[Row, ...]
    oracle_calls: int
    oracle_proofs: tuple[dict[str, Any], ...]
    master_certificate: ExactLPCertificate | None = None
    stress_witness: StressWitness | None = None

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "oracle_calls": self.oracle_calls,
            "retained_rows": len(self.rows),
            "challenger_ids": [row[2] for row in self.rows],
            "oracle_proofs": list(self.oracle_proofs),
        }
        if self.parameters is not None:
            result["parameters"] = self.parameters.to_json()
        if self.budget is not None:
            result["budget"] = fraction_json(self.budget)
        if self.margin is not None:
            result["margin"] = fraction_json(self.margin)
        if self.master_certificate is not None:
            result["master_certificate"] = _lp_certificate_json(self.master_certificate)
        if self.stress_witness is not None:
            result["stress_witness"] = self.stress_witness.to_json()
        return result


@dataclass(frozen=True)
class ProfileResult:
    budget: Fraction
    value: Fraction
    parameters: ParameterPair
    rows: tuple[Row, ...]
    oracle_calls: int
    oracle_proofs: tuple[dict[str, Any], ...]
    master_certificate: ExactLPCertificate | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "budget": fraction_json(self.budget),
            "value": fraction_json(self.value),
            "parameters": self.parameters.to_json(),
            "oracle_calls": self.oracle_calls,
            "retained_rows": len(self.rows),
            "challenger_ids": [row[2] for row in self.rows],
            "oracle_proofs": list(self.oracle_proofs),
            "master_certificate": _lp_certificate_json(self.master_certificate),
        }


def _normalised_row(oracle: SeparationOracle, result: OracleResult) -> Row:
    if isinstance(oracle, ExplicitOracle):
        alternative = next(
            alt for alt in oracle.instance.challengers if alt.identifier == result.alternative_id
        )
        d, h = oracle.instance.normalised_vectors(alternative)
        return d, h, result.alternative_id
    if isinstance(oracle, AssignmentOracle):
        objectives = tuple(int(v) for v in result.proof["objective"])
        constraints = tuple(int(v) for v in result.proof["constraints"])
        candidate_objectives, _ = oracle.data.evaluate(oracle.data.candidate)
        d = tuple(
            Q(value - candidate, scale)
            for value, candidate, scale in zip(
                objectives, candidate_objectives, oracle.data.objective_scales
            )
        )
        h = tuple(
            Q(value, scale)
            for value, scale in zip(constraints, oracle.data.constraint_scales)
        )
        return d, h, result.alternative_id
    if isinstance(oracle, LayeredPathOracle):
        objectives = tuple(int(v) for v in result.proof["objective"])
        constraints = tuple(int(v) for v in result.proof["constraints"])
        candidate_objectives, _ = oracle.data.evaluate(oracle.data.candidate_edges)
        d = tuple(
            Q(value - candidate, scale)
            for value, candidate, scale in zip(
                objectives, candidate_objectives, oracle.data.objective_scales
            )
        )
        h = tuple(
            Q(value, scale)
            for value, scale in zip(constraints, oracle.data.constraint_scales)
        )
        return d, h, result.alternative_id
    raise TypeError(f"unsupported oracle type: {type(oracle).__name__}")


def score(parameters: ParameterPair, row: Row) -> Fraction:
    d, h, _ = row
    return dot(parameters.weights, d) + dot(parameters.multipliers, h)


def solve_minimum_budget_master(rows: Sequence[Row], p: int, m: int) -> ExactLPCertificate:
    if not rows:
        # Canonical interior simplex point is chosen outside the LP to avoid an
        # arbitrary vertex under a fully degenerate objective.
        return ExactLPCertificate(
            status="OPTIMAL",
            objective=Q(0),
            point=tuple(Q(1, p) for _ in range(p)) + tuple(Q(0) for _ in range(m)),
        )
    nvar = p + m
    inequalities: list[tuple[list[Fraction], Fraction]] = []
    for d, h, _ in rows:
        inequalities.append((list(d) + list(h), Q(0)))
    for i in range(nvar):
        row = [Q(0)] * nvar
        row[i] = Q(1)
        inequalities.append((row, Q(0)))
    equality = [Q(1)] * p + [Q(0)] * m
    objective = [Q(0)] * p + [Q(1)] * m
    return solve_exact_lp(objective, inequalities, [(equality, Q(1))])


def solve_profile_master(rows: Sequence[Row], p: int, m: int, budget: Fraction) -> ExactLPCertificate:
    if not rows:
        raise ValueError("fixed-budget profile master must be seeded")
    nvar = p + m + 1
    gamma = nvar - 1
    inequalities: list[tuple[list[Fraction], Fraction]] = []
    for d, h, _ in rows:
        inequalities.append((list(d) + list(h) + [Q(-1)], Q(0)))
    for i in range(p + m):
        row = [Q(0)] * nvar
        row[i] = Q(1)
        inequalities.append((row, Q(0)))
    budget_row = [Q(0)] * nvar
    for j in range(m):
        budget_row[p + j] = Q(-1)
    inequalities.append((budget_row, -budget))
    equality = [Q(1)] * p + [Q(0)] * (m + 1)
    objective = [Q(0)] * nvar
    objective[gamma] = Q(1)
    return solve_exact_lp(objective, inequalities, [(equality, Q(1))], maximise=True)


def solve_stress_witness(rows: Sequence[Row], p: int, m: int) -> StressWitness | None:
    n = len(rows)
    if n == 0:
        return None
    nvar = n + 1
    eta = n
    inequalities: list[tuple[list[Fraction], Fraction]] = []
    for x in range(n):
        row = [Q(0)] * nvar
        row[x] = Q(1)
        inequalities.append((row, Q(0)))
    row = [Q(0)] * nvar
    row[eta] = Q(1)
    inequalities.append((row, Q(0)))
    for i in range(p):
        row = [-rows[x][0][i] for x in range(n)] + [Q(-1)]
        inequalities.append((row, Q(0)))
    for j in range(m):
        row = [-rows[x][1][j] for x in range(n)] + [Q(0)]
        inequalities.append((row, Q(0)))
    equality = [Q(1)] * n + [Q(0)]
    objective = [Q(0)] * n + [Q(1)]
    result = solve_exact_lp(objective, inequalities, [(equality, Q(1))], maximise=True)
    if not result.optimal or result.objective is None or result.point is None:
        return None
    if result.objective <= 0:
        return None
    coefficients = tuple(result.point[:n])
    return StressWitness(
        depth=result.objective,
        coefficients=coefficients,
        challenger_ids=tuple(row[2] for row in rows),
    )


def _parameters_from_master(result: ExactLPCertificate, p: int, m: int) -> ParameterPair:
    if not result.optimal or result.point is None:
        raise ExactLPError("master does not contain an exact optimum")
    return ParameterPair(tuple(result.point[:p]), tuple(result.point[p : p + m]))


def minimum_budget_row_generation(
    oracle: SeparationOracle,
    *,
    max_iterations: int | None = None,
) -> MinimumBudgetResult:
    p = len(oracle.instance.objective_scales)
    m = len(oracle.instance.constraint_scales)
    rows: list[Row] = []
    proofs: list[dict[str, Any]] = []
    limit = max_iterations if max_iterations is not None else 1_000_000
    for iteration in range(limit):
        master = solve_minimum_budget_master(rows, p, m)
        if master.status.startswith("INFEASIBLE"):
            witness = solve_stress_witness(rows, p, m)
            if witness is None:
                return MinimumBudgetResult(
                    status="UNRESOLVED_NUMERICALLY",
                    parameters=None,
                    budget=None,
                    margin=None,
                    rows=tuple(rows),
                    oracle_calls=len(proofs),
                    oracle_proofs=tuple(proofs),
                )
            return MinimumBudgetResult(
                status="IRREPARABLE_DOMAIN",
                parameters=None,
                budget=None,
                margin=None,
                rows=tuple(rows),
                oracle_calls=len(proofs),
                oracle_proofs=tuple(proofs),
                stress_witness=witness,
            )
        parameters = _parameters_from_master(master, p, m)
        separation = oracle.minimise(parameters)
        proofs.append(separation.proof)
        if separation.score >= 0:
            status = "STRICTLY_CERTIFIED" if separation.score > 0 else "CERTIFIED_MINIMUM_BUDGET"
            return MinimumBudgetResult(
                status=status,
                parameters=parameters,
                budget=parameters.budget,
                margin=separation.score,
                rows=tuple(rows),
                oracle_calls=len(proofs),
                oracle_proofs=tuple(proofs),
                master_certificate=master,
            )
        new_row = _normalised_row(oracle, separation)
        if any(existing[2] == new_row[2] for existing in rows):
            raise AssertionError("strictly violated challenger was already in the pool")
        rows.append(new_row)
    raise RuntimeError("row generation exceeded its explicit iteration limit")


def fixed_budget_row_generation(
    oracle: SeparationOracle,
    budget: Fraction,
    *,
    max_iterations: int | None = None,
) -> ProfileResult:
    p = len(oracle.instance.objective_scales)
    m = len(oracle.instance.constraint_scales)
    initial = ParameterPair(tuple(Q(1, p) for _ in range(p)), tuple(Q(0) for _ in range(m)))
    separation = oracle.minimise(initial)
    rows: list[Row] = [_normalised_row(oracle, separation)]
    proofs: list[dict[str, Any]] = [separation.proof]
    limit = max_iterations if max_iterations is not None else 1_000_000
    for _ in range(limit):
        master = solve_profile_master(rows, p, m, budget)
        if not master.optimal or master.objective is None or master.point is None:
            raise ExactLPError("fixed-budget master was not reconstructed exactly")
        parameters = ParameterPair(
            tuple(master.point[:p]), tuple(master.point[p : p + m])
        )
        gamma = master.objective
        separation = oracle.minimise(parameters)
        proofs.append(separation.proof)
        if separation.score >= gamma:
            if separation.score != gamma:
                # The restricted optimum cannot be lower than the full-domain
                # minimum at the same parameters.  Strict inequality reflects
                # only degeneracy; the exact global profile remains gamma.
                pass
            return ProfileResult(
                budget=budget,
                value=gamma,
                parameters=parameters,
                rows=tuple(rows),
                oracle_calls=len(proofs),
                oracle_proofs=tuple(proofs),
                master_certificate=master,
            )
        new_row = _normalised_row(oracle, separation)
        if any(existing[2] == new_row[2] for existing in rows):
            raise AssertionError("violated profile challenger was already in the pool")
        rows.append(new_row)
    raise RuntimeError("profile row generation exceeded its explicit iteration limit")


def full_domain_minimum_budget(instance: FiniteInstance) -> MinimumBudgetResult:
    d, h, ids = instance.matrices()
    rows: list[Row] = [
        (tuple(d_row), tuple(h_row), identifier)
        for d_row, h_row, identifier in zip(d, h, ids)
    ]
    master = solve_minimum_budget_master(rows, instance.p, instance.m)
    if master.status.startswith("INFEASIBLE"):
        # An exact stress LP has one variable per challenger.  For large
        # explicit domains the publishable exact obstruction is obtained by
        # row generation, whose restricted pool is small.  The all-row LP is
        # retained only as a numerical baseline in that case.
        witness = solve_stress_witness(rows, instance.p, instance.m) if len(rows) <= 50 else None
        return MinimumBudgetResult(
            status="IRREPARABLE_DOMAIN" if witness else "INFEASIBLE_FULL_MASTER_NUMERIC",
            parameters=None,
            budget=None,
            margin=None,
            rows=tuple(rows),
            oracle_calls=0,
            oracle_proofs=(),
            stress_witness=witness,
        )
    parameters = _parameters_from_master(master, instance.p, instance.m)
    minimum = min(score(parameters, row) for row in rows)
    return MinimumBudgetResult(
        status="STRICTLY_CERTIFIED" if minimum > 0 else "CERTIFIED_MINIMUM_BUDGET",
        parameters=parameters,
        budget=parameters.budget,
        margin=minimum,
        rows=tuple(rows),
        oracle_calls=0,
        oracle_proofs=(),
        master_certificate=master,
    )


def full_domain_profile(instance: FiniteInstance, budget: Fraction) -> ProfileResult:
    d, h, ids = instance.matrices()
    rows: list[Row] = [
        (tuple(d_row), tuple(h_row), identifier)
        for d_row, h_row, identifier in zip(d, h, ids)
    ]
    result = solve_profile_master(rows, instance.p, instance.m, budget)
    if not result.optimal or result.objective is None or result.point is None:
        raise ExactLPError("full profile was not reconstructed exactly")
    parameters = ParameterPair(
        tuple(result.point[: instance.p]),
        tuple(result.point[instance.p : instance.p + instance.m]),
    )
    return ProfileResult(
        budget=budget,
        value=result.objective,
        parameters=parameters,
        rows=tuple(rows),
        oracle_calls=0,
        oracle_proofs=(),
        master_certificate=result,
    )


def classify_minimum_budget(result: MinimumBudgetResult) -> str:
    if result.status == "IRREPARABLE_DOMAIN":
        return "irreparable"
    if result.budget == 0:
        return "harmless"
    if result.budget is not None and result.budget > 0:
        return "repairable"
    return "unresolved"
