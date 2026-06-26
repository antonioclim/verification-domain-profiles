#!/usr/bin/env python3
"""Numerical full-domain scaling baseline for the enumerated scaling cases.

The baseline uses floating-point HiGHS and is retained only as a timing and
sanity comparison. Exact row-generation classifications remain authoritative.
"""
from __future__ import annotations

import csv
import json
import math
import time
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mmor_certificates.instances import random_assignment_data, random_layered_path_data

protocol = json.loads((ROOT / "protocol/COMPUTATIONAL_PROTOCOL.json").read_text(encoding="utf-8"))
with (ROOT / "results/raw/scaling_cases.csv").open(encoding="utf-8", newline="") as handle:
    structured = {row["case_id"]: row for row in csv.DictReader(handle)}


def solve(finite):
    p, m, candidate = finite.p, finite.m, finite.candidate
    A = np.empty((len(finite.challengers), p + m), dtype=float)
    for row_index, alternative in enumerate(finite.challengers):
        for i in range(p):
            A[row_index, i] = (
                alternative.objectives[i] - candidate.objectives[i]
            ) / finite.objective_scales[i]
        for j in range(m):
            A[row_index, p + j] = alternative.constraints[j] / finite.constraint_scales[j]
    objective = np.asarray([0.0] * p + [1.0] * m, dtype=float)
    equality = np.asarray([[1.0] * p + [0.0] * m], dtype=float)
    start = time.perf_counter_ns()
    result = linprog(
        objective,
        A_ub=-A,
        b_ub=np.zeros(len(A)),
        A_eq=equality,
        b_eq=[1.0],
        bounds=[(0, None)] * (p + m),
        method="highs",
    )
    elapsed = time.perf_counter_ns() - start
    return result, elapsed


def record(case_id, family, domain_size, p, result, elapsed):
    structured_ns = int(structured[case_id]["structured_solve_ns"])
    return {
        "case_id": case_id,
        "family": family,
        "domain_size": domain_size,
        "p": p,
        "status": int(result.status),
        "objective": None if result.fun is None else float(result.fun),
        "full_numeric_ns": elapsed,
        "structured_solve_ns": structured_ns,
        "speed_ratio_full_numeric_over_structured": elapsed / structured_ns,
    }


rows = []
for cfg in protocol["scaling_corpus"]["assignment"]:
    data = random_assignment_data(cfg["n"], cfg["p"], cfg["seed"])
    result, elapsed = solve(data.to_finite_instance())
    row = record(data.identifier, "assignment", math.factorial(cfg["n"]), cfg["p"], result, elapsed)
    rows.append(row)
    print(json.dumps(row), flush=True)
for cfg in protocol["scaling_corpus"]["layered_shortest_path"]:
    if cfg["internal_layers"] > 9:
        continue
    data = random_layered_path_data(cfg["width"], cfg["internal_layers"], cfg["p"], cfg["seed"])
    result, elapsed = solve(data.to_finite_instance())
    row = record(
        data.identifier,
        "layered_shortest_path",
        cfg["width"] ** cfg["internal_layers"],
        cfg["p"],
        result,
        elapsed,
    )
    rows.append(row)
    print(json.dumps(row), flush=True)

path = ROOT / "results/raw/numeric_full_domain_scaling.csv"
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

summary_path = ROOT / "results/processed/study_summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
ratios = [row["speed_ratio_full_numeric_over_structured"] for row in rows]
summary.update(
    {
        "numeric_scaling_baseline_cases": len(rows),
        "numeric_scaling_min_full_over_structured": min(ratios),
        "numeric_scaling_median_full_over_structured": float(np.median(ratios)),
        "numeric_scaling_max_full_over_structured": max(ratios),
    }
)
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
