from __future__ import annotations

import copy
import warnings

import pytest

from apr_core.goldset.governance.invariance_trace import hash_decision_path
from apr_core.goldset.surface_contract import SurfaceContractViolation, enforce_surface_exclusivity

from .conftest import FLAG_MATRIX, active_case, flag_id, load_case_payload, run_single_case_summary


def _perturb_text(payload: dict[str, object]) -> dict[str, object]:
    updated = copy.deepcopy(payload)
    updated["abstract"] = f"{payload['abstract']} Additional wording preserves the same measurement claim."
    updated["manuscript_text"] = f"{payload['manuscript_text']} The benchmark claim remains unchanged."
    return updated


def _mask_features(payload: dict[str, object]) -> dict[str, object]:
    updated = copy.deepcopy(payload)
    updated["figures_and_captions"] = []
    updated["tables"] = []
    updated["references"] = list(payload.get("references", [])) * 2
    return updated


def _permute_surfaces(payload: dict[str, object]) -> dict[str, object]:
    updated = copy.deepcopy(payload)
    updated["figures_and_captions"] = list(reversed(payload.get("figures_and_captions", [])))
    updated["tables"] = list(reversed(payload.get("tables", [])))
    updated["references"] = list(reversed(payload.get("references", [])))
    return updated


@pytest.mark.parametrize("flags", FLAG_MATRIX, ids=flag_id)
def test_adversarial_matrix_exercises_all_governance_flag_combinations(tmp_path, flags):
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    repeated_dir = tmp_path / "repeated"
    repeated_dir.mkdir()
    masked_dir = tmp_path / "masked"
    masked_dir.mkdir()
    permuted_dir = tmp_path / "permuted"
    permuted_dir.mkdir()

    payload = load_case_payload()
    repeated_ledger_path = tmp_path / "repeated_ledger.jsonl"
    permuted_ledger_path = tmp_path / "permuted_ledger.jsonl"

    baseline = run_single_case_summary(baseline_dir, payload, flags, ledger_path=repeated_ledger_path)
    repeated = run_single_case_summary(repeated_dir, _perturb_text(payload), flags, ledger_path=repeated_ledger_path)
    masked = run_single_case_summary(masked_dir, _mask_features(payload), flags)
    run_single_case_summary(tmp_path / "permuted_baseline", payload, flags, ledger_path=permuted_ledger_path)
    permuted = run_single_case_summary(permuted_dir, _permute_surfaces(payload), flags, ledger_path=permuted_ledger_path)

    baseline_case = active_case(baseline)
    repeated_case = active_case(repeated)
    masked_case = active_case(masked)
    permuted_case = active_case(permuted)

    assert baseline_case["case_id"] == repeated_case["case_id"] == masked_case["case_id"] == permuted_case["case_id"]
    assert repeated["governance_report"]["surface_contract_violations"] >= 0
    assert 0.0 <= repeated["governance_report"]["leakage_resilience_score"] <= 1.0
    assert 0.0 <= repeated["governance_report"]["attribution_stability_score"] <= 1.0
    assert 0.0 <= repeated["governance_report"]["invariance_precision"] <= 1.0
    assert 0.0 <= repeated["governance_report"]["invariance_recall"] <= 1.0
    assert repeated["governance_report"]["warning_mode"]["active"] is False
    assert set(repeated["governance_report"]["layers"]) == {
        "leakage_guard",
        "attribution_identifiability",
        "invariance_trace",
        "surface_contract",
    }

    if flags["leakage_guard"]:
        assert repeated_case["decision_recommendation"] == baseline_case["decision_recommendation"]
        assert repeated_case["leakage_guard"]["query_budget"] <= baseline_case["leakage_guard"]["query_budget"]
    else:
        assert "leakage_guard" not in repeated_case

    if flags["attribution_identifiability"]:
        assert masked_case["counterfactual_extended"]["identifiability_status"] in {"unique", "correlated", "degenerate"}
    else:
        assert "counterfactual_extended" not in masked_case

    if flags["invariance_trace"]:
        assert permuted_case["decision_recommendation"] == baseline_case["decision_recommendation"]
        assert permuted_case["invariance_trace"]["drift_detected"] is False
        assert hash_decision_path(
            {"ordered": ["x", "y"], "float": 1.0000001},
            {"x": 1.0},
            {"decision_recommendation": "PLAUSIBLE_SEND_OUT"},
        ) == hash_decision_path(
            {"float": 1.0000002, "ordered": ["y", "x"]},
            {"x": 1.0},
            {"decision_recommendation": "PLAUSIBLE_SEND_OUT"},
        )
    else:
        assert "invariance_trace" not in permuted_case

    mixed_payload = {
        "ingestion": {
            "scientific_score": {"total": 1.0},
            "scientific_score_vector": {"claim_clarity": 1.0},
        }
    }
    if flags["strict_surface_contract"]:
        with pytest.raises(SurfaceContractViolation):
            enforce_surface_exclusivity(mixed_payload, strict_surface_contract=True)
    else:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            status = enforce_surface_exclusivity(mixed_payload, strict_surface_contract=False)
        assert status["mixed_usage_violation"] is True
        assert caught
