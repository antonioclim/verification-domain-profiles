#!/usr/bin/env python3
"""Standalone exact checker for retained MMOR verification-profile objects.

The checker uses only the Python standard library. It verifies explicit finite
instances, minimum-budget certificates and fixed-budget profile records with
exact rational arithmetic. It does not import the generator package and does
not invoke an optimiser.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

MAX_BYTES = 50 * 1024 * 1024


class Rejected(ValueError):
    pass


def reject(code: str, message: str) -> None:
    raise Rejected(f"{code}: {message}")


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            reject("JSON_DUPLICATE_KEY", key)
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.stat().st_size > MAX_BYTES:
        reject("FILE_SIZE", f"{path.name} exceeds {MAX_BYTES} bytes")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_pairs,
            parse_constant=lambda token: reject("JSON_CONSTANT", token),
        )
    except UnicodeDecodeError as exc:
        reject("UTF8", str(exc))
    except json.JSONDecodeError as exc:
        reject("JSON", str(exc))


def q(value: Any) -> Fraction:
    if isinstance(value, bool):
        reject("RATIONAL", "boolean is not a rational")
    if isinstance(value, int):
        return Fraction(value)
    if not isinstance(value, str):
        reject("RATIONAL", f"expected integer or rational string, observed {type(value).__name__}")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        reject("RATIONAL", str(exc))
    canonical = str(result.numerator) if result.denominator == 1 else f"{result.numerator}/{result.denominator}"
    if value != canonical:
        reject("RATIONAL_CANONICAL", f"{value!r} should be {canonical!r}")
    return result


def dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    if len(a) != len(b):
        reject("DIMENSION", "dot-product dimension mismatch")
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def canonical_instance_digest(instance: dict[str, Any]) -> str:
    payload = {
        "identifier": instance["identifier"],
        "candidate_id": instance["candidate_id"],
        "family": instance["family"],
        "objective_scales": instance["objective_scales"],
        "constraint_scales": instance["constraint_scales"],
        "alternatives": [
            {
                "identifier": alt["identifier"],
                "objectives": alt["objectives"],
                "constraints": alt["constraints"],
                "decision": alt["decision"],
            }
            for alt in instance["alternatives"]
        ],
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def validate_instance(instance: dict[str, Any]) -> tuple[int, int, dict[str, dict[str, Any]], dict[str, Any]]:
    required = {
        "schema", "identifier", "family", "candidate_id", "objective_scales",
        "constraint_scales", "digest", "alternatives", "metadata",
    }
    if set(instance) != required:
        reject("INSTANCE_FIELDS", f"observed fields {sorted(instance)}")
    if instance["schema"] != "mmor-verification-instance-1.0":
        reject("INSTANCE_SCHEMA", str(instance["schema"]))
    scales_d = instance["objective_scales"]
    scales_h = instance["constraint_scales"]
    if not isinstance(scales_d, list) or len(scales_d) < 2 or any(not isinstance(v, int) or v <= 0 for v in scales_d):
        reject("OBJECTIVE_SCALES", "objective scales must be positive integers")
    if not isinstance(scales_h, list) or any(not isinstance(v, int) or v <= 0 for v in scales_h):
        reject("CONSTRAINT_SCALES", "constraint scales must be positive integers")
    p, m = len(scales_d), len(scales_h)
    alternatives = instance["alternatives"]
    if not isinstance(alternatives, list) or not alternatives:
        reject("ALTERNATIVES", "non-empty list required")
    lookup: dict[str, dict[str, Any]] = {}
    for alt in alternatives:
        if set(alt) != {"identifier", "objectives", "constraints", "decision"}:
            reject("ALTERNATIVE_FIELDS", str(alt.get("identifier", "?")))
        identifier = alt["identifier"]
        if not isinstance(identifier, str) or not identifier or identifier in lookup:
            reject("ALTERNATIVE_ID", repr(identifier))
        if not isinstance(alt["objectives"], list) or len(alt["objectives"]) != p or any(not isinstance(v, int) for v in alt["objectives"]):
            reject("OBJECTIVE_VECTOR", identifier)
        if not isinstance(alt["constraints"], list) or len(alt["constraints"]) != m or any(not isinstance(v, int) for v in alt["constraints"]):
            reject("CONSTRAINT_VECTOR", identifier)
        lookup[identifier] = alt
    candidate_id = instance["candidate_id"]
    if candidate_id not in lookup:
        reject("CANDIDATE", "candidate identifier absent")
    candidate = lookup[candidate_id]
    if any(candidate["constraints"]):
        reject("CANDIDATE_ACTIVITY", "candidate active-constraint differences must be zero")
    digest = canonical_instance_digest(instance)
    if digest != instance["digest"]:
        reject("INSTANCE_DIGEST", f"expected {digest}, observed {instance['digest']}")
    return p, m, lookup, candidate


def rows_from_instance(
    instance: dict[str, Any], lookup: dict[str, dict[str, Any]], candidate: dict[str, Any]
) -> dict[str, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]]:
    scales_d = instance["objective_scales"]
    scales_h = instance["constraint_scales"]
    result: dict[str, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = {}
    for identifier, alt in lookup.items():
        if identifier == instance["candidate_id"]:
            continue
        d = tuple(Fraction(v - b, s) for v, b, s in zip(alt["objectives"], candidate["objectives"], scales_d))
        h = tuple(Fraction(v, s) for v, s in zip(alt["constraints"], scales_h))
        row = (d, h)
        result[identifier] = row
        decision = alt.get("decision")
        if instance["family"] == "assignment" and isinstance(decision, list):
            result["perm:" + ",".join(str(v) for v in decision)] = row
        elif instance["family"] == "layered_shortest_path" and isinstance(decision, list):
            result["path:" + "|".join(str(v) for v in decision)] = row
    return result


def parse_parameters(payload: dict[str, Any], p: int, m: int) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...], Fraction]:
    if not isinstance(payload, dict) or set(payload) != {"weights", "multipliers", "budget"}:
        reject("PARAMETER_FIELDS", "weights, multipliers and budget required")
    weights = tuple(q(v) for v in payload["weights"])
    multipliers = tuple(q(v) for v in payload["multipliers"])
    budget = q(payload["budget"])
    if len(weights) != p or len(multipliers) != m:
        reject("PARAMETER_DIMENSION", "weight or multiplier dimension mismatch")
    if any(v < 0 for v in weights + multipliers):
        reject("PARAMETER_SIGN", "parameters must be non-negative")
    if sum(weights, Fraction(0)) != 1:
        reject("WEIGHT_SIMPLEX", "weights do not sum to one")
    if sum(multipliers, Fraction(0)) != budget:
        reject("BUDGET", "budget does not equal multiplier sum")
    return weights, multipliers, budget


def score(weights: Sequence[Fraction], multipliers: Sequence[Fraction], row: tuple[tuple[Fraction, ...], tuple[Fraction, ...]]) -> Fraction:
    d, h = row
    return dot(weights, d) + dot(multipliers, h)


def build_minimum_master(
    challenger_ids: Sequence[str], rows: dict[str, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]], p: int, m: int
) -> tuple[list[tuple[tuple[Fraction, ...], Fraction]], list[tuple[tuple[Fraction, ...], Fraction]], tuple[Fraction, ...]]:
    nvar = p + m
    inequalities: list[tuple[tuple[Fraction, ...], Fraction]] = []
    for identifier in challenger_ids:
        if identifier not in rows:
            reject("CHALLENGER_ID", identifier)
        d, h = rows[identifier]
        inequalities.append((d + h, Fraction(0)))
    for i in range(nvar):
        row = [Fraction(0)] * nvar
        row[i] = Fraction(1)
        inequalities.append((tuple(row), Fraction(0)))
    equality = (tuple([Fraction(1)] * p + [Fraction(0)] * m), Fraction(1))
    objective = tuple([Fraction(0)] * p + [Fraction(1)] * m)
    return inequalities, [equality], objective


def build_profile_master(
    challenger_ids: Sequence[str], rows: dict[str, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]], p: int, m: int, budget: Fraction
) -> tuple[list[tuple[tuple[Fraction, ...], Fraction]], list[tuple[tuple[Fraction, ...], Fraction]], tuple[Fraction, ...]]:
    nvar = p + m + 1
    inequalities: list[tuple[tuple[Fraction, ...], Fraction]] = []
    for identifier in challenger_ids:
        if identifier not in rows:
            reject("CHALLENGER_ID", identifier)
        d, h = rows[identifier]
        inequalities.append((d + h + (Fraction(-1),), Fraction(0)))
    for i in range(p + m):
        row = [Fraction(0)] * nvar
        row[i] = Fraction(1)
        inequalities.append((tuple(row), Fraction(0)))
    budget_row = [Fraction(0)] * nvar
    for j in range(m):
        budget_row[p + j] = Fraction(-1)
    inequalities.append((tuple(budget_row), -budget))
    equality = (tuple([Fraction(1)] * p + [Fraction(0)] * (m + 1)), Fraction(1))
    # The generator solves maximisation by certifying minimisation of -gamma.
    objective = tuple([Fraction(0)] * (p + m) + [Fraction(-1)])
    return inequalities, [equality], objective


def verify_kkt(
    payload: dict[str, Any],
    inequalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    equalities: Sequence[tuple[Sequence[Fraction], Fraction]],
    objective: Sequence[Fraction],
    expected_point: Sequence[Fraction],
    expected_reported_objective: Fraction,
    *,
    maximise: bool,
) -> None:
    required = {"status", "objective", "point", "active_rows", "inequality_multipliers", "equality_multipliers"}
    if not isinstance(payload, dict) or set(payload) != required:
        reject("KKT_FIELDS", f"observed {sorted(payload) if isinstance(payload, dict) else type(payload).__name__}")
    if payload["status"] != "OPTIMAL":
        reject("KKT_STATUS", str(payload["status"]))
    point = tuple(q(v) for v in payload["point"])
    if point != tuple(expected_point):
        reject("KKT_POINT", "master point differs from reported parameters")
    reported = q(payload["objective"])
    if reported != expected_reported_objective:
        reject("KKT_OBJECTIVE", f"expected {expected_reported_objective}, observed {reported}")
    if any(dot(row, point) < rhs for row, rhs in inequalities):
        reject("KKT_PRIMAL", "inequality infeasibility")
    if any(dot(row, point) != rhs for row, rhs in equalities):
        reject("KKT_PRIMAL", "equality infeasibility")
    active = payload["active_rows"]
    if not isinstance(active, list) or any(not isinstance(v, int) or v < 0 or v >= len(inequalities) for v in active):
        reject("KKT_ACTIVE", "invalid active-row index")
    if len(active) != len(set(active)):
        reject("KKT_ACTIVE", "duplicate active-row index")
    y = tuple(q(v) for v in payload["inequality_multipliers"])
    beta = tuple(q(v) for v in payload["equality_multipliers"])
    if len(y) != len(active) or len(beta) != len(equalities) or any(v < 0 for v in y):
        reject("KKT_MULTIPLIERS", "dimension or sign error")
    for index in active:
        row, rhs = inequalities[index]
        if dot(row, point) != rhs:
            reject("KKT_COMPLEMENTARITY", f"row {index} is not tight")
    c = tuple(objective)
    for coordinate in range(len(c)):
        lhs = sum(y_i * inequalities[index][0][coordinate] for y_i, index in zip(y, active))
        lhs -= sum(beta_i * row[coordinate] for beta_i, (row, _) in zip(beta, equalities))
        if lhs != c[coordinate]:
            reject("KKT_STATIONARITY", f"coordinate {coordinate}")
    primal = dot(c, point)
    dual = sum(y_i * inequalities[index][1] for y_i, index in zip(y, active))
    dual -= sum(beta_i * rhs for beta_i, (_, rhs) in zip(beta, equalities))
    if primal != dual:
        reject("KKT_DUALITY", f"primal {primal}, dual {dual}")
    original_objective = -primal if maximise else primal
    if original_objective != reported:
        reject("KKT_REPORTED_OBJECTIVE", f"expected {original_objective}, observed {reported}")


def verify_minimum_budget(instance: dict[str, Any], certificate: dict[str, Any]) -> dict[str, Any]:
    p, m, lookup, candidate = validate_instance(instance)
    if certificate.get("schema") != "mmor-minimum-budget-certificate-1.0":
        reject("CERTIFICATE_SCHEMA", str(certificate.get("schema")))
    required = {"schema", "case_id", "family", "instance_digest", "classification", "result", "protocol_sha256"}
    if set(certificate) != required:
        reject("CERTIFICATE_FIELDS", f"observed {sorted(certificate)}")
    if certificate["instance_digest"] != instance["digest"]:
        reject("CERTIFICATE_DIGEST", "certificate is bound to another instance")
    if certificate["case_id"] != instance["identifier"] or certificate["family"] != instance["family"]:
        reject("CERTIFICATE_ID", "case or family mismatch")
    rows = rows_from_instance(instance, lookup, candidate)
    result = certificate["result"]
    status = result.get("status")
    challenger_ids = result.get("challenger_ids")
    if not isinstance(challenger_ids, list) or len(challenger_ids) != len(set(challenger_ids)):
        reject("CHALLENGERS", "unique challenger list required")
    if status == "IRREPARABLE_DOMAIN":
        if certificate["classification"] != "irreparable":
            reject("CLASSIFICATION", "irreparable status/classification mismatch")
        witness = result.get("stress_witness")
        if not isinstance(witness, dict) or set(witness) != {"depth", "challenger_ids", "coefficients"}:
            reject("STRESS_FIELDS", "invalid stress witness")
        ids = witness["challenger_ids"]
        coeff = tuple(q(v) for v in witness["coefficients"])
        depth = q(witness["depth"])
        if ids != challenger_ids or len(coeff) != len(ids) or any(v < 0 for v in coeff) or sum(coeff, Fraction(0)) != 1 or depth <= 0:
            reject("STRESS", "invalid coefficients or depth")
        for identifier in ids:
            if identifier not in rows:
                reject("STRESS_ID", identifier)
        for i in range(p):
            value = sum(a * rows[identifier][0][i] for a, identifier in zip(coeff, ids))
            if value > -depth:
                reject("STRESS_OBJECTIVE", f"coordinate {i}: {value} > {-depth}")
        for j in range(m):
            value = sum(a * rows[identifier][1][j] for a, identifier in zip(coeff, ids))
            if value > 0:
                reject("STRESS_CONSTRAINT", f"coordinate {j}: {value}")
        return {"status": "VERIFIED", "classification": "irreparable", "depth": str(depth)}
    if status not in {"CERTIFIED_MINIMUM_BUDGET", "STRICTLY_CERTIFIED"}:
        reject("STATUS", str(status))
    weights, multipliers, budget = parse_parameters(result.get("parameters"), p, m)
    if q(result.get("budget")) != budget:
        reject("BUDGET", "reported budget mismatch")
    all_scores = {identifier: score(weights, multipliers, row) for identifier, row in rows.items()}
    minimum = min(all_scores.values(), default=Fraction(0))
    if minimum < 0 or q(result.get("margin")) != minimum:
        reject("GLOBAL_MARGIN", f"reported {result.get('margin')}, recomputed {minimum}")
    expected_class = "harmless" if budget == 0 else "repairable"
    if certificate["classification"] != expected_class:
        reject("CLASSIFICATION", f"expected {expected_class}")
    if budget == 0:
        # The non-negativity of multipliers makes zero a global lower bound.
        pass
    else:
        master = result.get("master_certificate")
        inequalities, equalities, objective = build_minimum_master(challenger_ids, rows, p, m)
        verify_kkt(
            master, inequalities, equalities, objective,
            weights + multipliers, budget, maximise=False,
        )
    return {
        "status": "VERIFIED",
        "classification": expected_class,
        "budget": str(budget),
        "margin": str(minimum),
    }


def verify_profile(instance: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    p, m, lookup, candidate = validate_instance(instance)
    if record.get("schema") != "mmor-profile-record-1.0":
        reject("PROFILE_SCHEMA", str(record.get("schema")))
    required = {"schema", "case_id", "family", "instance_digest", "protocol_sha256", "result"}
    if set(record) != required:
        reject("PROFILE_FIELDS", f"observed {sorted(record)}")
    if record["instance_digest"] != instance["digest"] or record["case_id"] != instance["identifier"] or record["family"] != instance["family"]:
        reject("PROFILE_ID", "instance binding mismatch")
    rows = rows_from_instance(instance, lookup, candidate)
    result = record["result"]
    budget = q(result.get("budget"))
    value = q(result.get("value"))
    weights, multipliers, parameter_budget = parse_parameters(result.get("parameters"), p, m)
    if parameter_budget > budget:
        reject("PROFILE_BUDGET", "multiplier budget exceeds the declared bound")
    all_scores = {identifier: score(weights, multipliers, row) for identifier, row in rows.items()}
    minimum = min(all_scores.values(), default=Fraction(0))
    if minimum != value:
        reject("PROFILE_VALUE", f"reported {value}, recomputed {minimum}")
    challenger_ids = result.get("challenger_ids")
    if not isinstance(challenger_ids, list) or len(challenger_ids) != len(set(challenger_ids)):
        reject("PROFILE_CHALLENGERS", "unique challenger list required")
    point = weights + multipliers + (value,)
    inequalities, equalities, objective = build_profile_master(challenger_ids, rows, p, m, budget)
    verify_kkt(
        result.get("master_certificate"), inequalities, equalities, objective,
        point, value, maximise=True,
    )
    return {"status": "VERIFIED", "budget": str(budget), "value": str(value)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    args = parser.parse_args()
    try:
        instance = load_json(args.instance)
        payload = load_json(args.object)
        if payload.get("schema") == "mmor-minimum-budget-certificate-1.0":
            report = verify_minimum_budget(instance, payload)
        elif payload.get("schema") == "mmor-profile-record-1.0":
            report = verify_profile(instance, payload)
        else:
            reject("OBJECT_SCHEMA", str(payload.get("schema")))
        report["checker"] = {"name": "mmor-profile-standalone-checker", "version": "2.0.1"}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Rejected as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
