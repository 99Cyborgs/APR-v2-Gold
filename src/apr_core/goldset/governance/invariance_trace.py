from __future__ import annotations

import hashlib
import json
from typing import Any

NON_DETERMINISTIC_FIELDS = {"generated_at_utc", "trace_hash", "run_id", "seed"}


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonicalize(value[key])
            for key in sorted(value)
            if key not in NON_DETERMINISTIC_FIELDS
        }
    if isinstance(value, (set, tuple)):
        value = list(value)
    if isinstance(value, list):
        normalized = [_canonicalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, float):
        return round(value, 6)
    return value


def hash_decision_path(features, severity_weights, scoring_path):
    payload = {
        "canonical_features": _canonicalize(features),
        "severity_weights": _canonicalize(severity_weights),
        "scoring_path": _canonicalize(scoring_path),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def compare_trace_distributions(trace_a, trace_b):
    left = list(trace_a or [])
    right = list(trace_b or [])
    if not left and not right:
        return 0.0
    union = set(left) | set(right)
    if not union:
        return 0.0
    overlap = len(set(left) & set(right))
    return round(1.0 - (overlap / float(len(union))), 6)


def detect_silent_drift(trace_history):
    if len(trace_history) < 2:
        return {"drift_detected": False, "drift_score": 0.0}
    latest = trace_history[-1]
    previous = trace_history[-2]
    outputs_identical = latest.get("outputs") == previous.get("outputs")
    hashes_differ = latest.get("trace_hash") != previous.get("trace_hash")
    drift_score = compare_trace_distributions([latest.get("trace_hash")], [previous.get("trace_hash")])
    return {
        "drift_detected": bool(outputs_identical and hashes_differ),
        "drift_score": drift_score,
    }


def build_invariance_trace(
    case: dict[str, Any],
    observed: dict[str, Any],
    severity_weights: dict[str, float],
    case_history: list[dict[str, Any]],
) -> dict[str, Any]:
    features = {
        "error_classes": case.get("error_classes", []),
        "observed": observed,
        "scientific_score_vector_legacy": case.get("scientific_score_vector_legacy"),
        "scientific_score_vector_native": case.get("scientific_score_vector_native", case.get("scientific_score_vector")),
        "editorial_score": case.get("editorial_score"),
    }
    weights = {
        error_class: severity_weights.get(error_class, 0.0)
        for error_class in sorted(case.get("error_classes", []))
    }
    scoring_path = {
        "decision_score": case.get("decision_score"),
        "recommendation_loss": case.get("recommendation_loss"),
        "scientific_loss": case.get("scientific_loss"),
        "editorial_penalty": case.get("editorial_penalty"),
        "total_loss": case.get("total_loss"),
        "boundary_margin": case.get("boundary_margin"),
        "loss_band": case.get("loss_band"),
        "decision_recommendation": case.get("decision_recommendation"),
        "scientific_recommendation": case.get("scientific_recommendation"),
        "decision_consistency_status": case.get("decision_consistency_status"),
        "fatal_override": case.get("fatal_override"),
        "status": case.get("status"),
        "weight_applications": weights,
        "counterfactuals": case.get("drift_counterfactuals", []),
    }
    trace_hash = hash_decision_path(features, weights, scoring_path)
    history: list[dict[str, Any]] = []
    previous = case_history[-1] if case_history else None
    if previous and previous.get("invariance_trace"):
        history.append(
            {
                "trace_hash": previous["invariance_trace"].get("trace_hash"),
                "outputs": {
                    "decision_recommendation": previous.get("decision_recommendation"),
                    "loss_band": previous.get("loss_band"),
                    "status": previous.get("status"),
                },
            }
        )
    history.append(
        {
            "trace_hash": trace_hash,
            "outputs": {
                "decision_recommendation": case.get("decision_recommendation"),
                "loss_band": case.get("loss_band"),
                "status": case.get("status"),
            },
        }
    )
    drift = detect_silent_drift(history)
    return {
        "trace_hash": trace_hash,
        "drift_detected": drift["drift_detected"],
        "drift_score": drift["drift_score"],
    }
