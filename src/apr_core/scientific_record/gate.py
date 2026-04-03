from __future__ import annotations

"""Judge scientific-record adequacy after reviewability has been established.

This module is a gate, not a scoring surface. It separates fatal defects from
repairable weaknesses so APR can distinguish manuscripts that should not be sent
out at all from manuscripts that remain assessable but require substantive
repair before submission.
"""

from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields
from apr_core.models import CriterionAssessment

BROAD_MARKERS = ["universal", "all orbital phenomena", "paradigm", "overturns", "field-defining"]


def _criterion(
    status: str,
    severity: str,
    why: str,
    required_repair: str | None,
    anchors: list[dict[str, str] | None],
) -> dict[str, Any]:
    return CriterionAssessment(
        status=status,
        severity=severity,
        why=why,
        required_repair=required_repair,
        evidence_anchors=dedupe_anchors(anchors),
    ).as_dict()


def _breadth_signal(parsing: dict[str, Any]) -> int:
    text = f"{parsing.get('central_claim') or ''} {parsing.get('novelty_delta_candidate') or ''}".lower()
    return sum(1 for marker in BROAD_MARKERS if marker in text)


def assess_scientific_record(
    payload: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    reviewability: dict[str, Any],
    transparency: dict[str, Any],
    integrity: dict[str, Any],
) -> dict[str, Any]:
    central_anchor = parsing.get("central_claim_anchor") or first_anchor_from_fields(payload, ["title", "abstract"])
    method_anchor = parsing.get("first_hard_object") or first_anchor_from_fields(payload, ["manuscript_text", "supplement_or_appendix", "abstract"])
    support_anchor = parsing.get("decisive_support_object") or parsing.get("first_hard_object")
    literature_anchor = first_anchor_from_fields(payload, ["references", "abstract", "manuscript_text"])
    transparency_anchor = first_anchor_from_fields(payload, ["ethics_and_disclosures", "supplement_or_appendix", "manuscript_text", "abstract"])
    integrity_anchor = first_anchor_from_fields(payload, ["reviewer_notes", "ethics_and_disclosures", "abstract"])

    confidence = parsing.get("claim_extraction_confidence", 0.0)
    contradiction_flags = parsing.get("contradiction_flags") or []
    support_richness = int(bool(payload.get("figures_and_captions"))) + int(bool(payload.get("tables"))) + int(bool(payload.get("supplement_or_appendix")))
    ref_count = len(payload.get("references") or [])
    breadth = _breadth_signal(parsing)

    criteria: dict[str, dict[str, Any]] = {}

    # Reviewability is a prerequisite here. Scientific-record status should
    # never be read as trust in manuscripts whose core claim is still
    # unrecoverable or method surface is missing.
    if reviewability["checks"]["recoverable_central_claim"] == "fail" or confidence < 0.4:
        criteria["problem_definition_and_claim_clarity"] = _criterion(
            "fail",
            "fatal",
            "The central claim is not recoverable with sufficient stability for editorial assessment.",
            "Reduce the manuscript to one explicit primary claim and align the abstract and body around it.",
            [central_anchor],
        )
    elif confidence < 0.7 or contradiction_flags:
        criteria["problem_definition_and_claim_clarity"] = _criterion(
            "borderline",
            "moderate",
            "The central claim is only partly recoverable or is destabilized by internal contradiction signals.",
            "Narrow scope, remove contradictory registers, and restate the central claim in one sentence.",
            [central_anchor],
        )
    else:
        criteria["problem_definition_and_claim_clarity"] = _criterion(
            "pass",
            "none",
            "A central claim is recoverable and stable enough for downstream assessment.",
            None,
            [central_anchor],
        )

    if reviewability["checks"]["assessable_method_model_or_protocol"] == "fail":
        criteria["methodological_legibility"] = _criterion(
            "fail",
            "fatal",
            "No reconstructable method, model, or protocol surface is visible.",
            "Expose one assessable derivation, protocol, benchmark workflow, or analysis surface.",
            [method_anchor],
        )
    elif len((payload.get("manuscript_text") or "")) < 220 and not payload.get("supplement_or_appendix"):
        criteria["methodological_legibility"] = _criterion(
            "borderline",
            "major",
            "Methodological detail is present but too thin for confident scientific-record assessment.",
            "Add methodological detail, assumptions, and the exact evaluation surface.",
            [method_anchor],
        )
    else:
        criteria["methodological_legibility"] = _criterion(
            "pass",
            "none",
            "A method, model, or protocol surface is visible for assessment.",
            None,
            [method_anchor],
        )

    if classification["article_claim_mismatch"]:
        criteria["evidence_to_claim_alignment"] = _criterion(
            "fail",
            "fatal",
            f"The article form is mismatched to the inferred claim burden: {classification['article_claim_mismatch_reason']}.",
            "Reframe the article honestly or rebuild the evidence package to match the claim burden.",
            [central_anchor, support_anchor],
        )
    elif not support_anchor:
        criteria["evidence_to_claim_alignment"] = _criterion(
            "fail",
            "fatal",
            "No decisive support object is visible for the main claim.",
            "Add a claim-bearing figure, table, theorem, derivation, or benchmark object.",
            [central_anchor],
        )
    elif breadth >= 1 and support_richness < 2:
        criteria["evidence_to_claim_alignment"] = _criterion(
            "fail",
            "fatal",
            "Broad or revisionary claim language outruns the visible support chain.",
            "Narrow the central claim or add substantially stronger support before submission.",
            [central_anchor, support_anchor],
        )
    elif classification["claim_type"] in {"benchmark_claim", "empirical_claim", "replication_claim", "null_result_claim"} and support_richness < 2:
        criteria["evidence_to_claim_alignment"] = _criterion(
            "borderline",
            "major",
            "The support chain is visible but thin relative to the claim type.",
            "Add a clearer comparator, decisive table or figure, or a stronger validation surface.",
            [central_anchor, support_anchor],
        )
    else:
        criteria["evidence_to_claim_alignment"] = _criterion(
            "pass",
            "none",
            "The visible support chain is minimally commensurate with the claim as stated.",
            None,
            [central_anchor, support_anchor],
        )

    if classification["article_type"] in {"review", "systematic_review"} and ref_count < 5:
        criteria["literature_positioning"] = _criterion(
            "fail",
            "major",
            "Review-like article form is under-supported by the visible reference layer.",
            "Expand the reference base and make comparator coverage explicit.",
            [literature_anchor],
        )
    elif ref_count == 0:
        criteria["literature_positioning"] = _criterion(
            "borderline",
            "major",
            "No explicit reference layer is visible, so literature positioning is provisional.",
            "Add the nearest comparator literature and state the exact delta from prior work.",
            [literature_anchor],
        )
    elif ref_count < 2:
        criteria["literature_positioning"] = _criterion(
            "borderline",
            "moderate",
            "The literature layer is present but still sparse for confident positioning.",
            "Add the most relevant comparator and scope-setting references.",
            [literature_anchor],
        )
    else:
        criteria["literature_positioning"] = _criterion(
            "pass",
            "none",
            "A minimally auditable literature context is present.",
            None,
            [literature_anchor],
        )

    if classification["article_type"] == "systematic_review" and not payload.get("reporting_checklist"):
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "fail",
            "major",
            "A review-synthesis manuscript lacks a visible reporting checklist trace.",
            "Provide the applicable reporting checklist and indicate where it is satisfied.",
            [transparency_anchor],
        )
    elif transparency["status"] == "missing" and classification["outlet_profile"] == "preprint_screen":
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "borderline",
            "moderate",
            "Transparency pathways are still missing, but the current outlet profile is preprint screening rather than journal readiness.",
            "Add explicit data, code, and materials statements before journal submission.",
            [transparency_anchor],
        )
    elif transparency["status"] == "missing":
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "fail",
            "major",
            "No explicit transparency pathway is declared where one would normally be expected.",
            "Declare data, code, and materials pathways or justify non-public restrictions explicitly.",
            [transparency_anchor],
        )
    elif transparency["status"] == "incomplete":
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "borderline",
            "moderate",
            "Transparency pathways are only partly declared.",
            "Complete the missing transparency statements or mark them not applicable explicitly.",
            [transparency_anchor],
        )
    elif transparency["status"] == "not_applicable":
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "not_assessable",
            "none",
            "No material transparency obligation is inferred for the visible article form.",
            None,
            [transparency_anchor],
        )
    else:
        criteria["transparency_and_reporting_readiness"] = _criterion(
            "pass",
            "none",
            "Transparency pathways are declared at the current core threshold.",
            None,
            [transparency_anchor],
        )

    if integrity["status"] == "escalate":
        criteria["integrity_and_policy_readiness"] = _criterion(
            "fail",
            "fatal",
            "Integrity or policy signals require human review before submission readiness can be judged.",
            "Resolve authorship, overlap, image, or ethics concerns through human review before any submission action.",
            [integrity_anchor],
        )
    elif integrity["status"] == "flagged":
        criteria["integrity_and_policy_readiness"] = _criterion(
            "borderline",
            "major",
            "Policy-sensitive signals remain unresolved.",
            "Clarify the flagged policy surface and document the resolution path.",
            [integrity_anchor],
        )
    else:
        criteria["integrity_and_policy_readiness"] = _criterion(
            "pass",
            "none",
            "No integrity blocker is visible at the core screening level.",
            None,
            [integrity_anchor],
        )

    fatal_failures: list[str] = []
    repairable_failures: list[str] = []
    major_concerns: list[dict[str, Any]] = []
    name_map = {
        "problem_definition_and_claim_clarity": "unrecoverable_or_unstable_central_claim",
        "methodological_legibility": "no_assessable_method_model_or_protocol",
        "evidence_to_claim_alignment": "fundamental_evidence_to_claim_mismatch",
        "literature_positioning": "literature_positioning_underpowered",
        "transparency_and_reporting_readiness": "transparency_or_reporting_incomplete",
        "integrity_and_policy_readiness": "integrity_or_policy_blocker",
    }
    for criterion_name, detail in criteria.items():
        if detail["status"] == "fail" and detail["severity"] == "fatal":
            fatal_failures.append(name_map[criterion_name])
        elif detail["status"] == "fail":
            repairable_failures.append(name_map[criterion_name])
        elif detail["status"] == "borderline":
            repairable_failures.append(name_map[criterion_name])
        if detail["status"] in {"fail", "borderline"}:
            major_concerns.append(
                {
                    "criterion": criterion_name,
                    "severity": detail["severity"],
                    "why_it_fails": detail["why"],
                    "required_evidence_or_revision": detail["required_repair"],
                    "evidence_anchors": detail["evidence_anchors"],
                }
            )

    # Fatal failures represent states APR treats as non-sendable. Borderline and
    # non-fatal failures remain part of the scientific record because they are
    # repair targets, not proof that the manuscript is unassessable.
    if fatal_failures:
        status = "fatal_fail"
    elif any(detail["status"] == "fail" for detail in criteria.values()):
        status = "repairable_fail"
    elif any(detail["status"] == "borderline" for detail in criteria.values()):
        status = "borderline"
    else:
        status = "pass"

    evidence_summary = (
        f"support_object={support_anchor['kind'] if support_anchor else 'none'}; "
        f"references={ref_count}; transparency={transparency['status']}; integrity={integrity['status']}"
    )
    return {
        "status": status,
        "criteria": criteria,
        "fatal_failures": fatal_failures,
        "repairable_failures": repairable_failures,
        "major_concerns": major_concerns,
        "evidence_summary": evidence_summary,
    }
