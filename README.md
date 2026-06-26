# Verification-domain certificate profiles

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXXX.svg)] ([https://doi.org/10.5281/zenodo.XXXXXXXX](https://doi.org/10.5281/zenodo.20915544))

This repository provides the validated computational implementation of a theory of
positive scalarisation certificates over finite verification domains. For a
selected feasible candidate, the central profile is

```text
Gamma_V(B) = max  min_x [lambda^T d(x) + nu^T h(x)]
             s.t. lambda in the simplex, nu >= 0, 1^T nu <= B.
```

The profile records the best scalar margin achievable over a declared domain
when normalised active-constraint multipliers receive budget `B`. It induces
three exact domain classes:

- **harmless**: the minimum budget is zero
- **repairable**: a finite positive budget is necessary and sufficient
- **irreparable**: no finite multiplier budget can certify the candidate

The implementation contains exact rational profile masters, minimum-budget and
fixed-budget row generation, structured assignment and layered shortest-path
oracles, complete finite-domain baselines, exact augmented-Chebyshev intervals
and a standard-library standalone checker.

## Status

Version `2.0.0` is the first stable release of the verification-domain profile framework. The retained exact evidence and the public source tree pass the included release validation. A cross-platform GitHub Actions workflow is supplied for hosted execution after the repository update. Independent physical-machine replication is encouraged but is not claimed as completed by this archive.

No universal runtime superiority is claimed. On the retained small correctness cases the full-domain baseline is sometimes faster. On eight larger enumerated scaling cases the numerical full-domain LP was between 3.30 and 30.50 times slower than structured row generation, with a median factor of 7.10. The numerical LP is a timing baseline only; exact row-generation replay is the source of truth.

The profile is unit-invariant, not scale-free. Objective and active-constraint scales are part of the certificate semantics. They must be declared before comparing domains and must transform together with any change of measurement units.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[validation]"
```

On Windows PowerShell use `.venv\Scripts\Activate.ps1`.

## Fast validation

```bash
make validate
```

The command validates metadata and JSON Schemas, runs the unit suite, replays
all 84 minimum-budget certificates and all 196 profile records with the
standalone checker, attacks representative objects with resealed semantic
mutations and verifies the retained summary.

## Full study

```bash
make study
make objects
make numeric-baseline
make figures
make validate
```

The normative case grid is frozen in
`protocol/COMPUTATIONAL_PROTOCOL.json`. Candidate selection is independent of
the certificate weight and finite grids are prohibited as ground truth.

## Retained evidence

- 84/84 exact classification agreements
- 84/84 exact minimum-budget agreements
- 196/196 exact fixed-budget profile agreements
- 84/84 positive-rescaling invariance checks
- 28 harmless, 28 repairable and 28 irreparable cases
- 24 structured assignment and layered-path cases
- at most 15 structured oracle calls in the correctness corpus
- median 0.904% and maximum 5.79% of challenger outcomes retained
- 36 finite exact Chebyshev thresholds
- median exact/conservative threshold ratio 16.5 and maximum 193.08
- 73 of 84 declared finite budget grids missed the exact minimum budget
- scaling domains up to 177,147 alternatives

## Repository structure

- `src/mmor_certificates/` — exact masters, profile algorithms and oracles
- `checker/` — standalone exact checker using only the Python standard library
- `schemas/` — JSON Schemas for instances, certificates and profile records
- `protocol/` — frozen computational protocol
- `results/instances/` — finite instances bound to retained proof objects
- `results/certificates/` — minimum-budget and irreparability certificates
- `results/profiles/` — exact fixed-budget profile records
- `results/raw/` — case-level numerical and exact evidence
- `results/processed/` — aggregate study summary
- `figures/` — deterministic publication figures
- `validation/` — replay summaries and file manifest
- `docs/` — mathematical, algorithmic and evidence contracts
- `docs/MIGRATION_v1_TO_v2.md` — conceptual, API and archival changes from version 1

## Licences

Source code is licensed under BSD-3-Clause. Retained instances, proof objects,
results, figures and prose documentation are licensed under CC BY 4.0. See
`LICENSE`, `LICENSE-DATA.md` and `NOTICE`.
