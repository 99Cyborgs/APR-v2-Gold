from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))
existing = sys.modules.get("apr_core")
if existing and not str(getattr(existing, "__file__", "")).startswith(str(SRC)):
    for name in list(sys.modules):
        if name == "apr_core" or name.startswith("apr_core."):
            sys.modules.pop(name, None)

import apr_core.goldset.runner as goldset_runner  # noqa: E402
from apr_core.goldset import run_goldset_manifest  # noqa: E402


def _active_cases(summary: dict[str, object]) -> list[dict[str, object]]:
    return [case for case in summary["cases"] if case["case_state"] == "active"]


def test_editorial_weight_invariance_holds_for_fixture_manifest():
    baseline = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", export_calibration_extended=True)
    weighted = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        export_calibration_extended=True,
        enable_editorial_weight=True,
    )

    baseline_cases = _active_cases(baseline)
    weighted_cases = _active_cases(weighted)

    assert any((case.get("editorial_penalty") or 0) > 0 for case in weighted_cases)
    assert {case["case_id"]: case["decision_recommendation"] for case in baseline_cases} == {
        case["case_id"]: case["decision_recommendation"] for case in weighted_cases
    }
    assert {case["case_id"]: case["loss_band"] for case in baseline_cases} == {
        case["case_id"]: case["loss_band"] for case in weighted_cases
    }
    assert [case["case_id"] for case in sorted(baseline_cases, key=goldset_runner._public_rank_key)] == [
        case["case_id"] for case in sorted(weighted_cases, key=goldset_runner._public_rank_key)
    ]
    goldset_runner._enforce_editorial_weight_invariance(weighted_cases, weighted["governance"])


def test_editorial_weight_invariance_guard_rejects_calibration_bin_drift():
    governance = goldset_runner._resolve_goldset_governance_config(enable_editorial_weight=True)
    cases = [
        {
            "case_id": "case-a",
            "case_state": "active",
            "scientific_recommendation": "PLAUSIBLE_SEND_OUT",
            "scientific_recommendation_band": "viable_journal",
            "decision_recommendation": "PLAUSIBLE_SEND_OUT",
            "scientific_loss": 1.0,
            "loss_band": "high",
        }
    ]

    with pytest.raises(goldset_runner.EditorialDriftError):
        goldset_runner._enforce_editorial_weight_invariance(cases, governance)
