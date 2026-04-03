from __future__ import annotations

"""Run the governed APR audit pipeline from schema-bound input to schema-bound output.

APR accepts only payloads that satisfy the active input schema, but schema
validity is not acceptance. Downstream layers still reject semantically
unassessable, unsupported, or governance-blocked manuscripts before any
canonical record is emitted.
"""

from typing import Any

from jsonschema import validate

from apr_core.classify import classify_package
from apr_core.ingest import build_metadata, grade_input_sufficiency, normalize_input
from apr_core.integrity import assess_integrity
from apr_core.models import CanonicalAuditRecord
from apr_core.packs import execute_packs
from apr_core.parse import extract_claims
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema, load_contract_manifest, load_policy_layer
from apr_core.rehabilitation import build_rehabilitation_plan
from apr_core.reviewability import assess_reviewability
from apr_core.scientific_record import assess_scientific_record
from apr_core.transparency import assess_transparency
from apr_core.utils import utc_now_iso
from apr_core.venue import route_venue


def _decision_from_states(
    input_sufficiency: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    reviewability: dict[str, Any],
    integrity: dict[str, Any],
    scientific_record: dict[str, Any],
    venue: dict[str, Any],
    pack_execution: dict[str, Any],
    pack_results: list[dict[str, Any]],
) -> dict[str, Any]:
    human = integrity["human_escalation_required"] or pack_execution["any_pack_requested_human_escalation"]
    pack_uncertainty = bool(pack_execution["pack_load_failures"]) or any(
        result["status"] in {"borderline", "fail"} for result in pack_results
    )

    if reviewability["status"] == "fail":
        recommendation = "NON_REVIEWABLE"
    elif scientific_record["status"] == "fatal_fail":
        recommendation = "DO_NOT_SUBMIT"
    elif scientific_record["status"] == "repairable_fail":
        if classification["article_claim_mismatch"] or reviewability["checks"]["assessable_method_model_or_protocol"] == "fail":
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

    if human or input_sufficiency["grade"] == "low" or parsing["claim_extraction_confidence"] < 0.6 or pack_execution["pack_load_failures"]:
        confidence = "low"
    elif scientific_record["status"] == "borderline" or pack_uncertainty or input_sufficiency["grade"] == "medium":
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "human_escalation_required": human,
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
    scientific_record = assess_scientific_record(normalized, parsing, classification, reviewability, transparency, integrity)
    processing_states.append("SCIENTIFIC_RECORD_ASSESSED")
    venue = route_venue(normalized, parsing, classification, scientific_record)
    processing_states.append("VENUE_CALIBRATED")
    rehabilitation = build_rehabilitation_plan(normalized, classification, reviewability, scientific_record, venue, integrity, transparency)
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
        "scientific_record": scientific_record,
        "venue": venue,
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
        scientific_record,
        venue,
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
