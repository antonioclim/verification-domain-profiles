#!/usr/bin/env python3
"""Build and inspect a wheel in an isolated temporary directory."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.0.1"


def remove_transient() -> None:
    for path in sorted(ROOT.rglob("*"), reverse=True):
        if path.is_dir() and (path.name in {"__pycache__", ".pytest_cache", "build", "dist"} or path.name.endswith(".egg-info")):
            shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob("*.pyc"):
        path.unlink(missing_ok=True)


def main() -> int:
    remove_transient()
    with tempfile.TemporaryDirectory(prefix="mmor-wheel-") as tmp:
        wheel_dir = Path(tmp) / "wheel"
        wheel_dir.mkdir()
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", ".", "-w", str(wheel_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        wheels = sorted(wheel_dir.glob("*.whl"))
        failures: list[str] = []
        if proc.returncode != 0 or len(wheels) != 1:
            failures.append(proc.stdout + proc.stderr)
        else:
            with zipfile.ZipFile(wheels[0]) as archive:
                metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
                metadata = archive.read(metadata_name).decode("utf-8")
                if f"Version: {VERSION}" not in metadata:
                    failures.append("wheel metadata version mismatch")
                if "@" in metadata:
                    failures.append("wheel metadata contains contact address")
        result = {"schema": "mmor-wheel-smoke-1.0", "wheel_count": len(wheels), "failures": failures, "status": "PASS" if not failures else "FAIL"}
        out = ROOT / "validation" / "wheel.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        remove_transient()
        return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
