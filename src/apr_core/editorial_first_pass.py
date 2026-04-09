from __future__ import annotations

from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors
from apr_core.policy import load_policy_layer

GAP_MARKERS = ("gap", "limited by", "however", "despite", "fails", "remains unclear", "need for")
REFERENCE_COVERAGE_MARKERS = ("baseline", "prior work", "relative to", "versus", "compare", "compares")


def assess_editorial_first_pass(
    payload: dict[str, Any],
    parsing: dict[str, Any],
    structural_integrity: dict[str, Any],
) -> dict[str, Any]:
    policy = load_policy_layer()["policy_layer"]["editorial_first_pass"]
    component_maxes = policy["component_max_scores"]
    abstract = str(payload.get("abstract") or "")
    manuscript_text = str(payload.get("manuscript_text") or "")
    combined_text = f"{abstract} {manuscript_text}".lower()
    decisive_result_object = parsing.get("decisive_support_object") or parsing.get("first_hard_object")

    abstract_clarity = 0
    if abstract.strip():
        abstract_clarity += 2
        if len(abstract.split()) >= 20:
            abstract_clarity += 2
        if parsing.get("central_claim"):
            abstract_clarity += 2
        if any(char.isdigit() for char in abstract) or "%" in abstract or "relative to" in abstract.lower():
            abstract_clarity += 2
    abstract_clarity = min(int(component_maxes["abstract_clarity"]), abstract_clarity)

    intro_gap_definition = 0
    if any(marker in combined_text for marker in GAP_MARKERS):
        intro_gap_definition += 3
    if any(marker in combined_text for marker in REFERENCE_COVERAGE_MARKERS):
        intro_gap_definition += 2
    if len(payload.get("references") or []) >= 2:
        intro_gap_definition += 1
    intro_gap_definition = min(int(component_maxes["intro_gap_definition"]), intro_gap_definition)

    first_hard_object_validity = 0
    if parsing.get("first_hard_object"):
        first_hard_object_validity += 3
    if decisive_result_object:
        first_hard_object_validity += 3
    if structural_integrity["research_spine_signals"]["method"]:
        first_hard_object_validity += 1
    if structural_integrity["research_spine_signals"]["result"]:
        first_hard_object_validity += 1
    first_hard_object_validity = min(int(component_maxes["first_hard_object_validity"]), first_hard_object_validity)

    figure_support = 0
    figure_support += min(3, len(payload.get("figures_and_captions") or []))
    figure_support += min(2, len(payload.get("tables") or []))
    figure_support = min(int(component_maxes["figure_support"]), figure_support)

    references_coverage = 0
    reference_count = len(payload.get("references") or [])
    if reference_count >= 1:
        references_coverage += 2
    if reference_count >= 3:
        references_coverage += 2
    if any(marker in combined_text for marker in REFERENCE_COVERAGE_MARKERS):
        references_coverage += 1
    references_coverage = min(int(component_maxes["references_coverage"]), references_coverage)

    component_scores = {
        "abstract_clarity": abstract_clarity,
        "intro_gap_definition": intro_gap_definition,
        "first_hard_object_validity": first_hard_object_validity,
        "figure_support": figure_support,
        "references_coverage": references_coverage,
    }
    total_score = sum(component_scores.values())

    probability_config = policy["desk_reject_probability"]
    raw_probability = (
        float(probability_config["floor"])
        + ((32 - total_score) / 32.0) * float(probability_config["score_weight"])
        + (float(probability_config["low_clarity_penalty"]) if abstract_clarity <= 3 else 0.0)
        + (float(probability_config["low_evidence_penalty"]) if figure_support <= 1 or references_coverage <= 1 else 0.0)
    )
    desk_reject_probability = max(0.0, min(1.0, round(raw_probability, 2)))

    anchors = dedupe_anchors(
        [
            parsing.get("central_claim_anchor"),
            parsing.get("novelty_delta_anchor"),
            decisive_result_object,
            first_anchor_from_fields(payload, ["abstract", "manuscript_text", "figures_and_captions", "tables"]),
            *search_anchors(payload, GAP_MARKERS, max_hits=1),
            *search_anchors(payload, REFERENCE_COVERAGE_MARKERS, max_hits=1),
        ]
    )

    return {
        "central_claim": parsing.get("central_claim"),
        "novelty_delta": parsing.get("novelty_delta_candidate"),
        "decisive_result_object": decisive_result_object,
        "component_scores": component_scores,
        "editorial_first_pass_score_32": total_score,
        "desk_reject_probability": desk_reject_probability,
        "evidence_anchors": anchors,
    }
