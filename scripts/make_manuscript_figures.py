#!/usr/bin/env python3
"""Generate publication figures from the frozen retained evidence."""
from __future__ import annotations

import csv
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
from PIL import Image

from mmor_certificates.instances import explicit_profile_instance
from mmor_certificates.profile import full_domain_profile

OUT = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def save(fig, stem: str) -> None:
    png = OUT / f"{stem}.png"
    eps = OUT / f"{stem}.eps"
    fig.savefig(png, dpi=600, bbox_inches="tight", metadata={})
    fig.savefig(eps, bbox_inches="tight", format="eps", metadata={})
    plt.close(fig)
    # Remove ancillary textual chunks from PNG.
    with Image.open(png) as image:
        image.save(png, format="PNG", optimize=False)
    # Remove non-semantic EPS header fields.
    lines = []
    for line in eps.read_text(encoding="latin-1").splitlines():
        if line.startswith(("%%CreationDate:", "%%Creator:")):
            continue
        lines.append(line)
    eps.write_text("\n".join(lines) + "\n", encoding="latin-1")


# Figure 1: exact profile trichotomy.
fig, ax = plt.subplots(figsize=(6.85, 4.15))
styles = {
    "harmless": ("-", "o"),
    "repairable": ("--", "s"),
    "irreparable": (":", "^")
}
for class_name in ("harmless", "repairable", "irreparable"):
    instance = explicit_profile_instance(3, class_name, 101)
    budgets = [Fraction(i, 20) for i in range(41)]
    values = [float(full_domain_profile(instance, budget).value) for budget in budgets]
    linestyle, marker = styles[class_name]
    ax.plot(
        [float(budget) for budget in budgets],
        values,
        linestyle=linestyle,
        marker=marker,
        markevery=8,
        linewidth=1.4,
        markersize=4,
        label=class_name,
    )
ax.axhline(0.0, linewidth=0.8)
ax.set_xlabel("Normalised multiplier budget $B$")
ax.set_ylabel(r"Profile value $\Gamma_V(B)$")
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "Fig1_profile_trichotomy")


# Figure 2: exact versus conservative Chebyshev threshold.
rows: list[tuple[int, float, str]] = []
for path in sorted((ROOT / "results/raw/cases").glob("*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    cheb = payload.get("chebyshev", {})
    ratio = cheb.get("ratio")
    if ratio is None:
        continue
    rows.append((int(payload["p"]), float(Fraction(ratio)), payload["family"]))
fig, ax = plt.subplots(figsize=(6.85, 4.15))
markers = {2: "o", 3: "s", 4: "^", 5: "D"}
for p in sorted({row[0] for row in rows}):
    vals = [row[1] for row in rows if row[0] == p]
    x = [p + (i - (len(vals) - 1) / 2) * 0.018 for i in range(len(vals))]
    ax.scatter(x, vals, marker=markers.get(p, "o"), s=28, label=f"$p={p}$")
ax.set_yscale("log")
ax.set_xlabel("Objective dimension $p$")
ax.set_ylabel("Exact upper threshold / conservative bound")
ax.set_xticks(sorted({row[0] for row in rows}))
ax.legend(frameon=False, ncol=2)
fig.tight_layout()
save(fig, "Fig2_chebyshev_threshold_ratio")


# Figure 3: retained row fraction against complete domain size.
with (ROOT / "results/raw/scaling_cases.csv").open(encoding="utf-8", newline="") as handle:
    scaling = list(csv.DictReader(handle))
fig, ax = plt.subplots(figsize=(6.85, 4.15))
families = sorted({row["family"] for row in scaling})
family_markers = {name: marker for name, marker in zip(families, ["o", "s", "^", "D", "v", "P"])}
for family in families:
    subset = [row for row in scaling if row["family"] == family]
    ax.scatter(
        [float(row["domain_size"]) for row in subset],
        [float(row["fraction_inspected"]) for row in subset],
        marker=family_markers[family],
        s=34,
        label=family.replace("_", " "),
    )
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Complete verification-domain cardinality")
ax.set_ylabel("Retained rows / complete domain")
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "Fig3_row_economy")


# Figure 4: numerical full-domain scaling baseline.
with (ROOT / "results/raw/numeric_full_domain_scaling.csv").open(encoding="utf-8", newline="") as handle:
    timing = list(csv.DictReader(handle))
labels = [row["case_id"].replace("assignment-", "A-").replace("path-", "P-") for row in timing]
ratios = [float(row["speed_ratio_full_numeric_over_structured"]) for row in timing]
fig, ax = plt.subplots(figsize=(6.85, 4.3))
ax.bar(range(len(ratios)), ratios)
ax.axhline(1.0, linewidth=0.8, linestyle="--")
ax.set_yscale("log")
ax.set_ylabel("Full-domain numerical time / structured time")
ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
fig.tight_layout()
save(fig, "Fig4_scaling_baseline")

print("Generated manuscript figures in", OUT)
