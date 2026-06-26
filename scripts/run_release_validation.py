#!/usr/bin/env python3
"""Validate the computational distribution and retained exact evidence."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from mmor_certificates import __version__

VERSION = "2.0.0"
VALIDATION = ROOT / "validation"
PROTOCOL = ROOT / "protocol" / "COMPUTATIONAL_PROTOCOL.json"
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_checker():
    path = ROOT / "checker" / "verify_profile_object.py"
    spec = importlib.util.spec_from_file_location("mmor_standalone_checker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("standalone checker could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata_validation() -> dict[str, Any]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    zenodo = load_json(ROOT / ".zenodo.json")
    codemeta = load_json(ROOT / "codemeta.json")
    protocol = load_json(PROTOCOL)
    checks = {
        "package_version": project["project"]["version"] == VERSION,
        "runtime_version": __version__ == VERSION,
        "citation_version": str(citation["version"]) == VERSION,
        "zenodo_version": str(zenodo["version"]) == VERSION,
        "codemeta_version": str(codemeta["version"]) == VERSION,
        "protocol_version": protocol["software_version"] == VERSION,
        "protocol_digest": (ROOT / "protocol/COMPUTATIONAL_PROTOCOL.sha256").read_text(encoding="utf-8").strip() == PROTOCOL_SHA256,
        "source_licence": project["project"]["license"]["text"] == citation["license"] == "BSD-3-Clause" and zenodo["license"] == "bsd-3-clause",
        "release_identifier_absent": "doi" not in citation and "doi" not in zenodo,
        "email_absent": "@" not in json.dumps({"project": project["project"].get("authors"), "citation": citation["authors"], "zenodo": zenodo["creators"]}),
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    return {"schema": "mmor-metadata-validation-1.0", "checks": checks, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def schema_validation() -> dict[str, Any]:
    schemas = {
        "instances": jsonschema.Draft202012Validator(load_json(ROOT / "schemas/instance.schema.json")),
        "certificates": jsonschema.Draft202012Validator(load_json(ROOT / "schemas/minimum_budget_certificate.schema.json")),
        "profiles": jsonschema.Draft202012Validator(load_json(ROOT / "schemas/profile_record.schema.json")),
    }
    counts = {key: 0 for key in schemas}
    failures: list[str] = []
    for key, validator in schemas.items():
        for path in sorted((ROOT / "results" / key).glob("*.json")):
            try:
                validator.validate(load_json(path))
                counts[key] += 1
            except Exception as exc:
                failures.append(f"{path.relative_to(ROOT).as_posix()}: {type(exc).__name__}: {exc}")
    expected = {"instances": 84, "certificates": 84, "profiles": 196}
    if counts != expected:
        failures.append(f"object counts {counts}, expected {expected}")
    return {"schema": "mmor-json-schema-validation-1.0", "counts": counts, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def checker_replay(fast: bool) -> dict[str, Any]:
    checker = load_checker()
    certificate_paths = sorted((ROOT / "results/certificates").glob("*.json"))
    profile_paths = sorted((ROOT / "results/profiles").glob("*.json"))
    if fast:
        certificate_paths = certificate_paths[::7][:12]
        profile_paths = profile_paths[::17][:12]
    failures: list[str] = []
    class_counts = {"harmless": 0, "repairable": 0, "irreparable": 0}
    for path in certificate_paths:
        try:
            payload = load_json(path)
            instance = load_json(ROOT / "results/instances" / f"{payload['case_id']}.json")
            report = checker.verify_minimum_budget(instance, payload)
            class_counts[report["classification"]] += 1
        except Exception as exc:
            failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
    for path in profile_paths:
        try:
            payload = load_json(path)
            instance = load_json(ROOT / "results/instances" / f"{payload['case_id']}.json")
            checker.verify_profile(instance, payload)
        except Exception as exc:
            failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
    # Separate-process boundary on representative harmless, repairable, irreparable and profile objects.
    cli_objects = [
        ("explicit-p2-harmless-s101", "results/certificates/explicit-p2-harmless-s101.json"),
        ("explicit-p2-repairable-s101", "results/certificates/explicit-p2-repairable-s101.json"),
        ("explicit-p2-irreparable-s101", "results/certificates/explicit-p2-irreparable-s101.json"),
        ("explicit-p2-repairable-s101", "results/profiles/explicit-p2-repairable-s101-b0.json"),
    ]
    for case_id, relative in cli_objects:
        proc = subprocess.run(
            [sys.executable, "checker/verify_profile_object.py", "--instance", f"results/instances/{case_id}.json", "--object", relative],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            failures.append(f"process replay {relative}: {proc.stdout}{proc.stderr}")
    return {
        "schema": "mmor-standalone-replay-1.0",
        "mode": "fast" if fast else "complete",
        "certificates": len(certificate_paths),
        "profiles": len(profile_paths),
        "classification_counts": class_counts,
        "process_boundary_cases": len(cli_objects),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def mutation_validation() -> dict[str, Any]:
    checker = load_checker()
    repair = load_json(ROOT / "results/certificates/explicit-p2-repairable-s101.json")
    irreparable = load_json(ROOT / "results/certificates/explicit-p2-irreparable-s101.json")
    profile = load_json(ROOT / "results/profiles/explicit-p2-repairable-s101-b0.json")
    instance_repair = load_json(ROOT / "results/instances/explicit-p2-repairable-s101.json")
    instance_irrep = load_json(ROOT / "results/instances/explicit-p2-irreparable-s101.json")
    mutations: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []

    def add(name, kind, base, instance, mutate):
        obj = deepcopy(base)
        mutate(obj)
        mutations.append((name, kind, obj, instance))

    add("certificate_digest", "certificate", repair, instance_repair, lambda o: o.__setitem__("instance_digest", "sha256:" + "0" * 64))
    add("certificate_budget", "certificate", repair, instance_repair, lambda o: o["result"].__setitem__("budget", "3/2"))
    add("parameter_budget", "certificate", repair, instance_repair, lambda o: o["result"]["parameters"].__setitem__("budget", "3/2"))
    add("weight_sum", "certificate", repair, instance_repair, lambda o: o["result"]["parameters"]["weights"].__setitem__(0, "3/4"))
    add("negative_multiplier", "certificate", repair, instance_repair, lambda o: o["result"]["parameters"]["multipliers"].__setitem__(0, "-1/2"))
    add("margin", "certificate", repair, instance_repair, lambda o: o["result"].__setitem__("margin", "1"))
    add("master_objective", "certificate", repair, instance_repair, lambda o: o["result"]["master_certificate"].__setitem__("objective", "3/2"))
    add("master_point", "certificate", repair, instance_repair, lambda o: o["result"]["master_certificate"]["point"].__setitem__(0, "3/4"))
    add("master_multiplier", "certificate", repair, instance_repair, lambda o: o["result"]["master_certificate"]["inequality_multipliers"].__setitem__(0, "3"))
    add("challenger_id", "certificate", repair, instance_repair, lambda o: o["result"]["challenger_ids"].__setitem__(0, "absent"))
    add("classification", "certificate", repair, instance_repair, lambda o: o.__setitem__("classification", "harmless"))
    add("noncanonical_rational", "certificate", repair, instance_repair, lambda o: o["result"]["parameters"]["weights"].__setitem__(0, "2/4"))

    add("stress_zero_depth", "certificate", irreparable, instance_irrep, lambda o: o["result"]["stress_witness"].__setitem__("depth", "0"))
    add("stress_sum", "certificate", irreparable, instance_irrep, lambda o: o["result"]["stress_witness"]["coefficients"].__setitem__(0, "3/4"))
    add("stress_negative", "certificate", irreparable, instance_irrep, lambda o: o["result"]["stress_witness"]["coefficients"].__setitem__(0, "-1/2"))
    add("stress_id", "certificate", irreparable, instance_irrep, lambda o: o["result"]["stress_witness"]["challenger_ids"].__setitem__(0, "absent"))
    add("irreparable_class", "certificate", irreparable, instance_irrep, lambda o: o.__setitem__("classification", "repairable"))
    add("irreparable_digest", "certificate", irreparable, instance_irrep, lambda o: o.__setitem__("instance_digest", "sha256:" + "f" * 64))

    add("profile_value", "profile", profile, instance_repair, lambda o: o["result"].__setitem__("value", "0"))
    add("profile_budget", "profile", profile, instance_repair, lambda o: o["result"].__setitem__("budget", "1/10"))
    add("profile_weight", "profile", profile, instance_repair, lambda o: o["result"]["parameters"]["weights"].__setitem__(0, "3/4"))
    add("profile_master_objective", "profile", profile, instance_repair, lambda o: o["result"]["master_certificate"].__setitem__("objective", "0"))
    add("profile_active_row", "profile", profile, instance_repair, lambda o: o["result"]["master_certificate"]["active_rows"].__setitem__(0, 999))
    add("profile_challenger", "profile", profile, instance_repair, lambda o: o["result"]["challenger_ids"].__setitem__(0, "absent"))

    accepted: list[str] = []
    rejected = 0
    for name, kind, payload, instance in mutations:
        try:
            if kind == "certificate":
                checker.verify_minimum_budget(instance, payload)
            else:
                checker.verify_profile(instance, payload)
            accepted.append(name)
        except Exception:
            rejected += 1
    return {
        "schema": "mmor-semantic-mutation-validation-1.0",
        "mutations": len(mutations),
        "rejected": rejected,
        "incorrectly_accepted": accepted,
        "status": "PASS" if rejected == len(mutations) else "FAIL",
    }


def unit_tests() -> dict[str, Any]:
    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(SRC)
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    count = 0
    for line in proc.stderr.splitlines() + proc.stdout.splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except Exception:
                pass
    return {"schema": "mmor-unit-test-summary-1.0", "exit_code": proc.returncode, "tests": count, "status": "PASS" if proc.returncode == 0 else "FAIL", "output": proc.stdout + proc.stderr if proc.returncode else ""}


def import_boundary() -> dict[str, Any]:
    path = ROOT / "checker/verify_profile_object.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    nonstandard = sorted(name for name in imports if name not in sys.stdlib_module_names and name != "__future__")
    return {"schema": "mmor-checker-import-boundary-1.0", "imports": sorted(imports), "nonstandard": nonstandard, "status": "PASS" if not nonstandard and "mmor_certificates" not in imports else "FAIL"}


def retained_summary() -> dict[str, Any]:
    summary = load_json(ROOT / "results/processed/study_summary.json")
    checks = {
        "software_version": summary.get("software_version") == VERSION,
        "protocol": summary.get("protocol_sha256") == PROTOCOL_SHA256,
        "classifications": (summary.get("classification_agreements"), summary.get("correctness_cases")) == (84, 84),
        "budgets": summary.get("budget_agreements") == 84,
        "profiles": (summary.get("profile_agreements"), summary.get("profile_points")) == (196, 196),
        "scale_invariance": summary.get("scale_invariance_agreements") == 84,
        "balanced_classes": summary.get("class_counts") == {"harmless": 28, "repairable": 28, "irreparable": 28},
        "no_failures": summary.get("failure_count") == 0,
        "study_status": summary.get("status") == "PASS",
        "independent_replication_not_claimed": summary.get("independent_physical_machine_replication") is False,
        "numeric_scaling": summary.get("numeric_scaling_baseline_cases") == 8 and summary.get("numeric_scaling_min_full_over_structured", 0) > 1,
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    return {"schema": "mmor-retained-evidence-validation-1.0", "checks": checks, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def distribution_validation() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("mmor_distribution_validation", ROOT / "scripts/validate_distribution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("tree scan could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scan(ROOT)


def wheel_smoke_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="mmor-wheel-") as tmp:
        tmp_path = Path(tmp)
        build_dir = tmp_path / "wheel"
        build_dir.mkdir()
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", ".", "-w", str(build_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        wheels = list(build_dir.glob("*.whl"))
        failures: list[str] = []
        if proc.returncode != 0 or len(wheels) != 1:
            failures.append(proc.stdout + proc.stderr)
        else:
            import zipfile
            with zipfile.ZipFile(wheels[0]) as archive:
                metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
                metadata = archive.read(metadata_name).decode("utf-8")
                if "Version: 2.0.0" not in metadata:
                    failures.append("wheel metadata version mismatch")
                if "@" in metadata:
                    failures.append("wheel metadata contains contact address")
        return {"schema": "mmor-wheel-smoke-1.0", "wheel_count": len(wheels), "failures": failures, "status": "PASS" if not failures else "FAIL"}


def remove_transient() -> None:
    for path in sorted(ROOT.rglob("*"), reverse=True):
        if path.is_dir() and (path.name in {"__pycache__", ".pytest_cache", "build", "dist"} or path.name.endswith(".egg-info")):
            shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob("*.pyc"):
        path.unlink(missing_ok=True)


def write_manifest() -> dict[str, Any]:
    excluded = {"FILE_MANIFEST.sha256", "manifest_summary.json"}
    lines: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in {".git", ".venv", "venv", "__pycache__", "build", "dist"} for part in path.parts) or path.name in excluded:
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}")
    manifest = VALIDATION / "FILE_MANIFEST.sha256"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"schema": "mmor-file-manifest-summary-1.0", "files": len(lines), "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(), "status": "PASS"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    VALIDATION.mkdir(parents=True, exist_ok=True)
    remove_transient()
    results = {
        "metadata": metadata_validation(),
        "schemas": schema_validation(),
        "replay": checker_replay(args.fast),
        "mutations": mutation_validation(),
        "tests": unit_tests(),
        "checker_imports": import_boundary(),
        "retained_evidence": retained_summary(),
        "distribution": distribution_validation(),
    }
    if not args.fast:
        results["wheel"] = wheel_smoke_test()
    for name, payload in results.items():
        write_json(VALIDATION / f"{name}.json", payload)
    remove_transient()
    # Scan again after all validation summaries have been written.
    results["distribution"] = distribution_validation()
    write_json(VALIDATION / "distribution.json", results["distribution"])
    statuses = {name: payload["status"] for name, payload in results.items()}
    validation_record = {
        "schema": "mmor-release-validation-1.0",
        "software_version": VERSION,
        "mode": "fast" if args.fast else "complete",
        "components": statuses,
        "external_boundaries": {
            "hosted_cross_platform_ci": "CONFIGURED_NOT_ARCHIVED",
            "independent_physical_machine": "NOT_CLAIMED",
            "priority_search": "TARGETED_SEARCH_COMPLETED_NOT_EXHAUSTIVE"
        },
        "status": "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL",
    }
    write_json(VALIDATION / "release_validation.json", validation_record)
    manifest = write_manifest()
    write_json(VALIDATION / "manifest_summary.json", manifest)
    manifest = write_manifest()
    output = {**validation_record, "manifest": manifest}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if validation_record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
