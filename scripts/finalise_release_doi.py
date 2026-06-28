#!/usr/bin/env python3
"""Insert a minted Zenodo version DOI into release metadata.

This script is intentionally post-deposit only. Before Zenodo mints the final
version DOI, the release candidate should contain no Zenodo version DOI in
CITATION.cff, CodeMeta, README, REPRODUCE or release notes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.0.1"
REPO = "https://github.com/antonioclim/verification-domain-profiles"
TAG_URL = f"{REPO}/releases/tag/v{VERSION}"
DOI_RE = re.compile(r"^10\.5281/zenodo\.\d+$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def set_yaml_scalar(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$", re.M)
    line = f'{key}: "{value}"'
    if pattern.search(text):
        return pattern.sub(line, text)
    return text.rstrip() + "\n" + line + "\n"


def add_or_replace_marker(text: str, doi_url: str) -> str:
    marker = f"Archived version DOI: {doi_url}"
    if "Archived version DOI: https://doi.org/10.5281/zenodo." in text:
        return re.sub(r"Archived version DOI: https://doi\.org/10\.5281/zenodo\.\d+", marker, text)
    if marker not in text:
        return text.rstrip() + "\n\n" + marker + "\n"
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doi", required=True, help="Zenodo version DOI")
    parser.add_argument("--date-released", default=None, help="ISO date YYYY-MM-DD; defaults to today in UTC")
    args = parser.parse_args()

    doi = args.doi.strip().replace("https://doi.org/", "")
    if not DOI_RE.fullmatch(doi):
        raise SystemExit("DOI must have the form 10.5281/zenodo.<digits>")
    doi_url = f"https://doi.org/{doi}"
    date_released = args.date_released or datetime.now(timezone.utc).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_released):
        raise SystemExit("--date-released must have the form YYYY-MM-DD")

    cff = ROOT / "CITATION.cff"
    text = read_text(cff)
    text = set_yaml_scalar(text, "doi", doi)
    text = set_yaml_scalar(text, "url", doi_url)
    text = set_yaml_scalar(text, "date-released", date_released)
    write_text(cff, text)

    cm_path = ROOT / "codemeta.json"
    cm = json.loads(read_text(cm_path))
    cm["identifier"] = doi_url
    cm["sameAs"] = [doi_url, TAG_URL]
    write_text(cm_path, json.dumps(cm, indent=2, sort_keys=True) + "\n")

    for rel in ["README.md", "REPRODUCE.md", "docs/RELEASE_NOTES_2.0.1.md"]:
        path = ROOT / rel
        write_text(path, add_or_replace_marker(read_text(path), doi_url))

    record = {
        "schema": "mmor-postdeposit-doi-record-1.0",
        "software_version": VERSION,
        "version_doi": doi,
        "version_doi_url": doi_url,
        "github_release": TAG_URL,
        "date_released": date_released,
        "status": "RECORDED",
    }
    validation = ROOT / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    (validation / "postdeposit_doi.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return subprocess.run([
        sys.executable,
        "scripts/run_release_validation.py",
        "--fast",
        "--expected-doi",
        doi,
    ], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
