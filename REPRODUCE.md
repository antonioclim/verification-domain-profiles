# Reproduction guide

## Fast exact validation

```bash
python -m pip install -e ".[validation]"
python scripts/run_release_validation.py
```

This validates 364 retained JSON objects, runs the unit suite and replays all
280 certificate/profile objects independently of the generator package.

## Recreate the correctness study

```bash
PYTHONPATH=src python scripts/run_computational_study.py
PYTHONPATH=src python scripts/export_exact_objects.py
PYTHONPATH=src python scripts/run_numeric_full_domain_scaling.py
python scripts/make_manuscript_figures.py
python scripts/run_release_validation.py
```

The study contains environment-dependent timing values. Exact classifications,
budgets, profile values and proof-object replays are expected to agree across
conforming environments. Timing values are descriptive and are not expected to
be byte-identical.

## Verify one object

```bash
python checker/verify_profile_object.py \
  --instance results/instances/explicit-p2-repairable-s101.json \
  --object results/certificates/explicit-p2-repairable-s101.json
```

The checker invokes no optimiser and imports no project module.
