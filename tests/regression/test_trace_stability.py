from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset.governance.invariance_trace import hash_decision_path  # noqa: E402


def test_identical_input_yields_identical_trace_hash():
    features = {"observed": {"a": 1.0}, "error_classes": ["x", "y"]}
    weights = {"x": 1.0, "y": 2.0}
    scoring_path = {"decision_recommendation": "PLAUSIBLE_SEND_OUT", "loss_band": "low"}

    assert hash_decision_path(features, weights, scoring_path) == hash_decision_path(features, weights, scoring_path)


def test_reordered_input_yields_identical_trace_hash():
    left_features = {"error_classes": ["x", "y"], "observed": {"a": 1.0, "b": 2.0}}
    right_features = {"observed": {"b": 2.0, "a": 1.0}, "error_classes": ["y", "x"]}
    left_weights = {"x": 1.0, "y": 2.0}
    right_weights = {"y": 2.0, "x": 1.0}
    left_path = {"decision_recommendation": "PLAUSIBLE_SEND_OUT", "loss_band": "low"}
    right_path = {"loss_band": "low", "decision_recommendation": "PLAUSIBLE_SEND_OUT"}

    assert hash_decision_path(left_features, left_weights, left_path) == hash_decision_path(right_features, right_weights, right_path)


def test_semantic_change_yields_different_trace_hash():
    features = {"observed": {"a": 1.0}, "error_classes": ["x", "y"]}
    weights = {"x": 1.0, "y": 2.0}
    baseline = {"decision_recommendation": "PLAUSIBLE_SEND_OUT", "loss_band": "low"}
    changed = {"decision_recommendation": "DO_NOT_SUBMIT", "loss_band": "high"}

    assert hash_decision_path(features, weights, baseline) != hash_decision_path(features, weights, changed)
