from __future__ import annotations

import warnings

import pytest

from apr_core.goldset.surface_contract import SurfaceContractViolation, enforce_surface_exclusivity

from .conftest import FLAG_NAMES, load_case_payload, run_single_case_summary


def test_strict_mode_raises_surface_contract_violation_for_mixed_ingestion_payload():
    payload = {
        "scientific_score": {"total": 1.0},
        "scientific_score_vector": {"claim_clarity": 1.0},
    }

    with pytest.raises(SurfaceContractViolation):
        enforce_surface_exclusivity({"ingestion": payload}, strict_surface_contract=True)


def test_non_strict_mode_allows_but_warns_on_surface_mixing():
    payload = {
        "aggregation": {
            "scientific_score": {"total": 1.0},
            "scientific_score_vector": {"claim_clarity": 1.0},
        }
    }

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        status = enforce_surface_exclusivity(payload, strict_surface_contract=False)

    assert status["mixed_usage_violation"] is True
    assert status["warning_mode_active"] is True
    assert status["enforcement_mode"] == "warn_only"
    assert status["reason_codes"] == ["surface_contract_mixed_namespace"]
    assert caught


def test_runner_enforces_surface_contract_at_ingestion(tmp_path):
    payload = load_case_payload()
    payload["scientific_score"] = {"total": 1.0}
    payload["scientific_score_vector"] = {"claim_clarity": 1.0}

    flags = dict(zip(FLAG_NAMES, (False, False, False, True), strict=False))
    with pytest.raises(SurfaceContractViolation):
        run_single_case_summary(tmp_path, payload, flags)
