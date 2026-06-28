# Release notes 2.0.1

Version 2.0.1 is a post-deposit archival correction release for the verification-domain certificate profile framework. It does not change the mathematical protocol, case grid, candidate-selection rules, proof-object semantics, algorithms, retained exact classifications or retained profile values from version 2.0.0.

## Corrections

- repository metadata now points to `https://github.com/antonioclim/verification-domain-profiles`;
- the validation script now accepts either a clean pre-deposit state with no release DOI, or a post-deposit state in which `CITATION.cff`, `codemeta.json` and public prose consistently contain the Zenodo version DOI;
- Zenodo metadata now treats the earlier companion artefact as a referenced artefact rather than as an identical object;
- package, protocol, validation and citation metadata are aligned to version `2.0.1`;
- `scripts/finalise_release_doi.py` inserts the Zenodo version DOI after the archive has been minted.

## Retained evidence

- 84/84 exact classification agreements;
- 84/84 exact minimum-budget agreements;
- 196/196 exact fixed-budget profile agreements;
- 24/24 semantic mutations rejected;
- 17/17 unit tests passed;
- 28 harmless, 28 repairable and 28 irreparable cases.

## Boundary

This release is archival hygiene, not a new scientific experiment. Timing values remain descriptive and environment-dependent; exact classifications, budgets, profile values and proof-object replay remain the normative evidence.

## Archived DOI

Archived version DOI: https://doi.org/10.5281/zenodo.21011691
