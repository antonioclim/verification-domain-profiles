"""Deterministic benchmark-instance construction."""
from __future__ import annotations

from fractions import Fraction
from itertools import permutations
import random
from typing import Iterable, Sequence

from .model import Alternative, FiniteInstance
from .oracles import AssignmentData, Edge, LayeredPathData
from .profile import classify_minimum_budget, full_domain_minimum_budget


def explicit_profile_instance(p: int, class_name: str, seed: int) -> FiniteInstance:
    """Controlled finite instance with a known profile class."""
    if p < 2:
        raise ValueError("p must be at least two")
    rng = random.Random((seed << 8) + p)
    m = 1
    alternatives: list[Alternative] = [Alternative("candidate", (0,) * p, (0,), {"kind": "candidate"})]
    if class_name == "harmless":
        for i in range(p):
            d = [rng.randint(1, 4) for _ in range(p)]
            d[i] += 3
            alternatives.append(Alternative(f"core{i}", tuple(d), (rng.randint(-2, 3),), {"kind": "core"}))
    elif class_name == "repairable":
        for i in range(p):
            d = [0] * p
            d[i] = -1
            alternatives.append(Alternative(f"core{i}", tuple(d), (1,), {"kind": "core"}))
    elif class_name == "irreparable":
        for i in range(p):
            if p == 2:
                d = [1, -2] if i == 0 else [-2, 1]
            else:
                d = [-1] * p
                d[i] = p - 2
            h = 1 if i < p - 1 else -(p - 1)
            alternatives.append(Alternative(f"core{i}", tuple(d), (h,), {"kind": "core"}))
    else:
        raise ValueError(f"unknown class {class_name!r}")
    # Add non-binding alternatives without changing the controlled class.
    for k in range(4):
        d = tuple(rng.randint(1, 7) for _ in range(p))
        alternatives.append(Alternative(f"noise{k}", d, (rng.randint(-2, 4),), {"kind": "noise"}))
    objective_scales = tuple(
        max(1, max(abs(alt.objectives[i]) for alt in alternatives)) for i in range(p)
    )
    constraint_scales = (max(1, max(abs(alt.constraints[0]) for alt in alternatives)),)
    instance = FiniteInstance(
        identifier=f"explicit-p{p}-{class_name}-s{seed}",
        candidate_id="candidate",
        alternatives=tuple(alternatives),
        objective_scales=objective_scales,
        constraint_scales=constraint_scales,
        family="explicit_controlled",
        metadata={"target_class": class_name, "seed": seed},
    )
    observed = classify_minimum_budget(full_domain_minimum_budget(instance))
    if observed != class_name:
        raise AssertionError(f"controlled class mismatch: expected {class_name}, observed {observed}")
    return instance


def _quantile(values: Sequence[int], fraction: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def _epsilon_candidate(records: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]], p: int) -> tuple[int, ...]:
    """Choose a Pareto-efficient candidate without a certificate weight."""
    current = list(records)
    for objective in range(1, p):
        threshold = _quantile([record[1][objective] for record in current], 0.55)
        filtered = [record for record in current if record[1][objective] <= threshold]
        if filtered:
            current = filtered
    return min(current, key=lambda record: (record[1], record[0]))[0]


def random_assignment_data(n: int, p: int, seed: int) -> AssignmentData:
    if n > 9:
        raise ValueError("candidate selection enumerates assignments and is limited to n<=9")
    rng = random.Random(1000003 * seed + 97 * n + p)
    objectives = tuple(
        tuple(tuple(rng.randint(1, 80) for _ in range(n)) for _ in range(n))
        for _ in range(p)
    )
    resources = (
        tuple(tuple(rng.randint(1, 30) for _ in range(n)) for _ in range(n)),
    )
    records: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []
    all_resource: list[int] = []
    for perm in permutations(range(n)):
        obj = tuple(sum(objectives[k][i][perm[i]] for i in range(n)) for k in range(p))
        resource = (sum(resources[0][i][perm[i]] for i in range(n)),)
        records.append((tuple(perm), obj, resource))
        all_resource.append(resource[0])
    initial_budget = _quantile(all_resource, 0.58)
    feasible = [record for record in records if record[2][0] <= initial_budget]
    if not feasible:
        raise AssertionError("assignment feasible set unexpectedly empty")
    candidate = _epsilon_candidate(feasible, p)
    candidate_record = next(record for record in records if record[0] == candidate)
    budgets = candidate_record[2]
    candidate_obj = candidate_record[1]
    objective_scales = tuple(
        max(1, max(abs(record[1][k] - candidate_obj[k]) for record in records))
        for k in range(p)
    )
    constraint_scales = (
        max(1, max(abs(record[2][0] - budgets[0]) for record in records)),
    )
    return AssignmentData(
        objectives=objectives,
        resources=resources,
        candidate=candidate,
        budgets=budgets,
        identifier=f"assignment-n{n}-p{p}-s{seed}",
        objective_scales=objective_scales,
        constraint_scales=constraint_scales,
    )


def random_layered_path_data(width: int, internal_layers: int, p: int, seed: int) -> LayeredPathData:
    if width < 2 or internal_layers < 1:
        raise ValueError("invalid layered graph dimensions")
    rng = random.Random(2000003 * seed + 193 * width + 17 * internal_layers + p)
    source = 0
    layers: list[tuple[int, ...]] = [(source,)]
    next_node = 1
    for _ in range(internal_layers):
        layer = tuple(range(next_node, next_node + width))
        next_node += width
        layers.append(layer)
    sink = next_node
    layers.append((sink,))
    edges: list[Edge] = []
    edge_index = 0
    for layer_index in range(len(layers) - 1):
        for u in layers[layer_index]:
            for v in layers[layer_index + 1]:
                objectives = tuple(rng.randint(1, 60) for _ in range(p))
                resources = (rng.randint(1, 22),)
                edges.append(Edge(u, v, objectives, resources, f"e{edge_index:06d}"))
                edge_index += 1
    provisional = LayeredPathData(
        identifier=f"path-w{width}-l{internal_layers}-p{p}-s{seed}",
        layers=tuple(layers),
        edges=tuple(edges),
        source=source,
        sink=sink,
        candidate_edges=tuple(),
        budgets=(0,),
        objective_scales=(1,) * p,
        constraint_scales=(1,),
    )
    paths = provisional.enumerate_paths()
    records: list[tuple[tuple[str, ...], tuple[int, ...], tuple[int, ...]]] = []
    resources_all: list[int] = []
    edge_map = provisional.edge_map()
    for path in paths:
        selected = [edge_map[eid] for eid in path]
        obj = tuple(sum(edge.objectives[k] for edge in selected) for k in range(p))
        resource = (sum(edge.resources[0] for edge in selected),)
        records.append((path, obj, resource))
        resources_all.append(resource[0])
    initial_budget = _quantile(resources_all, 0.58)
    feasible = [record for record in records if record[2][0] <= initial_budget]
    candidate = _epsilon_candidate(feasible, p)
    candidate_record = next(record for record in records if record[0] == candidate)
    budgets = candidate_record[2]
    candidate_obj = candidate_record[1]
    objective_scales = tuple(
        max(1, max(abs(record[1][k] - candidate_obj[k]) for record in records))
        for k in range(p)
    )
    constraint_scales = (
        max(1, max(abs(record[2][0] - budgets[0]) for record in records)),
    )
    return LayeredPathData(
        identifier=provisional.identifier,
        layers=provisional.layers,
        edges=provisional.edges,
        source=source,
        sink=sink,
        candidate_edges=tuple(candidate),
        budgets=budgets,
        objective_scales=objective_scales,
        constraint_scales=constraint_scales,
    )
