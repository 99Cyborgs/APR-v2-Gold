from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset import run_goldset_manifest  # noqa: E402
from apr_core.goldset.surface_contract import enforce_surface_exclusivity  # noqa: E402


def test_surface_contract_rejects_mixed_scoring_usage():
    with pytest.raises(ValueError):
        enforce_surface_exclusivity(
            {
                "scoring": {
                    "scientific_score": {"total": 1.0},
                    "scientific_vector": {"claim_clarity": 1.0},
                },
                "export": {},
            }
        )


def test_surface_contract_emits_runtime_namespace_status():
    summary = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml",
        strict_surface_contract=True,
    )
    case = next(item for item in summary["cases"] if item["case_id"] == "reviewable_sound_paper")

    assert case["surface_contract"]["legacy_present"] is True
    assert case["surface_contract"]["native_present"] is True
    assert case["surface_contract"]["mixed_usage_violation"] is False
    assert case["surface_contract"]["reason_codes"] == []
    assert case["surface_contract"]["enforcement_mode"] == "strict"
    assert case["surface_contract"]["warning_mode_active"] is False
