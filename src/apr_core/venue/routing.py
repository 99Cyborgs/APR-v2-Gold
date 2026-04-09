from __future__ import annotations

from typing import Any

from apr_core.anchors import dedupe_anchors

SELECTIVE_MARKERS = ["universal", "field-defining", "broad readership", "transform", "major advance"]
ROUTING_STATES = (
    "blocked_by_scientific_record",
    "retarget_specialist",
    "retarget_soundness_first",
    "preprint_ready_not_journal_ready",
    "submit_with_caution",
    "plausible_send_out",
)


def route_venue(
    payload: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    scientific_record: dict[str, Any],
) -> dict[str, Any]:
    outlet_profile = classification["outlet_profile"]
    scientific_gate_passed = scientific_record["status"] in {"pass", "borderline"}
    anchors = dedupe_anchors([parsing.get("central_claim_anchor"), parsing.get("decisive_support_object"), parsing.get("first_hard_object")])

    if not scientific_gate_passed:
        return {
            "outlet_profile": outlet_profile,
            "routing_state": "blocked_by_scientific_record",
            "scientific_record_gate_passed": False,
            "rationale": ["scientific_record_gate_not_passed"],
            "evidence_anchors": anchors,
        }

    rationale: list[str] = []
    broad_signal = any(marker in (parsing.get("central_claim") or "").lower() for marker in SELECTIVE_MARKERS)
    support_count = int(bool(payload.get("figures_and_captions"))) + int(bool(payload.get("tables")))

    if outlet_profile == "preprint_screen":
        routing_state = "preprint_ready_not_journal_ready"
        rationale.append("preprint_profile_selected")
    elif outlet_profile == "nature_selective":
        if scientific_record["status"] == "borderline" or classification["claim_type"] in {"replication_claim", "null_result_claim"}:
            routing_state = "retarget_soundness_first"
            rationale.append("selective_profile_with_soundness_first_fit")
        elif broad_signal and parsing.get("claim_extraction_confidence", 0.0) >= 0.85 and support_count >= 2:
            routing_state = "submit_with_caution"
            rationale.append("selective_profile_plausible_but_still_editorial_risk")
        else:
            routing_state = "retarget_specialist"
            rationale.append("selective_profile_exceeds_current_scope_signal")
    elif outlet_profile == "aps_selective":
        if parsing.get("claim_extraction_confidence", 0.0) >= 0.8 and support_count >= 2 and scientific_record["status"] == "pass":
            routing_state = "submit_with_caution"
            rationale.append("aps_selective_plausible_with_clear_support")
        else:
            routing_state = "retarget_specialist"
            rationale.append("specialist_fit_is_clearer_than_selective_fit")
    elif outlet_profile == "soundness_first_journal":
        routing_state = "plausible_send_out" if scientific_record["status"] == "pass" else "submit_with_caution"
        rationale.append("soundness_first_profile_selected")
    elif outlet_profile == "review_only_venue":
        routing_state = "plausible_send_out" if classification["article_type"] in {"review", "systematic_review"} else "retarget_specialist"
        rationale.append("review_only_profile_selected")
    else:
        routing_state = "plausible_send_out" if scientific_record["status"] == "pass" else "submit_with_caution"
        rationale.append("specialist_profile_selected")

    return {
        "outlet_profile": outlet_profile,
        "routing_state": routing_state,
        "scientific_record_gate_passed": True,
        "rationale": rationale,
        "evidence_anchors": anchors,
    }
