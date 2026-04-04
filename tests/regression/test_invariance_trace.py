from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

import apr_core.goldset.runner as goldset_runner  # noqa: E402
from apr_core.goldset import run_goldset_manifest  # noqa: E402
from apr_core.goldset.governance import invariance_trace as governance_invariance_trace  # noqa: E402


def test_invariance_trace_detects_silent_drift_when_outputs_match(tmp_path: Path, monkeypatch):
    ledger_path = tmp_path / "calibration_ledger.jsonl"

    baseline = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        ledger_path=ledger_path,
        invariance_trace=True,
    )
    monkeypatch.setattr(
        governance_invariance_trace,
        "hash_decision_path",
        lambda features, weights, scoring_path: "forced-drift-hash",
    )
    drifted = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        ledger_path=ledger_path,
        invariance_trace=True,
    )

    baseline_case = next(case for case in baseline["cases"] if case["case_id"] == "reviewable_sound_paper")
    drifted_case = next(case for case in drifted["cases"] if case["case_id"] == "reviewable_sound_paper")

    assert baseline_case["decision_recommendation"] == drifted_case["decision_recommendation"]
    assert baseline_case["loss_band"] == drifted_case["loss_band"]
    assert drifted_case["invariance_trace"]["drift_detected"] is True
    assert drifted_case["invariance_trace"]["drift_score"] > 0
