#!/usr/bin/env python3
"""Validate the public distribution tree for contact data, secrets and debris."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"}
BAD_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
BAD_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak", ".swp"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
TOKENS = [re.compile(r"gh[psoru]_[A-Za-z0-9_]{30,}"), re.compile(r"AKIA[A-Z0-9]{16}")]
ABSOLUTE_PATHS = [
    re.compile(r"(?<![A-Za-z0-9])/(?:home|Users|mnt|tmp)/[^\s\"'<>]+"),
    re.compile(r"[A-Za-z]:\\Users\\[^\s\"'<>]+", re.I),
]
LOCAL_ENDPOINT = re.compile(r"\b(?:127\.0\.0\.1|[A-Za-z0-9.-]+\.internal)\b", re.I)
UNRESOLVED = [
    re.compile(r"\b(?:" + "TO" + "DO|" + "FIX" + "ME|" + "T" + "BD)\b"),
    re.compile(r"\b(?:" + "YOUR|" + "NEW)_[A-Z0-9_]+\b"),
]


def scan(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    files = 0
    bytes_scanned = 0
    for path in sorted(root.rglob("*")):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP for part in relative_parts):
            continue
        if path.is_dir():
            if path.name.endswith(".egg-info"):
                findings.append({"path": path.relative_to(root).as_posix(), "category": "build_debris", "detail": path.name})
            continue
        if path.name in {"distribution.json", "distribution_scan.json"}:
            continue
        files += 1
        data = path.read_bytes()
        bytes_scanned += len(data)
        relative = path.relative_to(root).as_posix()
        if path.name in BAD_NAMES or path.suffix.lower() in BAD_SUFFIXES:
            findings.append({"path": relative, "category": "distribution_debris", "detail": path.name})
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if EMAIL.search(text):
            findings.append({"path": relative, "category": "contact_address", "detail": "address-like string"})
        if PRIVATE_KEY.search(text):
            findings.append({"path": relative, "category": "private_key", "detail": "private-key header"})
        for pattern in TOKENS:
            if pattern.search(text):
                findings.append({"path": relative, "category": "access_token", "detail": "token-like string"})
        for pattern in ABSOLUTE_PATHS:
            match = pattern.search(text)
            if match:
                findings.append({"path": relative, "category": "absolute_path", "detail": match.group(0)})
        match = LOCAL_ENDPOINT.search(text)
        if match:
            findings.append({"path": relative, "category": "local_endpoint", "detail": match.group(0)})
        for pattern in UNRESOLVED:
            match = pattern.search(text)
            if match:
                findings.append({"path": relative, "category": "unresolved_marker", "detail": match.group(0)})
    unique = sorted(
        {json.dumps(item, sort_keys=True): item for item in findings}.values(),
        key=lambda item: (item["path"], item["category"], item["detail"]),
    )
    return {
        "schema": "mmor-public-distribution-validation-1.0",
        "files_scanned": files,
        "bytes_scanned": bytes_scanned,
        "finding_count": len(unique),
        "findings": unique,
        "status": "PASS" if not unique else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "distribution_scan.json")
    args = parser.parse_args()
    result = scan(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
