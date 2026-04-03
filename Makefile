PYTHON ?= python

.PHONY: install test doctor contract goldset goldset-validate release

install:
	$(PYTHON) -m pip install -e .[dev]

contract:
	$(PYTHON) scripts/validate_contract.py

goldset-validate:
	$(PYTHON) scripts/validate_goldset.py

test:
	$(PYTHON) -m pytest

doctor:
	apr doctor

goldset:
	apr goldset --output output/goldset_summary.json

release:
	$(PYTHON) scripts/build_release.py
