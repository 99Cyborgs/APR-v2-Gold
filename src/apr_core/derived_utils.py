from __future__ import annotations

from typing import Any, Iterable

from apr_core.anchors import dedupe_anchors
from apr_core.utils import get_by_path, stable_json_sha256, utc_now_iso

CONTEXT_TYPES = (
    "phd_defense_committee",
    "dissertation_proposal_committee",
    "departmental_research_review",
    "journal_referee",
    "ethics_or_compliance_board",
)

RISK_CATEGORIES = (
    "central_claim_clarity_risk",
    "novelty_positioning_risk",
    "literature_gap_risk",
    "method_legibility_risk",
    "evidence_alignment_risk",
    "overclaim_risk",
    "comparator_or_control_risk",
    "reproducibility_risk",
    "statistics_or_uncertainty_risk",
    "scope_inflation_risk",
    "limitations_acknowledgment_risk",
    "ethics_or_provenance_risk",
    "defense_question_pressure_risk",
)

QUESTION_CATEGORIES = (
    "central_question_and_significance",
    "novelty_relative_to_nearest_prior_work",
    "assumptions_and_theoretical_framing",
    "method_choice_and_alternatives",
    "dataset_sample_or_experimental_design",
    "controls_and_baselines",
    "uncertainty_statistics_and_robustness",
    "interpretation_vs_alternative_explanations",
    "limitations_and_failure_conditions",
    "reproducibility_and_transparency",
    "ethics_and_provenance",
    "contribution_future_work_and_next_experiment",
)

ANNOTATION_CATEGORIES = (
    "strength_anchor",
    "weakness_anchor",
    "ambiguity_anchor",
    "risk_anchor",
    "question_anchor",
    "repair_anchor",
)

ANSWERABILITY_STATES = ("answered", "weak", "missing", "not_applicable")
ANSWERABILITY_RANK = {
    "answered": 0,
    "weak": 1,
    "missing": 2,
    "not_applicable": -1,
}


def severity_from_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def worst_answerability(states: Iterable[str]) -> str:
    observed = [state for state in states if state in ANSWERABILITY_RANK]
    if not observed:
        return "answered"
    return max(observed, key=lambda state: ANSWERABILITY_RANK[state])


def count_answerability(items: Iterable[str]) -> dict[str, int]:
    counts = {state: 0 for state in ANSWERABILITY_STATES}
    for state in items:
        if state in counts:
            counts[state] += 1
    return counts


def dedupe_strings(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def anchor_locations(anchors: Iterable[dict[str, str]]) -> list[str]:
    return dedupe_strings(anchor.get("location", "") for anchor in anchors if anchor)


def _coerce_anchor(candidate: Any) -> dict[str, str] | None:
    if not isinstance(candidate, dict):
        return None
    location = candidate.get("location")
    quote = candidate.get("quote")
    if isinstance(location, str) and isinstance(quote, str):
        return {"location": location, "quote": quote}
    return None


def collect_evidence_anchors(*values: Any) -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            collected.extend(collect_evidence_anchors(*value))
            continue
        if isinstance(value, dict):
            anchor = _coerce_anchor(value)
            if anchor:
                collected.append(anchor)
            if isinstance(value.get("evidence_anchors"), list):
                collected.extend(collect_evidence_anchors(*value["evidence_anchors"]))
    return dedupe_anchors(collected)


def evidence_anchors_from_paths(record: dict[str, Any], paths: Iterable[str]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for dotted_path in paths:
        try:
            anchors.extend(collect_evidence_anchors(get_by_path(record, dotted_path)))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return dedupe_anchors(anchors)


def artifact_source(canonical_record: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = canonical_record.get("metadata", {})
    return {
        "manuscript_id": metadata.get("manuscript_id"),
        "title": metadata.get("title"),
        "canonical_record_sha256": stable_json_sha256(canonical_record),
        "payload_sha256": stable_json_sha256(payload) if payload is not None else None,
        "canonical_contract_version": canonical_record.get("contract_version"),
        "canonical_policy_layer_version": canonical_record.get("policy_layer_version"),
    }


def artifact_provenance(canonical_record: dict[str, Any]) -> dict[str, Any]:
    canonical_provenance = canonical_record.get("provenance", {})
    return {
        "generated_at_utc": canonical_provenance.get("generated_at_utc") or utc_now_iso(),
        "runtime_version": canonical_record.get("contract_version"),
        "source_contract_version": canonical_record.get("contract_version"),
        "source_policy_layer_version": canonical_record.get("policy_layer_version"),
    }
