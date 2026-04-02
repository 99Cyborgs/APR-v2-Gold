from __future__ import annotations

from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors

ESCALATION_RULES = {
    "suspected_duplicate_publication": ["duplicate-publication", "conference version", "overlap"],
    "authorship_or_credit_dispute": ["authorship", "credit dispute", "authorship order is disputed"],
    "image_or_figure_integrity_signal": ["manually enhanced", "contrast", "image manipulation", "figure integrity"],
    "missing_critical_ethics_clearance": ["no ethics approval", "ethics approval was deferred", "no irb"],
}

FLAG_RULES = {
    "implausibly_perfect_results_surface": ["perfect agreement", "no uncertainty", "all cohorts"],
}


def assess_integrity(payload: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                payload.get("ethics_and_disclosures"),
                payload.get("reviewer_notes"),
            ],
        )
    ).lower()

    flags: list[str] = []
    escalate = False
    for code, phrases in ESCALATION_RULES.items():
        if any(phrase in text for phrase in phrases):
            flags.append(code)
            escalate = True
    for code, phrases in FLAG_RULES.items():
        if any(phrase in text for phrase in phrases):
            flags.append(code)

    anchors = dedupe_anchors(
        [
            *search_anchors(
                payload,
                [
                    "conference version",
                    "overlap",
                    "authorship",
                    "manually enhanced",
                    "contrast",
                    "ethics approval",
                    "perfect agreement",
                    "no uncertainty",
                ],
                max_hits=5,
            ),
            first_anchor_from_fields(payload, ["reviewer_notes", "ethics_and_disclosures", "abstract"]),
        ]
    )

    if escalate:
        status = "escalate"
    elif flags:
        status = "flagged"
    else:
        status = "clear"

    return {
        "status": status,
        "flags": flags,
        "human_escalation_required": status == "escalate",
        "evidence_anchors": anchors,
    }
