from __future__ import annotations

"""Gate whether a manuscript is assessable before scientific-record judgment.

Reviewability failure means APR lacks a stable claim, reconstructable method
surface, or claim-bearing support object. That state is rejected early so later
scientific judgments are not mistaken for justified evaluation of an
unassessable manuscript.
"""

from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields


def assess_reviewability(payload: dict[str, Any], parsing: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    first_hard_object = parsing.get("first_hard_object")
    decisive_support_object = parsing.get("decisive_support_object")
    central_claim_anchor = parsing.get("central_claim_anchor")

    # This layer blocks downstream adequacy judgments when the manuscript cannot
    # yet support disciplined review, even if the JSON shape is otherwise valid.
    checks = {
        "recoverable_central_claim": "pass"
        if parsing.get("central_claim") and parsing.get("claim_extraction_confidence", 0.0) >= 0.45
        else "fail",
        "coherent_article_claim_pair": "fail" if classification["article_claim_mismatch"] else "pass",
        "assessable_method_model_or_protocol": "pass"
        if first_hard_object and (payload.get("manuscript_text") or payload.get("supplement_or_appendix"))
        else "fail",
        "identifiable_support_object": "pass" if decisive_support_object else "fail",
        "scholarly_form_for_audit": "pass"
        if payload.get("title") and (payload.get("abstract") or payload.get("manuscript_text"))
        else "fail",
    }

    missing_requirements = [name for name, status in checks.items() if status == "fail"]
    anchors = dedupe_anchors(
        [
            central_claim_anchor,
            first_hard_object,
            decisive_support_object,
            first_anchor_from_fields(payload, ["references", "abstract", "manuscript_text"]),
        ]
    )

    return {
        "status": "fail" if missing_requirements else "pass",
        "checks": checks,
        "missing_requirements": missing_requirements,
        "first_hard_object": first_hard_object,
        "decisive_support_object": decisive_support_object,
        "evidence_anchors": anchors,
    }
