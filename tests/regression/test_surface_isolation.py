from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset import load_goldset_ledger_entry_schema, load_goldset_summary_schema, run_goldset_manifest  # noqa: E402
from apr_core import cli as apr_cli  # noqa: E402
import apr_core.goldset.runner as goldset_runner  # noqa: E402
from apr_core.goldset.governance.surface_contract import (  # noqa: E402
    enforce_surface_exclusivity,
    validate_governance_schema_contract,
)


def test_surface_isolation_fails_fast_on_mixed_scoring_consumption():
    with pytest.raises(ValueError):
        enforce_surface_exclusivity(
            {
                "scoring": {
                    "scientific_score": {"total": 1.0},
                    "scientific_vector": {"claim_clarity": 1.0},
                },
                "export": {},
            },
            strict_surface_contract=True,
        )


def test_surface_isolation_fields_are_declared_in_summary_and_ledger_schemas():
    validate_governance_schema_contract(
        load_goldset_summary_schema(),
        load_goldset_ledger_entry_schema(),
    )


def test_surface_isolation_remains_additive_in_runtime_output():
    baseline = run_goldset_manifest(ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml")
    strict = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml",
        strict_surface_contract=True,
    )

    baseline_case = next(case for case in baseline["cases"] if case["case_id"] == "reviewable_sound_paper")
    strict_case = next(case for case in strict["cases"] if case["case_id"] == "reviewable_sound_paper")

    assert "surface_contract" not in baseline_case
    assert strict_case["decision_recommendation"] == baseline_case["decision_recommendation"]
    assert strict_case["surface_contract"]["mixed_usage_violation"] is False


def test_provider_and_adapter_seams_remain_dormant_in_active_runtime():
    cli_source = Path(apr_cli.__file__).read_text(encoding="utf-8")
    runner_source = Path(goldset_runner.__file__).read_text(encoding="utf-8")

    assert "apr_core.providers" not in cli_source
    assert "apr_core.providers" not in runner_source
    assert "apr_core.adapters" not in cli_source
    assert "apr_core.adapters" not in runner_source
