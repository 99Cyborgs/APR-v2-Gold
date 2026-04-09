from __future__ import annotations

from typing import Any


def _one_publishable_unit(classification: dict[str, Any]) -> str:
    article_type = classification["article_type"]
    if article_type == "methods_or_tools":
        return "one method with one decisive benchmark and one documented failure regime"
    if article_type == "theory_or_model":
        return "one model with one discriminating consequence and one limiting-case check"
    if article_type == "replication_or_validation":
        return "one replication question with one decisive constraint table or figure"
    if article_type == "constraint_or_null_result":
        return "one null or constraint result with one auditable comparator"
    return "one core claim with one decisive support object and one stated limitation"


def _minimum_viable_evidence_package(classification: dict[str, Any]) -> list[str]:
    claim_type = classification["claim_type"]
    if claim_type == "model_claim":
        return [
            "one explicit formal object or derivation surface",
            "one discriminating consequence or comparator",
            "one explicit limitation or limiting case",
        ]
    if claim_type in {"benchmark_claim", "empirical_claim", "replication_claim", "null_result_claim"}:
        return [
            "one decisive figure or table",
            "one comparator or baseline",
            "one explicit uncertainty or limitation statement",
        ]
    return [
        "one explicit central claim",
        "one support object that bears the claim",
        "one boundary condition or limitation statement",
    ]


def build_rehabilitation_plan(
    payload: dict[str, Any],
    classification: dict[str, Any],
    reviewability: dict[str, Any],
    scientific_record: dict[str, Any],
    structural_integrity: dict[str, Any],
    claim_evidence_calibration: dict[str, Any],
    adversarial_resilience: dict[str, Any],
    editorial_first_pass: dict[str, Any],
    venue: dict[str, Any],
    integrity: dict[str, Any],
    transparency: dict[str, Any],
) -> dict[str, Any]:
    next_actions: list[str] = []
    if integrity["status"] == "escalate":
        development_track = "human_integrity_review"
        next_actions = [
            "Resolve integrity and policy concerns through human review before any submission action.",
            "Document figure, overlap, authorship, and ethics provenance explicitly.",
            "Re-run APR only after the disputed surfaces are resolved.",
        ]
    elif reviewability["status"] == "fail":
        development_track = "scope_and_reconstruct"
        next_actions = [
            "Reduce the manuscript to one reviewable unit with one explicit central claim.",
            "Expose a reconstructable method, model, or protocol surface.",
            "Add at least one decisive support object and a minimal reference layer.",
        ]
    elif structural_integrity["status"] == "non_reviewable":
        development_track = "research_spine_rebuild"
        next_actions = [
            "Rebuild the manuscript around one object of study, one question, one method, and one decisive result.",
            "Add an explicit comparator and one uncertainty or failure-condition statement.",
            "Retain only one publishable unit until the research spine is coherent.",
        ]
    elif structural_integrity["status"] == "rebuild_required":
        development_track = "research_spine_completion"
        next_actions = [
            "Fill the missing research-spine elements before submission or venue targeting.",
            "Make the comparator, uncertainty, and failure-condition surfaces explicit in the abstract and body.",
            "Collapse extra claims until one structurally coherent publishable unit remains.",
        ]
    elif scientific_record["status"] in {"fatal_fail", "repairable_fail"}:
        development_track = "scientific_record_repair"
        next_actions = [concern["required_evidence_or_revision"] for concern in scientific_record["major_concerns"] if concern["required_evidence_or_revision"]]
    elif venue["routing_state"] == "retarget_specialist":
        development_track = "retarget_and_frame"
        next_actions = [
            "Retarget to a specialist research journal aligned to the actual audience.",
            "Rewrite title and abstract around the scoped contribution rather than broad-readership framing.",
            "Keep the current evidence-to-claim calibration intact during retargeting.",
        ]
    elif venue["routing_state"] == "retarget_soundness_first":
        development_track = "soundness_first_submission"
        next_actions = [
            "Retarget to a soundness-first venue that values technical validity over broad advance.",
            "Make the evidence and transparency layers explicit for a validity-centered review.",
            "Remove any selective-journal framing from the title and abstract.",
        ]
    elif venue["routing_state"] == "preprint_ready_not_journal_ready":
        development_track = "preprint_discussion"
        next_actions = [
            "Use preprint release for discussion while continuing evidence and literature build-out.",
            "Complete the missing transparency and comparator surfaces before journal targeting.",
            "State the provisional limitations explicitly in the manuscript.",
        ]
    else:
        development_track = "submission_ready_with_checks"
        next_actions = [
            "Preserve current scope discipline and evidence-to-claim calibration.",
            "Keep transparency statements synchronized with the actual release surfaces.",
            "Retain the stated limitation boundary in the abstract and discussion.",
        ]

    if transparency["status"] == "incomplete":
        next_actions.append("Complete the missing data, code, or materials statements before external circulation.")
    if claim_evidence_calibration["status"] in {"watch", "fail", "fatal"}:
        next_actions.append("Reduce claim scope or expand the evidence package until claim magnitude and support are calibrated.")
    if adversarial_resilience["flag_count"] >= 3:
        next_actions.append("Remove rhetorical inflation, add explicit baselines, and avoid simulation-only proof framing.")
    if editorial_first_pass["desk_reject_probability"] >= 0.75:
        next_actions.append("Rewrite the title and abstract around the exact gap, decisive object, and bounded claim before submission.")

    deduped_actions = []
    seen = set()
    for action in next_actions:
        if action and action not in seen:
            seen.add(action)
            deduped_actions.append(action)

    return {
        "one_publishable_unit": _one_publishable_unit(classification),
        "development_track": development_track,
        "minimum_viable_evidence_package": _minimum_viable_evidence_package(classification),
        "next_actions_ranked": deduped_actions[:6],
    }
