from __future__ import annotations

from apr_core.goldset.attribution_identifiability import build_counterfactual_summary, detect_non_identifiability


def test_identical_feature_effects_are_never_reported_as_unique():
    summary = build_counterfactual_summary(
        [
            {"feature": "f1", "delta_loss": 1.0, "delta_residual": 1.0},
            {"feature": "f2", "delta_loss": 1.0, "delta_residual": 1.0},
            {"feature": "f3", "delta_loss": 1.0, "delta_residual": 1.0},
        ],
        stability=1.0,
    )

    assert summary["identifiability_status"] in {"degenerate", "correlated"}
    assert summary["identifiability_status"] != "unique"


def test_nearly_singular_attribution_matrix_is_marked_degenerate():
    identifiability = detect_non_identifiability(
        {
            "conditional_importance": {"x1": 1.0, "x2": 0.999999},
            "interaction_matrix": {
                "x1": {"x1": 0.0, "x2": 0.999998},
                "x2": {"x1": 0.999998, "x2": 0.0},
            },
        }
    )

    assert identifiability == "degenerate"


def test_highly_correlated_features_are_marked_correlated_instead_of_unique():
    identifiability = detect_non_identifiability(
        {
            "conditional_importance": {"x1": 1.0, "x2": 1.0},
            "interaction_matrix": {
                "x1": {"x1": 0.0, "x2": 0.25},
                "x2": {"x1": 0.25, "x2": 0.0},
            },
        }
    )

    assert identifiability == "correlated"
