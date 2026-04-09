PYTHON ?= python

.PHONY: install test doctor readiness contract goldset goldset-validate lockstep release

install:
	$(PYTHON) -m pip install -e .[dev]

contract:
	$(PYTHON) scripts/validate_contract.py

goldset-validate:
	$(PYTHON) scripts/validate_goldset.py

lockstep:
	$(PYTHON) scripts/validate_repo_lockstep.py

test:
	$(PYTHON) -m pytest

doctor:
	apr doctor

readiness:
	apr readiness

goldset:
	apr goldset --output output/goldset_summary.json

release:
	$(PYTHON) scripts/build_release.py
