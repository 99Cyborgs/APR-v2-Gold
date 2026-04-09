from __future__ import annotations

import re
from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors
from apr_core.policy import load_policy_layer

SCOPE_MARKERS = ("universal", "all orbital phenomena", "breakthrough", "field-defining", "transformative", "paradigm")
DELTA_MARKERS = ("improves", "reduces", "outperforms", "differs", "first", "novel", "new")
COMPARATOR_MARKERS = ("baseline", "relative to", "versus", "compare", "compares", "replication")
UNCERTAINTY_MARKERS = ("uncertainty", "confidence interval", "limitation", "failure regime", "should not be used")


def _affirmed_marker(text: str, marker: str) -> bool:
    lowered = text.lower()
    pattern = re.compile(rf"\b{re.escape(marker)}\b")
    for match in pattern.finditer(lowered):
        window = lowered[max(0, match.start() - 80) : match.end()]
        if not any(negation in window for negation in ("no ", "without ", "does not ", "never ", "missing ")):
            return True
    return False


def _claim_magnitude(payload: dict[str, Any], parsing: dict[str, Any], classification: dict[str, Any]) -> int:
    text = " ".join(
        filter(None, [parsing.get("central_claim"), parsing.get("novelty_delta_candidate"), payload.get("abstract"), payload.get("title")])
    ).lower()
    magnitude = 1
    if classification.get("claim_type") in {"benchmark_claim", "empirical_claim", "replication_claim", "model_claim"}:
        magnitude += 1
    if any(marker in text for marker in DELTA_MARKERS):
        magnitude += 1
    if any(marker in text for marker in SCOPE_MARKERS):
        magnitude += 1
    if classification.get("outlet_profile") in {"nature_selective", "aps_selective"}:
        magnitude += 1
    return max(1, min(5, magnitude))


def _evidence_level(payload: dict[str, Any], parsing: dict[str, Any], transparency: dict[str, Any]) -> int:
    support_richness = (
        int(bool(payload.get("figures_and_captions")))
        + int(bool(payload.get("tables")))
        + int(bool(payload.get("supplement_or_appendix")))
    )
    text = " ".join(filter(None, [payload.get("abstract"), payload.get("manuscript_text")])).lower()
    level = 1
    if parsing.get("decisive_support_object"):
        level += 1
    if support_richness >= 2:
        level += 1
    if len(payload.get("references") or []) >= 2 or any(_affirmed_marker(text, marker) for marker in COMPARATOR_MARKERS):
        level += 1
    if transparency.get("status") == "declared" and any(_affirmed_marker(text, marker) for marker in UNCERTAINTY_MARKERS):
        level += 1
    return max(1, min(5, level))


def assess_claim_evidence_calibration(
    payload: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    transparency: dict[str, Any],
) -> dict[str, Any]:
    policy = load_policy_layer()["policy_layer"]["claim_evidence_calibration"]
    claim_magnitude = _claim_magnitude(payload, parsing, classification)
    evidence_level = _evidence_level(payload, parsing, transparency)
    mismatch = claim_magnitude - evidence_level

    if mismatch >= int(policy["fatal_threshold"]):
        status = "fatal"
    elif mismatch >= int(policy["fail_threshold"]):
        status = "fail"
    elif mismatch > 0:
        status = "watch"
    else:
        status = "aligned"

    anchors = dedupe_anchors(
        [
            parsing.get("central_claim_anchor"),
            parsing.get("decisive_support_object"),
            first_anchor_from_fields(payload, ["tables", "figures_and_captions", "abstract", "manuscript_text"]),
            *search_anchors(payload, COMPARATOR_MARKERS, max_hits=1),
            *search_anchors(payload, UNCERTAINTY_MARKERS, max_hits=1),
        ]
    )

    return {
        "claim_magnitude": claim_magnitude,
        "evidence_level": evidence_level,
        "mismatch": mismatch,
        "status": status,
        "evidence_anchors": anchors,
    }
