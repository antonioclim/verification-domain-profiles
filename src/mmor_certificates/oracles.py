"""Exact full-domain separation oracles."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations
from typing import Iterable, Protocol, Sequence

from .model import Alternative, FiniteInstance, OracleResult, ParameterPair
from .rational import Q, dot, fraction_json, lcm_many


class SeparationOracle(Protocol):
    instance: FiniteInstance

    def minimise(self, parameters: ParameterPair) -> OracleResult: ...


@dataclass
class ExplicitOracle:
    instance: FiniteInstance

    def minimise(self, parameters: ParameterPair) -> OracleResult:
        best: tuple[Fraction, str, Alternative] | None = None
        for alternative in self.instance.challengers:
            d, h = self.instance.normalised_vectors(alternative)
            value = dot(parameters.weights, d) + dot(parameters.multipliers, h)
            item = (value, alternative.identifier, alternative)
            if best is None or item[:2] < best[:2]:
                best = item
        if best is None:
            raise ValueError("separation is undefined without challengers")
        value, _, alternative = best
        return OracleResult(
            alternative_id=alternative.identifier,
            score=value,
            decision=alternative.decision,
            proof={
                "type": "explicit_enumeration",
                "challengers_checked": len(self.instance.challengers),
                "minimum": fraction_json(value),
            },
        )


def _integer_cost_matrix(costs: Sequence[Sequence[Fraction]]) -> tuple[list[list[int]], int]:
    denominator = lcm_many(value.denominator for row in costs for value in row)
    integer = [
        [value.numerator * (denominator // value.denominator) for value in row]
        for row in costs
    ]
    return integer, denominator


def hungarian_integer(cost: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], int, tuple[int, ...], tuple[int, ...]]:
    """Minimum-cost square assignment with exact integer dual potentials."""
    n = len(cost)
    if n == 0 or any(len(row) != n for row in cost):
        raise ValueError("Hungarian adapter requires a non-empty square matrix")
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    inf = 10**100
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta or (minv[j] == delta and j < j1):
                    delta = minv[j]
                    j1 = j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * n
    for j in range(1, n + 1):
        assignment[p[j] - 1] = j - 1
    optimum = sum(cost[i][assignment[i]] for i in range(n))
    # Exact dual verification.
    if any(u[i + 1] + v[j + 1] > cost[i][j] for i in range(n) for j in range(n)):
        raise AssertionError("Hungarian dual infeasible")
    if any(u[i + 1] + v[assignment[i] + 1] != cost[i][assignment[i]] for i in range(n)):
        raise AssertionError("Hungarian complementary slackness failure")
    if sum(u[1:]) + sum(v[1:]) != optimum:
        raise AssertionError("Hungarian strong-duality failure")
    return tuple(assignment), optimum, tuple(u[1:]), tuple(v[1:])


@dataclass(frozen=True)
class AssignmentData:
    objectives: tuple[tuple[tuple[int, ...], ...], ...]
    resources: tuple[tuple[tuple[int, ...], ...], ...]
    candidate: tuple[int, ...]
    budgets: tuple[int, ...]
    identifier: str
    objective_scales: tuple[int, ...]
    constraint_scales: tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.candidate)

    @property
    def p(self) -> int:
        return len(self.objectives)

    @property
    def m(self) -> int:
        return len(self.resources)

    def evaluate(self, permutation: Sequence[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
        obj = tuple(sum(self.objectives[k][i][permutation[i]] for i in range(self.n)) for k in range(self.p))
        resource = tuple(sum(self.resources[k][i][permutation[i]] for i in range(self.n)) for k in range(self.m))
        constraints = tuple(resource[k] - self.budgets[k] for k in range(self.m))
        return obj, constraints

    def to_finite_instance(self, *, enumerate_all: bool = True) -> FiniteInstance:
        if not enumerate_all:
            raise ValueError("finite materialisation is only available by enumeration")
        alternatives: list[Alternative] = []
        for idx, permutation in enumerate(permutations(range(self.n))):
            obj, con = self.evaluate(permutation)
            alternatives.append(
                Alternative(
                    identifier=f"a{idx:06d}",
                    objectives=obj,
                    constraints=con,
                    decision=list(permutation),
                )
            )
        candidate_obj, candidate_con = self.evaluate(self.candidate)
        if any(candidate_con):
            raise AssertionError("assignment candidate must be active")
        candidate_id = next(
            alt.identifier for alt in alternatives if tuple(alt.decision) == self.candidate
        )
        return FiniteInstance(
            identifier=self.identifier,
            candidate_id=candidate_id,
            alternatives=tuple(alternatives),
            objective_scales=self.objective_scales,
            constraint_scales=self.constraint_scales,
            family="assignment",
            metadata={"n": self.n},
        )


@dataclass
class AssignmentOracle:
    data: AssignmentData

    @property
    def instance(self) -> FiniteInstance:
        candidate_obj, candidate_con = self.data.evaluate(self.data.candidate)
        return FiniteInstance(
            identifier=self.data.identifier,
            candidate_id="candidate",
            alternatives=(
                Alternative("candidate", candidate_obj, candidate_con, list(self.data.candidate)),
                Alternative("implicit-reference", candidate_obj, tuple(1 for _ in candidate_con), None),
            ),
            objective_scales=self.data.objective_scales,
            constraint_scales=self.data.constraint_scales,
            family="assignment",
            metadata={"n": self.data.n, "implicit": True},
        )

    def minimise(self, parameters: ParameterPair) -> OracleResult:
        n = self.data.n
        matrix: list[list[Fraction]] = []
        for i in range(n):
            row: list[Fraction] = []
            for j in range(n):
                value = sum(
                    (
                        parameters.weights[k]
                        * Q(self.data.objectives[k][i][j], self.data.objective_scales[k])
                        for k in range(self.data.p)
                    ),
                    Q(0),
                )
                value += sum(
                    (
                        parameters.multipliers[k]
                        * Q(self.data.resources[k][i][j], self.data.constraint_scales[k])
                        for k in range(self.data.m)
                    ),
                    Q(0),
                )
                row.append(value)
            matrix.append(row)
        integer_cost, denominator = _integer_cost_matrix(matrix)
        permutation, optimum_int, u, v = hungarian_integer(integer_cost)
        excluded_subproblems: list[dict[str, int]] = []
        if permutation == self.data.candidate:
            max_abs = max(abs(value) for row in integer_cost for value in row)
            forbidden_cost = (2 * n + 1) * max(1, max_abs) + 1
            alternatives: list[tuple[int, tuple[int, ...], tuple[int, ...], tuple[int, ...], int]] = []
            for row_index, candidate_column in enumerate(self.data.candidate):
                modified = [list(row) for row in integer_cost]
                modified[row_index][candidate_column] = forbidden_cost
                perm_i, value_i, u_i, v_i = hungarian_integer(modified)
                if perm_i[row_index] == candidate_column:
                    continue
                true_value = sum(integer_cost[i][perm_i[i]] for i in range(n))
                alternatives.append((true_value, perm_i, u_i, v_i, row_index))
                excluded_subproblems.append({"forbidden_row": row_index, "optimum": true_value})
            if not alternatives:
                raise RuntimeError("assignment domain contains no challenger")
            optimum_int, permutation, u, v, selected_forbidden_row = min(
                alternatives, key=lambda item: (item[0], item[1], item[4])
            )
        else:
            selected_forbidden_row = -1
        candidate_raw = sum(
            (
                parameters.weights[k]
                * Q(self.data.evaluate(self.data.candidate)[0][k], self.data.objective_scales[k])
                for k in range(self.data.p)
            ),
            Q(0),
        )
        candidate_raw += sum(
            (
                parameters.multipliers[k]
                * Q(self.data.budgets[k], self.data.constraint_scales[k])
                for k in range(self.data.m)
            ),
            Q(0),
        )
        score = Q(optimum_int, denominator) - candidate_raw
        obj, con = self.data.evaluate(permutation)
        identifier = "perm:" + ",".join(map(str, permutation))
        return OracleResult(
            alternative_id=identifier,
            score=score,
            decision=list(permutation),
            proof={
                "type": "assignment_integer_hungarian_dual",
                "integer_scale": denominator,
                "row_potentials": list(u),
                "column_potentials": list(v),
                "objective": list(obj),
                "constraints": list(con),
                "minimum_score": fraction_json(score),
                "candidate_excluded": True,
                "selected_forbidden_row": selected_forbidden_row,
                "excluded_subproblems": excluded_subproblems,
            },
        )


@dataclass(frozen=True)
class Edge:
    source: int
    target: int
    objectives: tuple[int, ...]
    resources: tuple[int, ...]
    identifier: str


@dataclass(frozen=True)
class LayeredPathData:
    identifier: str
    layers: tuple[tuple[int, ...], ...]
    edges: tuple[Edge, ...]
    source: int
    sink: int
    candidate_edges: tuple[str, ...]
    budgets: tuple[int, ...]
    objective_scales: tuple[int, ...]
    constraint_scales: tuple[int, ...]

    @property
    def p(self) -> int:
        return len(self.objective_scales)

    @property
    def m(self) -> int:
        return len(self.constraint_scales)

    def edge_map(self) -> dict[str, Edge]:
        return {edge.identifier: edge for edge in self.edges}

    def evaluate(self, edge_ids: Sequence[str]) -> tuple[tuple[int, ...], tuple[int, ...]]:
        lookup = self.edge_map()
        selected = [lookup[eid] for eid in edge_ids]
        objectives = tuple(sum(edge.objectives[k] for edge in selected) for k in range(self.p))
        resources = tuple(sum(edge.resources[k] for edge in selected) for k in range(self.m))
        return objectives, tuple(resources[k] - self.budgets[k] for k in range(self.m))

    def enumerate_paths(self) -> list[tuple[str, ...]]:
        outgoing: dict[int, list[Edge]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge.source, []).append(edge)
        for edges in outgoing.values():
            edges.sort(key=lambda edge: edge.identifier)
        paths: list[tuple[str, ...]] = []

        def visit(node: int, current: list[str]) -> None:
            if node == self.sink:
                paths.append(tuple(current))
                return
            for edge in outgoing.get(node, []):
                current.append(edge.identifier)
                visit(edge.target, current)
                current.pop()

        visit(self.source, [])
        return paths

    def to_finite_instance(self) -> FiniteInstance:
        alternatives: list[Alternative] = []
        candidate_id = ""
        for idx, path in enumerate(self.enumerate_paths()):
            obj, con = self.evaluate(path)
            identifier = f"path{idx:07d}"
            alternatives.append(Alternative(identifier, obj, con, list(path)))
            if tuple(path) == tuple(self.candidate_edges):
                candidate_id = identifier
        if not candidate_id:
            raise AssertionError("candidate path was not enumerated")
        return FiniteInstance(
            identifier=self.identifier,
            candidate_id=candidate_id,
            alternatives=tuple(alternatives),
            objective_scales=self.objective_scales,
            constraint_scales=self.constraint_scales,
            family="layered_shortest_path",
            metadata={"layers": len(self.layers), "paths": len(alternatives)},
        )


@dataclass
class LayeredPathOracle:
    data: LayeredPathData

    @property
    def instance(self) -> FiniteInstance:
        obj, con = self.data.evaluate(self.data.candidate_edges)
        return FiniteInstance(
            identifier=self.data.identifier,
            candidate_id="candidate",
            alternatives=(
                Alternative("candidate", obj, con, list(self.data.candidate_edges)),
                Alternative("implicit-reference", obj, tuple(1 for _ in con), None),
            ),
            objective_scales=self.data.objective_scales,
            constraint_scales=self.data.constraint_scales,
            family="layered_shortest_path",
            metadata={"implicit": True, "layers": len(self.data.layers)},
        )

    def minimise(self, parameters: ParameterPair) -> OracleResult:
        edge_costs: dict[str, Fraction] = {}
        denominators: list[int] = []
        for edge in self.data.edges:
            value = sum(
                (
                    parameters.weights[k] * Q(edge.objectives[k], self.data.objective_scales[k])
                    for k in range(self.data.p)
                ),
                Q(0),
            )
            value += sum(
                (
                    parameters.multipliers[k] * Q(edge.resources[k], self.data.constraint_scales[k])
                    for k in range(self.data.m)
                ),
                Q(0),
            )
            edge_costs[edge.identifier] = value
            denominators.append(value.denominator)
        scale = lcm_many(denominators)
        int_cost = {
            eid: value.numerator * (scale // value.denominator)
            for eid, value in edge_costs.items()
        }
        nodes = [node for layer in self.data.layers for node in layer]
        incoming: dict[int, list[Edge]] = {}
        for edge in self.data.edges:
            incoming.setdefault(edge.target, []).append(edge)

        def shortest(forbidden: str | None = None) -> tuple[tuple[str, ...], int, dict[int, int]]:
            inf = 10**100
            distance = {node: inf for node in nodes}
            predecessor: dict[int, Edge] = {}
            distance[self.data.source] = 0
            for layer in self.data.layers[1:]:
                for node in layer:
                    candidates = []
                    for edge in incoming.get(node, []):
                        if edge.identifier == forbidden or distance[edge.source] >= inf:
                            continue
                        candidates.append(
                            (distance[edge.source] + int_cost[edge.identifier], edge.identifier, edge)
                        )
                    if candidates:
                        best = min(candidates, key=lambda item: (item[0], item[1]))
                        distance[node] = best[0]
                        predecessor[node] = best[2]
            if distance[self.data.sink] >= inf:
                raise RuntimeError("sink is unreachable under candidate exclusion")
            path: list[str] = []
            node = self.data.sink
            while node != self.data.source:
                edge = predecessor[node]
                path.append(edge.identifier)
                node = edge.source
            path.reverse()
            if any(
                edge.identifier != forbidden
                and distance[edge.source] < inf
                and distance[edge.target] > distance[edge.source] + int_cost[edge.identifier]
                for edge in self.data.edges
            ):
                raise AssertionError("invalid shortest-path potentials")
            return tuple(path), distance[self.data.sink], distance

        path, optimum_int, distance = shortest()
        excluded_subproblems: list[dict[str, int]] = []
        selected_forbidden_edge: str | None = None
        if path == tuple(self.data.candidate_edges):
            alternatives: list[tuple[int, tuple[str, ...], str, dict[int, int]]] = []
            for edge_id in self.data.candidate_edges:
                path_i, value_i, distance_i = shortest(edge_id)
                alternatives.append((value_i, path_i, edge_id, distance_i))
                excluded_subproblems.append({"forbidden_edge": edge_id, "optimum": value_i})
            optimum_int, path, selected_forbidden_edge, distance = min(
                alternatives, key=lambda item: (item[0], item[1], item[2])
            )
        raw_optimum = Q(optimum_int, scale)
        candidate_obj, _ = self.data.evaluate(self.data.candidate_edges)
        candidate_raw = sum(
            (
                parameters.weights[k] * Q(candidate_obj[k], self.data.objective_scales[k])
                for k in range(self.data.p)
            ),
            Q(0),
        )
        candidate_raw += sum(
            (
                parameters.multipliers[k] * Q(self.data.budgets[k], self.data.constraint_scales[k])
                for k in range(self.data.m)
            ),
            Q(0),
        )
        score = raw_optimum - candidate_raw
        obj, con = self.data.evaluate(path)
        return OracleResult(
            alternative_id="path:" + "|".join(path),
            score=score,
            decision=list(path),
            proof={
                "type": "layered_dag_integer_potentials",
                "integer_scale": scale,
                "distance_to_sink": optimum_int,
                "objective": list(obj),
                "constraints": list(con),
                "minimum_score": fraction_json(score),
                "candidate_excluded": True,
                "selected_forbidden_edge": selected_forbidden_edge,
                "excluded_subproblems": excluded_subproblems,
            },
        )
