PYTHON ?= python

.PHONY: test study objects numeric-baseline figures validate clean

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

study:
	PYTHONPATH=src $(PYTHON) scripts/run_computational_study.py

objects:
	PYTHONPATH=src $(PYTHON) scripts/export_exact_objects.py

numeric-baseline:
	PYTHONPATH=src $(PYTHON) scripts/run_numeric_full_domain_scaling.py

figures:
	$(PYTHON) scripts/make_manuscript_figures.py

validate:
	PYTHONPATH=src $(PYTHON) scripts/run_release_validation.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf build dist *.egg-info src/*.egg-info
