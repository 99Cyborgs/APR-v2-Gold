from __future__ import annotations

import itertools
import sys
from pathlib import Path

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

FLAG_NAMES = (
    "leakage_guard",
    "attribution_identifiability",
    "invariance_trace",
    "strict_surface_contract",
)


def _active_cases(summary: dict[str, object]) -> list[dict[str, object]]:
    return [case for case in summary["cases"] if case["case_state"] == "active"]


def _case_decisions(summary: dict[str, object]) -> dict[str, object]:
    return {case["case_id"]: case["decision_recommendation"] for case in _active_cases(summary)}


def _ranking_indices(summary: dict[str, object]) -> dict[str, int]:
    ordered = sorted(_active_cases(summary), key=goldset_runner._public_rank_key)
    return {case["case_id"]: index for index, case in enumerate(ordered)}


def _loss_bands(summary: dict[str, object]) -> dict[str, object]:
    return {case["case_id"]: case["loss_band"] for case in _active_cases(summary)}


def _calibration_bins(summary: dict[str, object]) -> dict[str, object]:
    return {
        case["case_id"]: case["calibration_extended"]["loss_band"]
        for case in summary["calibration_export"]["cases"]
    }


def test_governance_flags_do_not_change_decisions_rankings_or_bins():
    baseline = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        export_calibration_extended=True,
    )
    baseline_decisions = _case_decisions(baseline)
    baseline_ranking_indices = _ranking_indices(baseline)
    baseline_loss_bands = _loss_bands(baseline)
    baseline_calibration_bins = _calibration_bins(baseline)

    for enabled_values in itertools.product((False, True), repeat=len(FLAG_NAMES)):
        summary = run_goldset_manifest(
            ROOT / "benchmarks" / "goldset" / "manifest.yaml",
            export_calibration_extended=True,
            **dict(zip(FLAG_NAMES, enabled_values, strict=False)),
        )

        assert _case_decisions(summary) == baseline_decisions
        assert _ranking_indices(summary) == baseline_ranking_indices
        assert _loss_bands(summary) == baseline_loss_bands
        assert _calibration_bins(summary) == baseline_calibration_bins
