from __future__ import annotations

import copy
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


def _holdout_case_result(*, case_id: str, scientific_loss: float, expected_recommendation: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "expected": {"exact": {"decision.recommendation": expected_recommendation}},
        "expected_decision": {
            "recommendation": expected_recommendation,
            "recommendation_band": goldset_runner._recommendation_band(expected_recommendation),
            "human_escalation_required": False,
        },
        "mismatches": [],
        "scientific_recommendation": "PLAUSIBLE_SEND_OUT",
        "scientific_recommendation_band": "viable_journal",
        "decision_confidence": "high",
        "scientific_score": {
            "evidence_alignment": 1.0,
            "methodological_validity": 1.0,
            "reproducibility": 1.0,
            "falsifiability": 1.0,
            "baseline_comparison": 1.0,
            "total": 1.0,
        },
        "scientific_score_vector": goldset_runner._empty_scientific_score_vector(),
        "scientific_score_vector_legacy": {
            "evidence_alignment": 1.0,
            "methodological_validity": 1.0,
            "reproducibility": 1.0,
            "falsifiability": 1.0,
            "baseline_comparison": 1.0,
            "total": 1.0,
        },
        "scientific_score_vector_native": goldset_runner._empty_scientific_score_vector(),
        "editorial_score": {
            "clarity": 1.0,
            "novelty_explicitness": 1.0,
            "structure_quality": 1.0,
            "rhetorical_density": 0.0,
            "total": 1.0,
        },
        "scientific_loss": scientific_loss,
        "editorial_penalty": 0.0,
        "total_loss": scientific_loss,
        "boundary_margin": 1.0,
        "decision_score": scientific_loss,
        "recommendation_bias": 0,
        "recommendation_loss": 0,
        "loss_band": goldset_runner._loss_band(scientific_loss),
        "total_score": scientific_loss,
        "editorial_forecast": None,
        "author_recommendation": None,
        "decision_recommendation": "PLAUSIBLE_SEND_OUT",
        "status": "fail",
        "decision_consistency_status": "exact_match",
        "drift_counterfactual": None,
        "drift_counterfactuals": [],
        "drift_counterfactual_stability": None,
        "error_classes": ["wrong_article_type"],
        "editorial_plausibility_flags": [],
        "editorial_anomalies": {
            "novelty_density": 0.0,
            "claim_to_evidence_ratio": 0.0,
            "rhetorical_intensity": 0.0,
            "triggered": [],
        },
    }


def _public_surface(masked: dict[str, object]) -> dict[str, object]:
    return {
        key: copy.deepcopy(masked[key])
        for key in (
            "expected",
            "expected_decision",
            "decision_recommendation",
            "scientific_score",
            "scientific_score_vector",
            "scientific_score_vector_legacy",
            "scientific_score_vector_native",
            "error_classes",
            "error_class_bins",
            "error_class_groups",
            "recommendation_bin",
            "loss_band",
            "status",
        )
    }


def test_holdout_leakage_outputs_do_not_encode_expected_labels():
    governance = goldset_runner._resolve_goldset_governance_config(
        holdout_noise=True,
        holdout_blindness_level="moderate",
    )
    governance["holdout_noise"]["error_count_jitter"] = 0
    manifest_sha256 = "holdout-manifest"
    positive = _holdout_case_result(
        case_id="holdout-positive",
        scientific_loss=2.5,
        expected_recommendation="PLAUSIBLE_SEND_OUT",
    )
    blocked = _holdout_case_result(
        case_id="holdout-blocked",
        scientific_loss=4.5,
        expected_recommendation="DO_NOT_SUBMIT",
    )

    masked_positive = goldset_runner._obfuscate_holdout_result(
        positive,
        manifest_sha256=manifest_sha256,
        governance=governance,
    )
    masked_blocked = goldset_runner._obfuscate_holdout_result(
        blocked,
        manifest_sha256=manifest_sha256,
        governance=governance,
    )

    assert _public_surface(masked_positive) == _public_surface(masked_blocked)
    assert masked_positive["expected"]["exact"] == {}
    assert masked_blocked["expected_decision"]["recommendation"] is None
    assert masked_positive["error_class_groups"] == {"semantic": 1}


def test_holdout_leakage_repeated_probing_cannot_reconstruct_exact_loss():
    governance = goldset_runner._resolve_goldset_governance_config(
        holdout_noise=True,
        holdout_blindness_level="moderate",
    )
    governance["holdout_noise"]["error_count_jitter"] = 0
    manifest_sha256 = "holdout-manifest"
    lower_loss = _holdout_case_result(
        case_id="holdout-low",
        scientific_loss=2.5,
        expected_recommendation="PLAUSIBLE_SEND_OUT",
    )
    higher_loss = _holdout_case_result(
        case_id="holdout-high",
        scientific_loss=4.5,
        expected_recommendation="PLAUSIBLE_SEND_OUT",
    )

    repeated_low = [
        goldset_runner._obfuscate_holdout_result(lower_loss, manifest_sha256=manifest_sha256, governance=governance)
        for _ in range(5)
    ]
    repeated_high = [
        goldset_runner._obfuscate_holdout_result(higher_loss, manifest_sha256=manifest_sha256, governance=governance)
        for _ in range(5)
    ]

    assert all(probe["loss_band"] == repeated_low[0]["loss_band"] for probe in repeated_low)
    assert all(probe["loss_band"] == repeated_high[0]["loss_band"] for probe in repeated_high)
    assert repeated_low[0]["loss_band"] == repeated_high[0]["loss_band"] == "medium"
    assert lower_loss["scientific_loss"] != higher_loss["scientific_loss"]
