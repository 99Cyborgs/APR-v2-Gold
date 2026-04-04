from __future__ import annotations

import copy

import pytest

from apr_core.goldset.governance.invariance_trace import hash_decision_path

from .conftest import FLAG_MATRIX, active_case, flag_id, load_case_payload, run_single_case_summary


def _permuted_payload() -> dict[str, object]:
    payload = load_case_payload()
    updated = copy.deepcopy(payload)
    updated["figures_and_captions"] = list(reversed(payload.get("figures_and_captions", [])))
    updated["tables"] = list(reversed(payload.get("tables", [])))
    updated["references"] = list(reversed(payload.get("references", [])))
    return updated


@pytest.mark.parametrize("flags", FLAG_MATRIX, ids=flag_id)
def test_same_semantics_different_ordering_does_not_trigger_drift(tmp_path, flags):
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    permuted_dir = tmp_path / "permuted"
    permuted_dir.mkdir()
    ledger_path = tmp_path / "invariance_ledger.jsonl"

    payload = load_case_payload()
    baseline = run_single_case_summary(baseline_dir, payload, flags, ledger_path=ledger_path)
    permuted = run_single_case_summary(permuted_dir, _permuted_payload(), flags, ledger_path=ledger_path)

    baseline_case = active_case(baseline)
    permuted_case = active_case(permuted)

    assert permuted_case["decision_recommendation"] == baseline_case["decision_recommendation"]
    assert permuted_case["loss_band"] == baseline_case["loss_band"]
    if flags["invariance_trace"]:
        assert permuted_case["invariance_trace"]["drift_detected"] is False
    else:
        assert "invariance_trace" not in permuted_case


def test_same_semantics_with_float_precision_and_serialization_noise_hashes_identically():
    left_hash = hash_decision_path(
        {
            "observed": {"alpha": 1.0000001, "beta": {"x": 2.0, "y": 3.0}},
            "error_classes": ["a", "b"],
        },
        {"a": 1.0, "b": 2.0},
        {"decision_recommendation": "PLAUSIBLE_SEND_OUT", "loss_band": "low"},
    )
    right_hash = hash_decision_path(
        {
            "error_classes": ["b", "a"],
            "observed": {"beta": {"y": 3.0, "x": 2.0}, "alpha": 1.0000002},
        },
        {"b": 2.0, "a": 1.0},
        {"loss_band": "low", "decision_recommendation": "PLAUSIBLE_SEND_OUT"},
    )

    assert left_hash == right_hash
