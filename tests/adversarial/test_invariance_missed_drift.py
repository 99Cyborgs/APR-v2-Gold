from __future__ import annotations

from apr_core.goldset.governance.invariance_trace import build_invariance_trace, hash_decision_path


def _case_payload(native_score: float) -> dict[str, object]:
    return {
        "error_classes": ["wrong_article_type"],
        "scientific_score_vector_legacy": {
            "evidence_alignment": 1.0,
            "methodological_validity": 1.0,
            "reproducibility": 1.0,
            "falsifiability": 1.0,
            "baseline_comparison": 1.0,
            "total": 5.0,
        },
        "scientific_score_vector_native": {
            "claim_clarity": native_score,
            "evidence_alignment": 1.0,
            "falsifiability": 1.0,
            "baseline_comparison": 1.0,
            "methodological_legibility": 1.0,
        },
        "editorial_score": {
            "clarity": 1.0,
            "novelty_explicitness": 0.5,
            "structure_quality": 1.0,
            "rhetorical_density": 0.1,
            "total": 2.6,
        },
        "decision_score": 3.0,
        "recommendation_loss": 0.0,
        "scientific_loss": 3.0,
        "editorial_penalty": 0.0,
        "total_loss": 3.0,
        "boundary_margin": 1.0,
        "loss_band": "medium",
        "decision_recommendation": "RETARGET_SPECIALIST",
        "scientific_recommendation": "RETARGET_SPECIALIST",
        "decision_consistency_status": "exact_match",
        "fatal_override": False,
        "status": "pass",
        "drift_counterfactuals": [],
    }


def test_intermediate_score_change_with_same_final_decision_is_detected():
    observed = {"decision.recommendation": "RETARGET_SPECIALIST"}
    severity_weights = {"wrong_article_type": 3.0}

    baseline_case = _case_payload(native_score=0.8)
    changed_case = _case_payload(native_score=0.2)

    baseline_hash = hash_decision_path(
        {
            "error_classes": baseline_case["error_classes"],
            "observed": observed,
            "scientific_score_vector_legacy": baseline_case["scientific_score_vector_legacy"],
            "scientific_score_vector_native": baseline_case["scientific_score_vector_native"],
            "editorial_score": baseline_case["editorial_score"],
        },
        severity_weights,
        {
            "decision_score": baseline_case["decision_score"],
            "recommendation_loss": baseline_case["recommendation_loss"],
            "scientific_loss": baseline_case["scientific_loss"],
            "editorial_penalty": baseline_case["editorial_penalty"],
            "total_loss": baseline_case["total_loss"],
            "boundary_margin": baseline_case["boundary_margin"],
            "loss_band": baseline_case["loss_band"],
            "decision_recommendation": baseline_case["decision_recommendation"],
            "scientific_recommendation": baseline_case["scientific_recommendation"],
            "decision_consistency_status": baseline_case["decision_consistency_status"],
            "fatal_override": baseline_case["fatal_override"],
            "status": baseline_case["status"],
            "weight_applications": severity_weights,
            "counterfactuals": [],
        },
    )

    case_history = [
        {
            "decision_recommendation": baseline_case["decision_recommendation"],
            "loss_band": baseline_case["loss_band"],
            "status": baseline_case["status"],
            "invariance_trace": {"trace_hash": baseline_hash},
        }
    ]
    trace = build_invariance_trace(changed_case, observed, severity_weights, case_history)

    assert trace["drift_detected"] is True
    assert trace["drift_score"] > 0
