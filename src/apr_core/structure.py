from __future__ import annotations

import re
from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors
from apr_core.policy import load_policy_layer

QUESTION_MARKERS = ("question", "hypothesis", "aim", "objective", "we ask whether", "we test whether")
COMPARATOR_MARKERS = ("baseline", "compare", "compares", "relative to", "versus", "replication")
UNCERTAINTY_MARKERS = ("uncertainty", "confidence interval", "limitation", "limited by", "error bar", "variance")
FAILURE_MARKERS = ("failure regime", "failure condition", "should not be used", "breakdown", "does not hold", "fails when")
RESULT_MARKERS = ("we show", "we report", "results", "reduces", "improves", "predict", "agreement", "constraint")


def _affirmed_marker(text: str, marker: str) -> bool:
    lowered = text.lower()
    pattern = re.compile(rf"\b{re.escape(marker)}\b")
    for match in pattern.finditer(lowered):
        window = lowered[max(0, match.start() - 80) : match.end()]
        if not any(negation in window for negation in ("no ", "without ", "does not ", "never ", "missing ")):
            return True
    return False


def assess_structural_integrity(payload: dict[str, Any], parsing: dict[str, Any]) -> dict[str, Any]:
    policy = load_policy_layer()["policy_layer"]
    thresholds = policy["structural_integrity"]
    combined_text = " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                payload.get("supplement_or_appendix"),
            ],
        )
    ).lower()

    object_of_study = bool(parsing.get("central_claim"))
    claim_text = str(parsing.get("central_claim") or "").lower()
    question = any(_affirmed_marker(combined_text, marker) for marker in QUESTION_MARKERS) or (
        parsing.get("central_claim") is not None and any(token in claim_text for token in ("show", "test", "compare", "derive", "reanalyze"))
    )
    method = bool(parsing.get("first_hard_object")) or any(
        _affirmed_marker(combined_text, marker) for marker in ("method", "protocol", "workflow", "pipeline", "derive", "derivation")
    )
    result = bool(parsing.get("decisive_support_object")) or any(_affirmed_marker(combined_text, marker) for marker in RESULT_MARKERS)
    comparator = any(_affirmed_marker(combined_text, marker) for marker in COMPARATOR_MARKERS) or len(payload.get("references") or []) >= 2
    uncertainty = any(_affirmed_marker(combined_text, marker) for marker in UNCERTAINTY_MARKERS)
    failure_condition = any(_affirmed_marker(combined_text, marker) for marker in FAILURE_MARKERS)
    coherence_bonus = all((object_of_study, question, method, result))

    research_spine_signals = {
        "object_of_study": object_of_study,
        "question": question,
        "method": method,
        "result": result,
        "comparator": comparator,
        "uncertainty": uncertainty,
        "failure_condition": failure_condition,
        "coherence_bonus": coherence_bonus,
    }
    research_spine_score = sum(int(value) for value in research_spine_signals.values())

    if research_spine_score <= int(thresholds["non_reviewable_threshold"]):
        status = "non_reviewable"
    elif research_spine_score <= int(thresholds["rebuild_threshold"]):
        status = "rebuild_required"
    else:
        status = "pass"

    missing_elements = [name for name, present in research_spine_signals.items() if not present and name != "coherence_bonus"]
    anchors = dedupe_anchors(
        [
            parsing.get("central_claim_anchor"),
            parsing.get("first_hard_object"),
            parsing.get("decisive_support_object"),
            first_anchor_from_fields(payload, ["title", "abstract", "manuscript_text"]),
            *search_anchors(payload, QUESTION_MARKERS, max_hits=1),
            *search_anchors(payload, COMPARATOR_MARKERS, max_hits=1),
            *search_anchors(payload, UNCERTAINTY_MARKERS, max_hits=1),
            *search_anchors(payload, FAILURE_MARKERS, max_hits=1),
        ]
    )

    return {
        "status": status,
        "research_spine_score_8": research_spine_score,
        "research_spine_signals": research_spine_signals,
        "missing_elements": missing_elements,
        "evidence_anchors": anchors,
    }
