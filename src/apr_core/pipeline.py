from __future__ import annotations

"""Run the governed APR audit pipeline from schema-bound input to schema-bound output.

APR accepts only payloads that satisfy the active input schema, but schema
validity is not acceptance. Downstream layers still reject semantically
unassessable, unsupported, or governance-blocked manuscripts before any
canonical record is emitted.
"""

from typing import Any

from jsonschema import validate

from apr_core.adversarial import assess_adversarial_resilience
from apr_core.calibration import assess_claim_evidence_calibration
from apr_core.classify import classify_package
from apr_core.editorial_first_pass import assess_editorial_first_pass
from apr_core.ingest import build_metadata, grade_input_sufficiency, normalize_input
from apr_core.integrity import assess_integrity
from apr_core.models import CanonicalAuditRecord
from apr_core.packs import execute_packs
from apr_core.parse import extract_claims
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema, load_contract_manifest, load_policy_layer
from apr_core.rehabilitation import build_rehabilitation_plan
from apr_core.reviewability import assess_reviewability
from apr_core.scientific_record import assess_scientific_record
from apr_core.structure import assess_structural_integrity
from apr_core.transparency import assess_transparency
from apr_core.utils import utc_now_iso
from apr_core.venue import route_venue


def _downgrade_confidence(confidence: str) -> str:
    return {"high": "medium", "medium": "low", "low": "low"}[confidence]


def _editorial_forecast(
    recommendation: str,
    reviewability: dict[str, Any],
    structural_integrity: dict[str, Any],
    scientific_record: dict[str, Any],
    venue: dict[str, Any],
    editorial_first_pass: dict[str, Any],
) -> str:
    if reviewability["status"] == "fail" or structural_integrity["status"] == "non_reviewable":
        return "NON_REVIEWABLE"
    if scientific_record["status"] == "fatal_fail":
        return "SCIENTIFIC_RECORD_BLOCK"
    if scientific_record["status"] == "repairable_fail":
        return "REBUILD_REQUIRED"
    if venue["routing_state"] == "retarget_soundness_first":
        return "RETARGET_SOUNDNESS_FIRST"
    if venue["routing_state"] == "retarget_specialist":
        return "RETARGET_SPECIALIST"
    if venue["routing_state"] == "preprint_ready_not_journal_ready":
        return "PREPRINT_ONLY"
    if editorial_first_pass["desk_reject_probability"] >= 0.75:
        return "DESK_REJECT_RISK"
    if recommendation == "SUBMIT_WITH_CAUTION":
        return "CAUTIONARY_SEND_OUT"
    return "PLAUSIBLE_SEND_OUT"


def _author_recommendation(
    recommendation: str,
    editorial_forecast: str,
    editorial_first_pass: dict[str, Any],
) -> str:
    if editorial_forecast == "DESK_REJECT_RISK" and recommendation in {
        "PLAUSIBLE_SEND_OUT",
        "SUBMIT_WITH_CAUTION",
        "RETARGET_SPECIALIST",
        "RETARGET_SOUNDNESS_FIRST",
        "PREPRINT_READY_NOT_JOURNAL_READY",
    }:
        return "REVISE_BEFORE_SUBMISSION"
    if editorial_first_pass["desk_reject_probability"] >= 0.9 and recommendation == "PLAUSIBLE_SEND_OUT":
        return "SUBMIT_WITH_CAUTION"
    return recommendation


def _decision_from_states(
    input_sufficiency: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    reviewability: dict[str, Any],
    integrity: dict[str, Any],
    structural_integrity: dict[str, Any],
    claim_evidence_calibration: dict[str, Any],
    adversarial_resilience: dict[str, Any],
    scientific_record: dict[str, Any],
    venue: dict[str, Any],
    editorial_first_pass: dict[str, Any],
    pack_execution: dict[str, Any],
    pack_results: list[dict[str, Any]],
) -> dict[str, Any]:
    human = integrity["human_escalation_required"] or pack_execution["any_pack_requested_human_escalation"]
    pack_uncertainty = bool(pack_execution["pack_load_failures"]) or any(
        result["status"] in {"borderline", "fail"} for result in pack_results
    )

    if reviewability["status"] == "fail":
        recommendation = "NON_REVIEWABLE"
    elif integrity["status"] == "escalate":
        recommendation = "DO_NOT_SUBMIT"
    elif structural_integrity["status"] == "non_reviewable":
        recommendation = "NON_REVIEWABLE"
    elif scientific_record["status"] == "fatal_fail":
        recommendation = "DO_NOT_SUBMIT"
    elif scientific_record["status"] == "repairable_fail":
        if (
            structural_integrity["status"] == "rebuild_required"
            or claim_evidence_calibration["status"] in {"fail", "fatal"}
            or classification["article_claim_mismatch"]
            or reviewability["checks"]["assessable_method_model_or_protocol"] == "fail"
        ):
            recommendation = "REBUILD_BEFORE_SUBMISSION"
        else:
            recommendation = "REVISE_BEFORE_SUBMISSION"
    else:
        mapping = {
            "retarget_specialist": "RETARGET_SPECIALIST",
            "retarget_soundness_first": "RETARGET_SOUNDNESS_FIRST",
            "preprint_ready_not_journal_ready": "PREPRINT_READY_NOT_JOURNAL_READY",
            "submit_with_caution": "SUBMIT_WITH_CAUTION",
            "plausible_send_out": "PLAUSIBLE_SEND_OUT",
        }
        recommendation = mapping.get(venue["routing_state"], "SUBMIT_WITH_CAUTION")

    if adversarial_resilience["status"] == "blocked" and recommendation in {
        "RETARGET_SPECIALIST",
        "RETARGET_SOUNDNESS_FIRST",
        "PREPRINT_READY_NOT_JOURNAL_READY",
        "SUBMIT_WITH_CAUTION",
        "PLAUSIBLE_SEND_OUT",
    }:
        recommendation = "REVISE_BEFORE_SUBMISSION"

    if human or input_sufficiency["grade"] == "low" or parsing["claim_extraction_confidence"] < 0.6 or pack_execution["pack_load_failures"]:
        confidence = "low"
    elif scientific_record["status"] == "borderline" or pack_uncertainty or input_sufficiency["grade"] == "medium":
        confidence = "medium"
    else:
        confidence = "high"

    if adversarial_resilience["flag_count"] >= 3:
        confidence = _downgrade_confidence(confidence)
    if adversarial_resilience["status"] == "blocked":
        confidence = "low"

    editorial_forecast = _editorial_forecast(
        recommendation,
        reviewability,
        structural_integrity,
        scientific_record,
        venue,
        editorial_first_pass,
    )
    author_recommendation = _author_recommendation(recommendation, editorial_forecast, editorial_first_pass)

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "human_escalation_required": human,
        "editorial_forecast": editorial_forecast,
        "author_recommendation": author_recommendation,
    }


def run_audit(payload: dict[str, Any], *, pack_paths: list[str] | None = None) -> dict[str, Any]:
    # Input schema validation protects the contract boundary before APR applies
    # its own normalization rules. This prevents "cleanup" from laundering
    # structurally invalid payloads into apparently valid audit inputs.
    validate(instance=payload, schema=load_audit_input_schema())
    manifest = load_contract_manifest()
    policy = load_policy_layer()

    normalized = normalize_input(payload)
    input_sufficiency = grade_input_sufficiency(normalized)
    processing_states = ["INGESTED"]

    parsing = extract_claims(normalized)
    processing_states.append("PARSED")
    classification = classify_package(normalized, parsing)
    processing_states.append("CLASSIFIED")
    reviewability = assess_reviewability(normalized, parsing, classification)
    processing_states.append("REVIEWABILITY_ASSESSED")
    transparency = assess_transparency(normalized, classification)
    integrity = assess_integrity(normalized)
    structural_integrity = assess_structural_integrity(normalized, parsing)
    processing_states.append("STRUCTURAL_INTEGRITY_ASSESSED")
    claim_evidence_calibration = assess_claim_evidence_calibration(normalized, parsing, classification, transparency)
    processing_states.append("CLAIM_EVIDENCE_CALIBRATED")
    adversarial_resilience = assess_adversarial_resilience(
        normalized,
        parsing,
        classification,
        claim_evidence_calibration,
    )
    processing_states.append("ADVERSARIAL_RESILIENCE_ASSESSED")
    scientific_record = assess_scientific_record(
        normalized,
        parsing,
        classification,
        reviewability,
        transparency,
        integrity,
        structural_integrity,
        claim_evidence_calibration,
        adversarial_resilience,
    )
    processing_states.append("SCIENTIFIC_RECORD_ASSESSED")
    venue = route_venue(normalized, parsing, classification, scientific_record)
    processing_states.append("VENUE_CALIBRATED")
    editorial_first_pass = assess_editorial_first_pass(normalized, parsing, structural_integrity)
    processing_states.append("EDITORIAL_FIRST_PASS_ASSESSED")
    rehabilitation = build_rehabilitation_plan(
        normalized,
        classification,
        reviewability,
        scientific_record,
        structural_integrity,
        claim_evidence_calibration,
        adversarial_resilience,
        editorial_first_pass,
        venue,
        integrity,
        transparency,
    )
    processing_states.append("REHABILITATION_COMPUTED")

    # Everything above this point is semantic enforcement. A payload can satisfy
    # the input schema and still be downgraded to NON_REVIEWABLE, blocked on
    # scientific-record grounds, or forced to human escalation.
    core_record = {
        "contract_version": manifest["contract"]["version"],
        "policy_layer_version": policy["policy_layer"]["version"],
        "audit_mode": normalized["audit_mode"],
        "metadata": build_metadata(normalized),
        "input_sufficiency": input_sufficiency,
        "parsing": parsing,
        "classification": classification,
        "reviewability": reviewability,
        "transparency": transparency,
        "integrity": integrity,
        "structural_integrity": structural_integrity,
        "claim_evidence_calibration": claim_evidence_calibration,
        "adversarial_resilience": adversarial_resilience,
        "scientific_record": scientific_record,
        "venue": venue,
        "editorial_first_pass": editorial_first_pass,
        "rehabilitation": rehabilitation,
    }

    pack_execution, pack_results = execute_packs(normalized, core_record, pack_paths=pack_paths)
    processing_states.append("PACKS_EXECUTED")
    decision = _decision_from_states(
        input_sufficiency,
        parsing,
        classification,
        reviewability,
        integrity,
        structural_integrity,
        claim_evidence_calibration,
        adversarial_resilience,
        scientific_record,
        venue,
        editorial_first_pass,
        pack_execution,
        pack_results,
    )

    record = CanonicalAuditRecord(
        **core_record,
        pack_execution=pack_execution,
        pack_results=pack_results,
        decision=decision,
        provenance={
            "runtime_version": manifest["contract"]["version"],
            "generated_at_utc": utc_now_iso(),
            "contract_version": manifest["contract"]["version"],
            "policy_layer_version": policy["policy_layer"]["version"],
            "processing_states_completed": processing_states,
        },
        rendering={
            "default_renderer": "markdown",
            "canonical_source_only": True,
            "template_version": manifest["contract"]["version"],
        },
    ).as_dict()

    # Output schema validation closes the pipeline by proving that semantic
    # enforcement still serialized to the locked canonical contract.
    validate(instance=record, schema=load_canonical_record_schema())
    return record
