# Independent replication protocol

## Objective

Reproduce the exact classifications, minimum budgets, fixed-budget profile values and proof-object replay in an environment not used to create the archive. Timing values are descriptive and need not be byte-identical.

## Required environment

- Python 3.11, 3.12 or 3.13
- a clean virtual environment
- dependencies from `requirements-validation.txt`
- no modification of the frozen protocol

## Commands

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-validation.txt
python -m pip install --no-deps -e .
python scripts/run_release_validation.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Expected exact outcomes

- 84 classification agreements
- 84 minimum-budget agreements
- 196 fixed-budget profile agreements
- 84 rescaling-invariance agreements
- 84 minimum-budget objects accepted
- 196 profile records accepted
- 24 semantic mutations rejected
- 17 unit tests passed

## Report

Record the operating system, Python version, dependency versions, archive SHA-256, validation status and any differences. Do not combine timing results from different machines into one performance estimate.
