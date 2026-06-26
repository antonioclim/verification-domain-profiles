#!/usr/bin/env python3
"""Execute the frozen MMOR v2 computational protocol."""
from __future__ import annotations

import csv
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mmor_certificates import __version__
from mmor_certificates.chebyshev import tailored_interval, value as cheb_value
from mmor_certificates.instances import (
    explicit_profile_instance,
    random_assignment_data,
    random_layered_path_data,
)
from mmor_certificates.model import Alternative, FiniteInstance
from mmor_certificates.oracles import AssignmentOracle, ExplicitOracle, LayeredPathOracle
from mmor_certificates.profile import (
    MinimumBudgetResult,
    classify_minimum_budget,
    fixed_budget_row_generation,
    full_domain_minimum_budget,
    full_domain_profile,
    minimum_budget_row_generation,
)
from mmor_certificates.rational import Q, fraction_json

PROTOCOL_PATH = ROOT / "protocol" / "COMPUTATIONAL_PROTOCOL.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
RAW = ROOT / "results" / "raw"
PROCESSED = ROOT / "results" / "processed"
FIGURES = ROOT / "figures"
VALIDATION = ROOT / "validation"
for directory in (RAW, PROCESSED, FIGURES, VALIDATION):
    directory.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fraction_or_none(value: Fraction | None) -> str | None:
    return None if value is None else fraction_json(value)


def scaled_instance(instance: FiniteInstance, objective_factors: tuple[int, ...], constraint_factors: tuple[int, ...]) -> FiniteInstance:
    alternatives = tuple(
        Alternative(
            identifier=alt.identifier,
            objectives=tuple(v * f for v, f in zip(alt.objectives, objective_factors)),
            constraints=tuple(v * f for v, f in zip(alt.constraints, constraint_factors)),
            decision=alt.decision,
        )
        for alt in instance.alternatives
    )
    return FiniteInstance(
        identifier=instance.identifier + "-scaled",
        candidate_id=instance.candidate_id,
        alternatives=alternatives,
        objective_scales=tuple(v * f for v, f in zip(instance.objective_scales, objective_factors)),
        constraint_scales=tuple(v * f for v, f in zip(instance.constraint_scales, constraint_factors)),
        family=instance.family,
        metadata={**instance.metadata, "rescaled": True},
    )


def profile_budgets(class_name: str, budget: Fraction | None) -> list[Fraction]:
    if class_name == "repairable":
        assert budget is not None and budget > 0
        return [Q(0), budget / 2, budget, budget * 2 + Q(1, 10)]
    if class_name == "harmless":
        return [Q(0), Q(1, 4), Q(1)]
    return []


def feasible_outcomes(instance: FiniteInstance) -> tuple[list[tuple[int, ...]], int]:
    feasible = [alt for alt in instance.alternatives if all(value <= 0 for value in alt.constraints)]
    candidate_index = next(i for i, alt in enumerate(feasible) if alt.identifier == instance.candidate_id)
    return [alt.objectives for alt in feasible], candidate_index


def chebyshev_record(instance: FiniteInstance) -> dict[str, Any]:
    outcomes, candidate_index = feasible_outcomes(instance)
    interval = tailored_interval(outcomes, candidate_index)
    if interval.upper is None:
        rho = Q(1)
        candidate_value = cheb_value(outcomes[candidate_index], interval.weights, interval.reference, rho)
        strict_gap = min(
            cheb_value(row, interval.weights, interval.reference, rho) - candidate_value
            for i, row in enumerate(outcomes)
            if i != candidate_index
        ) if len(outcomes) > 1 else Q(0)
        return {
            "upper": None,
            "conservative_upper": fraction_or_none(interval.conservative_upper),
            "ratio": None,
            "strict_gap_at_test_rho": fraction_json(strict_gap),
            "tie_at_upper": None,
            "failure_above_upper": None,
        }
    rho = interval.upper / 2
    candidate_value = cheb_value(outcomes[candidate_index], interval.weights, interval.reference, rho)
    strict_gap = min(
        cheb_value(row, interval.weights, interval.reference, rho) - candidate_value
        for i, row in enumerate(outcomes)
        if i != candidate_index
    ) if len(outcomes) > 1 else Q(0)
    at_upper = [
        cheb_value(row, interval.weights, interval.reference, interval.upper)
        - cheb_value(outcomes[candidate_index], interval.weights, interval.reference, interval.upper)
        for i, row in enumerate(outcomes)
        if i != candidate_index
    ]
    above = interval.upper + Q(1, max(10, interval.upper.denominator * 10))
    above_gaps = [
        cheb_value(row, interval.weights, interval.reference, above)
        - cheb_value(outcomes[candidate_index], interval.weights, interval.reference, above)
        for i, row in enumerate(outcomes)
        if i != candidate_index
    ]
    ratio = (
        interval.upper / interval.conservative_upper
        if interval.conservative_upper is not None and interval.conservative_upper > 0
        else None
    )
    return {
        "upper": fraction_json(interval.upper),
        "conservative_upper": fraction_or_none(interval.conservative_upper),
        "ratio": fraction_or_none(ratio),
        "strict_gap_at_test_rho": fraction_json(strict_gap),
        "tie_at_upper": min(at_upper) == 0,
        "failure_above_upper": min(above_gaps) < 0,
    }


def run_case(
    case_id: str,
    instance: FiniteInstance,
    structured_oracle: Any,
    expected_class: str,
    family: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start = time.perf_counter_ns()
    structured = minimum_budget_row_generation(structured_oracle)
    structured_ns = time.perf_counter_ns() - start

    start = time.perf_counter_ns()
    explicit = minimum_budget_row_generation(ExplicitOracle(instance))
    explicit_ns = time.perf_counter_ns() - start

    start = time.perf_counter_ns()
    full = full_domain_minimum_budget(instance)
    full_ns = time.perf_counter_ns() - start

    observed = classify_minimum_budget(structured)
    explicit_class = classify_minimum_budget(explicit)
    full_class = classify_minimum_budget(full)
    classification_agreement = observed == expected_class == explicit_class
    if full.status != "INFEASIBLE_FULL_MASTER_NUMERIC":
        classification_agreement = classification_agreement and full_class == observed
    budget_agreement = structured.budget == explicit.budget
    if full.budget is not None:
        budget_agreement = budget_agreement and structured.budget == full.budget

    objective_factors = tuple(2 + ((i + len(case_id)) % 5) for i in range(instance.p))
    constraint_factors = tuple(3 + ((i + len(case_id)) % 7) for i in range(instance.m))
    scaled = scaled_instance(instance, objective_factors, constraint_factors)
    scaled_result = minimum_budget_row_generation(ExplicitOracle(scaled))
    scale_invariant = (
        classify_minimum_budget(scaled_result) == observed
        and scaled_result.budget == explicit.budget
    )

    profile_rows: list[dict[str, Any]] = []
    for budget in profile_budgets(observed, structured.budget):
        full_profile = full_domain_profile(instance, budget)
        structured_profile = fixed_budget_row_generation(structured_oracle, budget)
        explicit_profile = fixed_budget_row_generation(ExplicitOracle(instance), budget)
        profile_rows.append(
            {
                "case_id": case_id,
                "family": family,
                "p": instance.p,
                "budget": fraction_json(budget),
                "full_value": fraction_json(full_profile.value),
                "structured_value": fraction_json(structured_profile.value),
                "explicit_value": fraction_json(explicit_profile.value),
                "agreement": full_profile.value == structured_profile.value == explicit_profile.value,
                "structured_oracle_calls": structured_profile.oracle_calls,
                "structured_rows": len(structured_profile.rows),
            }
        )

    grid_records: dict[str, Any] = {}
    if structured.budget is not None and structured.budget > 0:
        for denominator in (10, 100, 1000):
            numerator = (structured.budget.numerator * denominator + structured.budget.denominator - 1) // structured.budget.denominator
            approximation = Q(numerator, denominator)
            grid_records[str(denominator)] = {
                "first_grid_budget": fraction_json(approximation),
                "exact_hit": approximation == structured.budget,
                "overestimate": fraction_json(approximation - structured.budget),
            }

    cheb = chebyshev_record(instance)
    record = {
        "case_id": case_id,
        "family": family,
        "p": instance.p,
        "m": instance.m,
        "alternatives": len(instance.alternatives),
        "expected_class": expected_class,
        "observed_class": observed,
        "structured_status": structured.status,
        "structured_budget": fraction_or_none(structured.budget),
        "structured_margin": fraction_or_none(structured.margin),
        "structured_oracle_calls": structured.oracle_calls,
        "structured_rows": len(structured.rows),
        "explicit_status": explicit.status,
        "explicit_budget": fraction_or_none(explicit.budget),
        "explicit_oracle_calls": explicit.oracle_calls,
        "full_status": full.status,
        "full_budget": fraction_or_none(full.budget),
        "classification_agreement": classification_agreement,
        "budget_agreement": budget_agreement,
        "scale_invariant": scale_invariant,
        "structured_time_ns": structured_ns,
        "explicit_time_ns": explicit_ns,
        "full_time_ns": full_ns,
        "domain_fraction_inspected": len(structured.rows) / max(1, len(instance.challengers)),
        "grid_baseline": grid_records,
        "chebyshev": cheb,
        "instance_digest": instance.digest(),
        "protocol_sha256": PROTOCOL_SHA256,
    }
    return record, profile_rows


def build_correctness_cases() -> list[tuple[str, FiniteInstance, Any, str, str]]:
    cases: list[tuple[str, FiniteInstance, Any, str, str]] = []
    explicit_cfg = PROTOCOL["correctness_corpus"]["explicit"]
    for p in explicit_cfg["objectives"]:
        for class_name in explicit_cfg["classes"]:
            for seed in explicit_cfg["seeds"]:
                instance = explicit_profile_instance(p, class_name, seed)
                cases.append((instance.identifier, instance, ExplicitOracle(instance), class_name, "explicit"))
    assignment_cfg = PROTOCOL["correctness_corpus"]["assignment"]
    for cfg in assignment_cfg["cases"]:
        data = random_assignment_data(assignment_cfg["size"], cfg["p"], cfg["seed"])
        instance = data.to_finite_instance()
        cases.append((data.identifier, instance, AssignmentOracle(data), cfg["class"], "assignment"))
    path_cfg = PROTOCOL["correctness_corpus"]["layered_shortest_path"]
    for cfg in path_cfg["cases"]:
        data = random_layered_path_data(path_cfg["width"], path_cfg["internal_layers"], cfg["p"], cfg["seed"])
        instance = data.to_finite_instance()
        cases.append((data.identifier, instance, LayeredPathOracle(data), cfg["class"], "layered_shortest_path"))
    return cases


def quantiles_ns(values: list[int]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)
    def at(fraction: float) -> float:
        position = fraction * (n - 1)
        lo = math.floor(position)
        hi = math.ceil(position)
        if lo == hi:
            return float(ordered[lo])
        return ordered[lo] * (hi - position) + ordered[hi] * (position - lo)
    q1 = at(0.25)
    q3 = at(0.75)
    return {
        "median_ns": at(0.5),
        "q1_ns": q1,
        "q3_ns": q3,
        "iqr_ns": q3 - q1,
    }


def time_callable(function: Callable[[], Any], warmups: int, repetitions: int) -> tuple[dict[str, float], Any]:
    result = None
    for _ in range(warmups):
        result = function()
    values: list[int] = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        result = function()
        values.append(time.perf_counter_ns() - start)
    return quantiles_ns(values), result


def run_timing(cases_by_id: dict[str, tuple[FiniteInstance, Any]]) -> list[dict[str, Any]]:
    config = PROTOCOL["timing"]
    output: list[dict[str, Any]] = []
    for case_id in config["cases"]:
        instance, structured_oracle = cases_by_id[case_id]
        structured_stats, structured_result = time_callable(
            lambda: minimum_budget_row_generation(structured_oracle),
            config["warmups"],
            config["repetitions"],
        )
        full_stats, full_result = time_callable(
            lambda: full_domain_minimum_budget(instance),
            config["warmups"],
            config["repetitions"],
        )
        output.append(
            {
                "case_id": case_id,
                "family": instance.family,
                "p": instance.p,
                "alternatives": len(instance.alternatives),
                "class": classify_minimum_budget(structured_result),
                "structured_median_ns": structured_stats["median_ns"],
                "structured_q1_ns": structured_stats["q1_ns"],
                "structured_q3_ns": structured_stats["q3_ns"],
                "structured_iqr_ns": structured_stats["iqr_ns"],
                "full_median_ns": full_stats["median_ns"],
                "full_q1_ns": full_stats["q1_ns"],
                "full_q3_ns": full_stats["q3_ns"],
                "full_iqr_ns": full_stats["iqr_ns"],
                "speed_ratio_full_over_structured": full_stats["median_ns"] / structured_stats["median_ns"],
                "oracle_calls": structured_result.oracle_calls,
                "rows": len(structured_result.rows),
            }
        )
    return output


def run_scaling() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cfg in PROTOCOL["scaling_corpus"]["assignment"]:
        start = time.perf_counter_ns()
        data = random_assignment_data(cfg["n"], cfg["p"], cfg["seed"])
        generation_ns = time.perf_counter_ns() - start
        oracle = AssignmentOracle(data)
        start = time.perf_counter_ns()
        result = minimum_budget_row_generation(oracle)
        solve_ns = time.perf_counter_ns() - start
        domain_size = math.factorial(cfg["n"])
        rows.append(
            {
                "case_id": data.identifier,
                "family": "assignment",
                "p": cfg["p"],
                "domain_size": domain_size,
                "class": classify_minimum_budget(result),
                "budget": fraction_or_none(result.budget),
                "oracle_calls": result.oracle_calls,
                "retained_rows": len(result.rows),
                "fraction_inspected": len(result.rows) / domain_size,
                "instance_generation_ns": generation_ns,
                "structured_solve_ns": solve_ns,
            }
        )
    for cfg in PROTOCOL["scaling_corpus"]["layered_shortest_path"]:
        start = time.perf_counter_ns()
        data = random_layered_path_data(cfg["width"], cfg["internal_layers"], cfg["p"], cfg["seed"])
        generation_ns = time.perf_counter_ns() - start
        oracle = LayeredPathOracle(data)
        start = time.perf_counter_ns()
        result = minimum_budget_row_generation(oracle)
        solve_ns = time.perf_counter_ns() - start
        domain_size = cfg["width"] ** cfg["internal_layers"]
        rows.append(
            {
                "case_id": data.identifier,
                "family": "layered_shortest_path",
                "p": cfg["p"],
                "domain_size": domain_size,
                "class": classify_minimum_budget(result),
                "budget": fraction_or_none(result.budget),
                "oracle_calls": result.oracle_calls,
                "retained_rows": len(result.rows),
                "fraction_inspected": len(result.rows) / domain_size,
                "instance_generation_ns": generation_ns,
                "structured_solve_ns": solve_ns,
            }
        )
    return rows


def make_figures(correctness: list[dict[str, Any]], profiles: list[dict[str, Any]], timing: list[dict[str, Any]], scaling: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    fractions = [row["domain_fraction_inspected"] for row in correctness if row["family"] != "explicit"]
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.hist(fractions, bins=12)
    ax.set_xlabel("Fraction of challenger outcomes retained")
    ax.set_ylabel("Cases")
    ax.set_title("Structured row generation versus complete domains")
    fig.tight_layout()
    fig.savefig(FIGURES / "row_fraction.png", dpi=240, metadata={})
    plt.close(fig)

    ratios = [row["speed_ratio_full_over_structured"] for row in timing]
    labels = [row["case_id"] for row in timing]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar(range(len(ratios)), ratios)
    ax.axhline(1.0, linewidth=1)
    ax.set_yscale("log")
    ax.set_ylabel("Full-domain / structured median time")
    ax.set_xticks(range(len(labels)), [str(i + 1) for i in range(len(labels))])
    ax.set_title("Natural full-domain baseline")
    fig.tight_layout()
    fig.savefig(FIGURES / "timing_ratio.png", dpi=240, metadata={})
    plt.close(fig)

    cheb_ratios = []
    for row in correctness:
        ratio = row["chebyshev"]["ratio"]
        if ratio is not None:
            cheb_ratios.append(float(Fraction(ratio)))
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.hist(cheb_ratios, bins=15)
    ax.set_xlabel("Exact upper threshold / conservative bound")
    ax.set_ylabel("Cases")
    ax.set_title("Conservatism of the former augmentation bound")
    fig.tight_layout()
    fig.savefig(FIGURES / "chebyshev_ratio.png", dpi=240, metadata={})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    for family in sorted({row["family"] for row in scaling}):
        selected = [row for row in scaling if row["family"] == family]
        ax.scatter(
            [row["domain_size"] for row in selected],
            [row["structured_solve_ns"] / 1e6 for row in selected],
            label=family,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Implicit domain size")
    ax.set_ylabel("Structured solve time (ms)")
    ax.legend()
    ax.set_title("Structured-oracle scaling")
    fig.tight_layout()
    fig.savefig(FIGURES / "structured_scaling.png", dpi=240, metadata={})
    plt.close(fig)


def main() -> int:
    correctness_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    cases_by_id: dict[str, tuple[FiniteInstance, Any]] = {}
    failures: list[str] = []
    for case_id, instance, oracle, expected_class, family in build_correctness_cases():
        try:
            record, profiles = run_case(case_id, instance, oracle, expected_class, family)
            correctness_rows.append(record)
            profile_rows.extend(profiles)
            cases_by_id[case_id] = (instance, oracle)
            if not record["classification_agreement"]:
                failures.append(f"{case_id}: classification disagreement")
            if not record["budget_agreement"]:
                failures.append(f"{case_id}: budget disagreement")
            if not record["scale_invariant"]:
                failures.append(f"{case_id}: scaling invariance failure")
            if any(not row["agreement"] for row in profiles):
                failures.append(f"{case_id}: profile disagreement")
            cheb = record["chebyshev"]
            if cheb["tie_at_upper"] is False or cheb["failure_above_upper"] is False:
                failures.append(f"{case_id}: Chebyshev threshold failure")
        except Exception as exc:
            failures.append(f"{case_id}: {type(exc).__name__}: {exc}")

    timing_rows = run_timing(cases_by_id)
    scaling_rows = run_scaling()

    correctness_fields = [
        "case_id", "family", "p", "m", "alternatives", "expected_class", "observed_class",
        "structured_status", "structured_budget", "structured_margin", "structured_oracle_calls",
        "structured_rows", "explicit_status", "explicit_budget", "explicit_oracle_calls", "full_status",
        "full_budget", "classification_agreement", "budget_agreement", "scale_invariant",
        "structured_time_ns", "explicit_time_ns", "full_time_ns", "domain_fraction_inspected",
        "instance_digest", "protocol_sha256"
    ]
    write_csv(RAW / "correctness_cases.csv", correctness_rows, correctness_fields)
    write_csv(
        RAW / "profile_cases.csv",
        profile_rows,
        ["case_id", "family", "p", "budget", "full_value", "structured_value", "explicit_value", "agreement", "structured_oracle_calls", "structured_rows"],
    )
    write_csv(
        RAW / "timing_cases.csv",
        timing_rows,
        list(timing_rows[0].keys()) if timing_rows else [],
    )
    write_csv(
        RAW / "scaling_cases.csv",
        scaling_rows,
        list(scaling_rows[0].keys()) if scaling_rows else [],
    )
    for row in correctness_rows:
        write_json(RAW / "cases" / f"{row['case_id']}.json", row)

    cheb_ratios = [
        Fraction(row["chebyshev"]["ratio"])
        for row in correctness_rows
        if row["chebyshev"]["ratio"] is not None
    ]
    grid_exact_hits = sum(
        1
        for row in correctness_rows
        for record in row["grid_baseline"].values()
        if record["exact_hit"]
    )
    grid_trials = sum(len(row["grid_baseline"]) for row in correctness_rows)
    structured_cases = [row for row in correctness_rows if row["family"] != "explicit"]
    summary = {
        "schema": "mmor-verification-profile-study-summary-1.0",
        "software_version": __version__,
        "protocol_sha256": PROTOCOL_SHA256,
        "correctness_cases": len(correctness_rows),
        "classification_agreements": sum(bool(row["classification_agreement"]) for row in correctness_rows),
        "budget_agreements": sum(bool(row["budget_agreement"]) for row in correctness_rows),
        "scale_invariance_agreements": sum(bool(row["scale_invariant"]) for row in correctness_rows),
        "profile_points": len(profile_rows),
        "profile_agreements": sum(bool(row["agreement"]) for row in profile_rows),
        "class_counts": {
            class_name: sum(row["observed_class"] == class_name for row in correctness_rows)
            for class_name in ("harmless", "repairable", "irreparable")
        },
        "structured_cases": len(structured_cases),
        "max_structured_oracle_calls": max(row["structured_oracle_calls"] for row in structured_cases),
        "median_structured_domain_fraction": statistics.median(row["domain_fraction_inspected"] for row in structured_cases),
        "max_structured_domain_fraction": max(row["domain_fraction_inspected"] for row in structured_cases),
        "chebyshev_finite_ratios": len(cheb_ratios),
        "chebyshev_median_exact_to_conservative": float(statistics.median(cheb_ratios)) if cheb_ratios else None,
        "chebyshev_max_exact_to_conservative": float(max(cheb_ratios)) if cheb_ratios else None,
        "grid_trials": grid_trials,
        "grid_exact_hits": grid_exact_hits,
        "timing_cases": len(timing_rows),
        "timing_median_full_over_structured": statistics.median(row["speed_ratio_full_over_structured"] for row in timing_rows),
        "timing_min_full_over_structured": min(row["speed_ratio_full_over_structured"] for row in timing_rows),
        "timing_max_full_over_structured": max(row["speed_ratio_full_over_structured"] for row in timing_rows),
        "scaling_cases": len(scaling_rows),
        "scaling_max_domain_size": max(row["domain_size"] for row in scaling_rows),
        "failure_count": len(failures),
        "failures": failures,
        "independent_physical_machine_replication": False,
        "status": "PASS" if not failures else "FAIL",
    }
    write_json(PROCESSED / "study_summary.json", summary)
    write_json(VALIDATION / "study_failures.json", {"failures": failures})
    make_figures(correctness_rows, profile_rows, timing_rows, scaling_rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
