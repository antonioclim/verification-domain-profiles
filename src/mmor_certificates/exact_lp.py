"""Hybrid numerical discovery with exact rational LP certification.

The numerical solver proposes an active set.  Every accepted result is rebuilt
from an exact rational basis and accompanied by an exact KKT certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Sequence

import numpy as np
from scipy.optimize import linprog

from .rational import Q, dot, q, rank, solve_square


class ExactLPError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExactLPCertificate:
    status: str
    objective: Fraction | None = None
    point: tuple[Fraction, ...] | None = None
    active_rows: tuple[int, ...] = ()
    inequality_multipliers: tuple[Fraction, ...] = ()
    equality_multipliers: tuple[Fraction, ...] = ()
    numerical_status: int | None = None
    numerical_message: str = ""

    @property
    def optimal(self) -> bool:
        return self.status == "OPTIMAL"


def _to_float_matrix(rows: Sequence[Sequence[Fraction]]) -> np.ndarray:
    if not rows:
        return np.empty((0, 0), dtype=float)
    return np.asarray([[float(v) for v in row] for row in rows], dtype=float)


def _feasible(
    point: Sequence[Fraction],
    inequalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    equalities: Sequence[tuple[Sequence[Fraction], Fraction]],
) -> bool:
    return all(dot(row, point) >= rhs for row, rhs in inequalities) and all(
        dot(row, point) == rhs for row, rhs in equalities
    )


def _kkt_certificate(
    c: Sequence[Fraction],
    active: Sequence[int],
    inequalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    equalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    point: Sequence[Fraction],
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]] | None:
    n = len(c)
    active_rows = [tuple(inequalities[i][0]) for i in active]
    equality_rows = [tuple(row) for row, _ in equalities]
    # c - A^T y + E^T beta = 0, hence [A^T, -E^T] [y,beta] = c.
    matrix: list[list[Fraction]] = []
    for coordinate in range(n):
        matrix.append(
            [row[coordinate] for row in active_rows]
            + [-row[coordinate] for row in equality_rows]
        )
    multipliers = solve_square(matrix, c)
    if multipliers is None:
        return None
    y = tuple(multipliers[: len(active_rows)])
    beta = tuple(multipliers[len(active_rows) :])
    if any(value < 0 for value in y):
        return None
    primal = dot(c, point)
    dual = sum(
        (y_i * inequalities[row_index][1] for y_i, row_index in zip(y, active)), Q(0)
    ) - sum(
        (beta_i * rhs for beta_i, (_, rhs) in zip(beta, equalities)), Q(0)
    )
    if primal != dual:
        return None
    return y, beta


def _solve_basis(
    c: Sequence[Fraction],
    active: Sequence[int],
    inequalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    equalities: Sequence[tuple[Sequence[Fraction], Fraction]],
) -> ExactLPCertificate | None:
    rows = [tuple(row) for row, _ in equalities] + [
        tuple(inequalities[i][0]) for i in active
    ]
    rhs = [value for _, value in equalities] + [inequalities[i][1] for i in active]
    if len(rows) != len(c) or rank(rows) != len(c):
        return None
    point = solve_square(rows, rhs)
    if point is None or not _feasible(point, inequalities, equalities):
        return None
    kkt = _kkt_certificate(c, active, inequalities, equalities, point)
    if kkt is None:
        return None
    y, beta = kkt
    return ExactLPCertificate(
        status="OPTIMAL",
        objective=dot(c, point),
        point=tuple(point),
        active_rows=tuple(active),
        inequality_multipliers=y,
        equality_multipliers=beta,
    )


def solve_exact_lp(
    objective: Sequence[Fraction],
    inequalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    equalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    *,
    maximise: bool = False,
    active_tolerance: float = 1e-7,
    max_fallback_combinations: int = 250_000,
) -> ExactLPCertificate:
    """Solve ``min c^T x`` over ``A x >= b, E x = f`` exactly.

    The function accepts arbitrary-sign variables; sign restrictions must be
    supplied as inequalities.  A numerical HiGHS solve discovers an active
    set.  The accepted optimum is reconstructed and certified over rationals.
    """
    c = tuple(q(v) for v in objective)
    if maximise:
        c = tuple(-v for v in c)
    n = len(c)
    A = [(tuple(q(v) for v in row), q(rhs)) for row, rhs in inequalities]
    E = [(tuple(q(v) for v in row), q(rhs)) for row, rhs in equalities]
    if any(len(row) != n for row, _ in A + E):
        raise ValueError("LP row dimension mismatch")
    if rank([row for row, _ in E]) != len(E):
        raise ValueError("equality rows are not independent")
    required_active = n - len(E)
    if required_active < 0:
        raise ValueError("too many equality rows")

    A_float = _to_float_matrix([row for row, _ in A])
    b_float = np.asarray([float(rhs) for _, rhs in A], dtype=float)
    E_float = _to_float_matrix([row for row, _ in E])
    f_float = np.asarray([float(rhs) for _, rhs in E], dtype=float)
    c_float = np.asarray([float(v) for v in c], dtype=float)
    result = linprog(
        c_float,
        A_ub=-A_float if len(A) else None,
        b_ub=-b_float if len(A) else None,
        A_eq=E_float if len(E) else None,
        b_eq=f_float if len(E) else None,
        bounds=[(None, None)] * n,
        method="highs",
    )
    if result.status == 2:
        return ExactLPCertificate(
            status="INFEASIBLE_NUMERICALLY",
            numerical_status=result.status,
            numerical_message=result.message,
        )
    if result.status == 3:
        return ExactLPCertificate(
            status="UNBOUNDED_NUMERICALLY",
            numerical_status=result.status,
            numerical_message=result.message,
        )
    if not result.success or result.x is None:
        return ExactLPCertificate(
            status="NUMERIC_FAILURE",
            numerical_status=result.status,
            numerical_message=result.message,
        )

    if required_active == 0:
        candidate = _solve_basis(c, (), A, E)
        if candidate is None:
            raise ExactLPError("failed to reconstruct equality-defined optimum")
        return ExactLPCertificate(**{**candidate.__dict__, "numerical_status": result.status, "numerical_message": result.message})

    residuals = A_float @ result.x - b_float
    order = sorted(range(len(A)), key=lambda i: (abs(residuals[i]), i))
    active = [i for i in order if abs(residuals[i]) <= active_tolerance]
    try:
        marginals = np.asarray(result.ineqlin.marginals, dtype=float)
        # SciPy solves -A x <= -b.  Its non-positive marginal corresponds to
        # the non-negative multiplier of A x >= b.
        dual_order = sorted(
            range(len(A)),
            key=lambda i: (-max(0.0, -marginals[i]), abs(residuals[i]), i),
        )
        dual_support = [i for i in dual_order if -marginals[i] > 1e-9]
    except Exception:
        dual_order = order
        dual_support = []
    # Degenerate LPs may have hundreds of tight rows.  Enumerating all of them
    # defeats the purpose of numerical active-set discovery.  Prioritise rows
    # carrying positive numerical dual mass, then the nearest residuals.
    priority: list[int] = []
    for i in dual_support + dual_order + order:
        if i not in priority:
            priority.append(i)
    candidate_sets: list[tuple[int, ...]] = []
    for width in (required_active, required_active + 2, required_active + 5, required_active + 9, required_active + 14):
        pool = sorted(priority[: min(len(priority), max(required_active, width))])
        if len(pool) >= required_active:
            candidate_sets.extend(combinations(pool, required_active))
    # Deduplicate while preserving deterministic order.
    seen: set[tuple[int, ...]] = set()
    unique_sets: list[tuple[int, ...]] = []
    for subset in candidate_sets:
        subset = tuple(sorted(subset))
        if subset not in seen:
            seen.add(subset)
            unique_sets.append(subset)

    best: ExactLPCertificate | None = None
    for subset in unique_sets:
        cert = _solve_basis(c, subset, A, E)
        if cert is not None:
            # Exact KKT feasibility already proves global optimality.  The
            # candidate ordering is deterministic, so the first certified
            # basis is a reproducible optimum and no exhaustive enumeration
            # of degenerate optimal bases is required.
            best = cert
            break
    if best is None:
        total = comb(len(A), required_active) if len(A) >= required_active else 0
        if total <= max_fallback_combinations:
            for subset in combinations(range(len(A)), required_active):
                cert = _solve_basis(c, subset, A, E)
                if cert is not None:
                    best = cert
                    break
        if best is None:
            raise ExactLPError(
                f"no exact KKT basis reconstructed; numerical objective={result.fun!r}, "
                f"active_candidates={len(active)}, total_combinations={total}"
            )
    objective_value = -best.objective if maximise and best.objective is not None else best.objective
    if maximise and best.point is not None:
        # Multipliers certify the sign-flipped minimisation problem; retain them
        # and expose the original maximisation objective.
        best = ExactLPCertificate(
            status=best.status,
            objective=objective_value,
            point=best.point,
            active_rows=best.active_rows,
            inequality_multipliers=best.inequality_multipliers,
            equality_multipliers=best.equality_multipliers,
            numerical_status=result.status,
            numerical_message=result.message,
        )
    else:
        best = ExactLPCertificate(
            status=best.status,
            objective=best.objective,
            point=best.point,
            active_rows=best.active_rows,
            inequality_multipliers=best.inequality_multipliers,
            equality_multipliers=best.equality_multipliers,
            numerical_status=result.status,
            numerical_message=result.message,
        )
    return best
