# Public release checklist for v2.0.1

This checklist is normative for the MMOR resubmission artefact.

## Pre-tag checks

- [ ] Working tree contains no `__pycache__`, `build`, `dist` or `*.egg-info` directories.
- [ ] `python -m py_compile scripts/run_release_validation.py scripts/finalise_release_doi.py checker/verify_profile_object.py` passes.
- [ ] `python scripts/run_release_validation.py --fast` passes in a clean environment.
- [ ] `python scripts/run_release_validation.py` passes locally or on GitHub Actions.
- [ ] `.zenodo.json` points to the v2.0.1 GitHub release and does not declare the earlier artefact identical.
- [ ] `CITATION.cff`, `codemeta.json`, `pyproject.toml` and README repository links all point to `verification-domain-profiles`.

## Tag and release

- [ ] Commit message: `Release v2.0.1 metadata and DOI validation hardening`.
- [ ] Public GitHub Actions are green on Ubuntu, Windows and macOS before manuscript citation.
- [ ] Create annotated tag `v2.0.1`.
- [ ] Create GitHub release using `docs/RELEASE_NOTES_2.0.1.md`.
- [ ] Trigger Zenodo archive from the tag/release.

## Post-Zenodo DOI finalisation

- [ ] Record the exact Zenodo version DOI, not only the concept DOI.
- [ ] Run `python scripts/finalise_release_doi.py --doi 10.5281/zenodo.21011691 --date-released 2026-06-28`.
- [ ] Run `python scripts/run_release_validation.py --expected-doi 10.5281/zenodo.21011691 --fast`.
- [ ] Confirm `validation/postdeposit_doi.json` exists and matches the DOI.
- [ ] Update the GitHub release body so the displayed DOI is the same version DOI.
- [ ] Use the same DOI in the manuscript Data availability, Code availability and references.

## No-go conditions

- [ ] Do not cite the release while public CI is red.
- [ ] Do not cite a Zenodo record whose related works state that the old artefact is identical.
- [ ] Do not cite a GitHub release whose displayed DOI differs from the DOI in the manuscript.
