from __future__ import annotations

import pytest

import apr_core.goldset.runner as goldset_runner

from .conftest import active_case, run_full_manifest_summary

INTERACTION_COMBINATIONS = [
    {"leakage_guard": True, "attribution_identifiability": False, "invariance_trace": True, "strict_surface_contract": False},
    {"leakage_guard": False, "attribution_identifiability": True, "invariance_trace": True, "strict_surface_contract": False},
    {"leakage_guard": True, "attribution_identifiability": True, "invariance_trace": False, "strict_surface_contract": False},
    {"leakage_guard": True, "attribution_identifiability": True, "invariance_trace": True, "strict_surface_contract": True},
]


def _case_decisions(summary: dict[str, object]) -> dict[str, object]:
    return {
        case["case_id"]: case["decision_recommendation"]
        for case in summary["cases"]
        if case["case_state"] == "active"
    }


def _ranking(summary: dict[str, object]) -> list[str]:
    active_cases = [case for case in summary["cases"] if case["case_state"] == "active"]
    return [case["case_id"] for case in sorted(active_cases, key=goldset_runner._public_rank_key)]


def _loss_bands(summary: dict[str, object]) -> dict[str, object]:
    return {
        case["case_id"]: case["loss_band"]
        for case in summary["cases"]
        if case["case_state"] == "active"
    }


@pytest.mark.parametrize("flags", INTERACTION_COMBINATIONS)
def test_cross_layer_interactions_do_not_create_decision_or_metadata_drift(tmp_path, flags):
    baseline = run_full_manifest_summary(tmp_path / "baseline", {name: False for name in flags})
    interaction = run_full_manifest_summary(tmp_path / "interaction", flags)

    assert _case_decisions(interaction) == _case_decisions(baseline)
    assert _ranking(interaction) == _ranking(baseline)
    assert _loss_bands(interaction) == _loss_bands(baseline)
    assert interaction["governance_report"]["surface_contract_violations"] == 0
    assert interaction["governance_report"]["contract_status"]["hard_fail_reason_codes"] == []

    calibration_ids = [case["case_id"] for case in interaction["calibration_export"]["cases"]]
    assert len(calibration_ids) == len(set(calibration_ids))

    case = active_case(interaction)
    assert case["scientific_score_vector"] == case["scientific_score_vector_native"]
    assert case.get("surface_contract", {"mixed_usage_violation": False})["mixed_usage_violation"] is False

    calibration_case = next(item for item in interaction["calibration_export"]["cases"] if item["case_id"] == case["case_id"])
    extended = calibration_case["calibration_extended"]
    assert extended["scientific_vector"] == extended["scientific_vector_native"]
    if flags["leakage_guard"]:
        assert case["leakage_guard"]["query_budget"] <= interaction["governance"]["leakage_guard"]["budget_cap"]
        assert interaction["governance_report"]["layers"]["leakage_guard"]["reproducibility_tier"] == "bounded_nondeterministic"
    if flags["attribution_identifiability"]:
        assert case["counterfactual_extended"]["identifiability_status"] in {"unique", "correlated", "degenerate"}
        assert interaction["governance_report"]["layers"]["attribution_identifiability"]["status"] in {"pass", "warning"}
    if flags["invariance_trace"]:
        assert case["invariance_trace"]["drift_detected"] is False
        assert interaction["governance_report"]["layers"]["invariance_trace"]["precision"] >= 0.0
