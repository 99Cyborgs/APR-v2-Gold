from __future__ import annotations

import re
from typing import Any

from apr_core.derived_utils import anchor_locations

TEXT_FIELDS = ("central_claim", "novelty_delta")
SET_FIELDS = (
    "risk_categories",
    "question_categories",
    "strength_anchor_locations",
    "weakness_anchor_locations",
)
KIND_FIELDS = ("first_hard_object_kind", "decisive_support_object_kind")
ERROR_CLASS_MAP = {
    "central_claim": "wrong_external_central_claim",
    "novelty_delta": "wrong_external_novelty_delta",
    "first_hard_object_kind": "wrong_external_first_hard_object_kind",
    "decisive_support_object_kind": "wrong_external_decisive_support_object_kind",
    "risk_categories": "wrong_external_risk_family",
    "question_categories": "wrong_external_question_family",
    "strength_anchor_locations": "wrong_external_strength_anchor",
    "weakness_anchor_locations": "wrong_external_weakness_anchor",
}
FIELD_THRESHOLDS = {
    "central_claim": 0.6,
    "novelty_delta": 0.55,
    "risk_categories": 0.6,
    "question_categories": 0.5,
    "strength_anchor_locations": 0.5,
    "weakness_anchor_locations": 0.5,
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str | None) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _text_f1(expected: str | None, actual: str | None) -> float:
    expected_tokens = _tokens(expected)
    actual_tokens = _tokens(actual)
    if not expected_tokens and not actual_tokens:
        return 1.0
    if not expected_tokens or not actual_tokens:
        return 0.0
    overlap = len(expected_tokens & actual_tokens)
    precision = overlap / len(actual_tokens)
    recall = overlap / len(expected_tokens)
    if precision + recall == 0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 6)


def _set_score(expected: list[str], actual: list[str]) -> dict[str, float]:
    expected_set = set(expected)
    actual_set = set(actual)
    if not expected_set and not actual_set:
        return {"precision": 1.0, "recall": 1.0}
    if not expected_set or not actual_set:
        return {"precision": 0.0, "recall": 0.0}
    overlap = len(expected_set & actual_set)
    return {
        "precision": round(overlap / len(actual_set), 6),
        "recall": round(overlap / len(expected_set), 6),
    }


def evaluate_external_dissection(
    case: dict[str, Any],
    record: dict[str, Any],
    defense_record: dict[str, Any],
    question_record: dict[str, Any],
) -> dict[str, Any]:
    expected = dict(case.get("expected_external") or {})
    if not expected:
        return {"available": False}

    observed = {
        "central_claim": record.get("parsing", {}).get("central_claim"),
        "novelty_delta": record.get("parsing", {}).get("novelty_delta_candidate"),
        "first_hard_object_kind": (record.get("parsing", {}).get("first_hard_object") or {}).get("kind"),
        "decisive_support_object_kind": (record.get("parsing", {}).get("decisive_support_object") or {}).get("kind"),
        "risk_categories": sorted(
            risk["category"]
            for risk in defense_record.get("risk_items", [])
            if risk["current_answerability"] != "not_applicable" and risk["score"] >= 35
        ),
        "question_categories": sorted({question["category"] for question in question_record.get("questions", [])}),
        "strength_anchor_locations": anchor_locations(
            anchor
            for item in defense_record.get("strength_anchors", [])
            for anchor in item.get("evidence_anchors", [])
        ),
        "weakness_anchor_locations": anchor_locations(
            anchor
            for item in defense_record.get("weakness_anchors", [])
            for anchor in item.get("evidence_anchors", [])
        ),
    }

    metrics: dict[str, Any] = {}
    mismatches: list[dict[str, Any]] = []
    error_classes: list[str] = []

    for field in TEXT_FIELDS:
        if field not in expected:
            continue
        score = _text_f1(expected.get(field), observed.get(field))
        metrics[f"{field}_token_f1"] = score
        if score < FIELD_THRESHOLDS[field]:
            mismatches.append(
                {"field": field, "expected": expected.get(field), "actual": observed.get(field), "metric": score}
            )
            error_classes.append(ERROR_CLASS_MAP[field])

    for field in KIND_FIELDS:
        if field not in expected:
            continue
        match = expected.get(field) == observed.get(field)
        metrics[f"{field}_match"] = match
        if not match:
            mismatches.append(
                {"field": field, "expected": expected.get(field), "actual": observed.get(field), "metric": 0.0}
            )
            error_classes.append(ERROR_CLASS_MAP[field])

    for field in SET_FIELDS:
        if field not in expected:
            continue
        score = _set_score(list(expected.get(field) or []), list(observed.get(field) or []))
        metrics[f"{field}_precision"] = score["precision"]
        metrics[f"{field}_recall"] = score["recall"]
        if score["recall"] < FIELD_THRESHOLDS[field]:
            mismatches.append(
                {"field": field, "expected": expected.get(field), "actual": observed.get(field), "metric": score["recall"]}
            )
            error_classes.append(ERROR_CLASS_MAP[field])

    return {
        "available": True,
        "status": "pass" if not mismatches else "fail",
        "expected": expected,
        "observed": observed,
        "metrics": metrics,
        "mismatches": mismatches,
        "error_classes": sorted(set(error_classes)),
    }


def summarize_external_dissection(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    active = [case["external_dissection"] for case in case_results if case.get("external_dissection", {}).get("available")]
    if not active:
        return {
            "available": False,
            "case_count": 0,
            "passed_case_count": 0,
            "failed_case_count": 0,
            "metric_means": {},
        }

    metric_totals: dict[str, float] = {}
    metric_counts: dict[str, int] = {}
    for case in active:
        for key, value in case.get("metrics", {}).items():
            metric_totals[key] = metric_totals.get(key, 0.0) + float(value)
            metric_counts[key] = metric_counts.get(key, 0) + 1

    return {
        "available": True,
        "case_count": len(active),
        "passed_case_count": sum(1 for case in active if case["status"] == "pass"),
        "failed_case_count": sum(1 for case in active if case["status"] == "fail"),
        "metric_means": {
            key: round(metric_totals[key] / metric_counts[key], 6)
            for key in sorted(metric_totals)
        },
    }
