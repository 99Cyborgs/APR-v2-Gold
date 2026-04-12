from __future__ import annotations

import re
from typing import Any

from jsonschema import validate

from apr_core.defense_readiness import DEFAULT_DEFENSE_CONTEXT, build_defense_readiness_record
from apr_core.policy import load_pdf_annotation_manifest_schema
from apr_core.question_generation import build_question_challenge_record
from apr_core.utils import stable_json_sha256
from apr_core.derived_utils import artifact_provenance, collect_evidence_anchors, severity_from_score

_PAGE_RE = re.compile(r"page\s+(?P<page>\d+)", re.IGNORECASE)


def _annotation_source(anchor: dict[str, str] | None) -> dict[str, Any]:
    if not anchor:
        return {
            "source_type": "fallback",
            "location": "fallback",
            "page_number": None,
            "text_quote": "",
        }
    location = anchor.get("location", "fallback")
    match = _PAGE_RE.search(location)
    page_number = int(match.group("page")) if match else None
    return {
        "source_type": "text_span",
        "location": location,
        "page_number": page_number,
        "text_quote": anchor.get("quote", ""),
    }


def _drilldown_entry(
    *,
    drilldown_id: str,
    title: str,
    summary: str,
    evidence: list[dict[str, str]],
    linked_risk_items: list[str],
    linked_question_items: list[str],
    mitigation_notes: list[str],
) -> dict[str, Any]:
    return {
        "drilldown_id": drilldown_id,
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "linked_risk_items": linked_risk_items,
        "linked_question_items": linked_question_items,
        "mitigation_notes": mitigation_notes,
    }


def build_pdf_annotation_manifest(
    canonical_record: dict[str, Any],
    *,
    payload: dict[str, Any] | None = None,
    defense_record: dict[str, Any] | None = None,
    question_record: dict[str, Any] | None = None,
    source_pdf_path: str | None = None,
    context_type: str = DEFAULT_DEFENSE_CONTEXT,
) -> dict[str, Any]:
    defense_record = defense_record or build_defense_readiness_record(
        canonical_record,
        payload=payload,
        context_type=context_type,
    )
    question_record = question_record or build_question_challenge_record(
        canonical_record,
        defense_record=defense_record,
        context_type=context_type,
    )

    annotations: list[dict[str, Any]] = []
    drilldowns: list[dict[str, Any]] = []
    risk_by_id = {risk["risk_id"]: risk for risk in defense_record.get("risk_items", [])}

    for index, strength in enumerate(defense_record.get("strength_anchors", []), start=1):
        anchor = (strength.get("evidence_anchors") or [None])[0]
        source = _annotation_source(anchor)
        drilldown_id = f"strength-{index}"
        annotations.append(
            {
                "annotation_id": f"strength-{index}",
                **source,
                "category": "strength_anchor",
                "severity": "positive",
                "linked_artifact_paths": [f"strength_anchors[{index - 1}]"],
                "short_inline_label": strength["label"],
                "suggested_repair_note": None,
                "drilldown_id": drilldown_id,
            }
        )
        drilldowns.append(
            _drilldown_entry(
                drilldown_id=drilldown_id,
                title=strength["label"],
                summary=strength["summary"],
                evidence=strength.get("evidence_anchors", []),
                linked_risk_items=[],
                linked_question_items=[],
                mitigation_notes=[],
            )
        )

    for index, weakness in enumerate(defense_record.get("weakness_anchors", []), start=1):
        anchor = (weakness.get("evidence_anchors") or [None])[0]
        source = _annotation_source(anchor)
        drilldown_id = f"weakness-{index}"
        annotations.append(
            {
                "annotation_id": f"weakness-{index}",
                **source,
                "category": "weakness_anchor",
                "severity": "moderate",
                "linked_artifact_paths": [f"weakness_anchors[{index - 1}]"],
                "short_inline_label": weakness["label"],
                "suggested_repair_note": None,
                "drilldown_id": drilldown_id,
            }
        )
        drilldowns.append(
            _drilldown_entry(
                drilldown_id=drilldown_id,
                title=weakness["label"],
                summary=weakness["summary"],
                evidence=weakness.get("evidence_anchors", []),
                linked_risk_items=[],
                linked_question_items=[],
                mitigation_notes=[],
            )
        )

    for index, risk in enumerate(defense_record.get("risk_items", []), start=1):
        if risk["current_answerability"] == "not_applicable":
            continue
        anchor = (risk.get("evidence_anchors") or [None])[0]
        source = _annotation_source(anchor)
        drilldown_id = f"risk-{index}"
        annotations.append(
            {
                "annotation_id": f"risk-{index}",
                **source,
                "category": "risk_anchor",
                "severity": risk["severity"],
                "linked_artifact_paths": [f"risk_items[{index - 1}]"],
                "short_inline_label": risk["category"].replace("_risk", "").replace("_", " "),
                "suggested_repair_note": risk["mitigation_path"],
                "drilldown_id": drilldown_id,
            }
        )
        if risk["current_answerability"] in {"weak", "missing"}:
            annotations.append(
                {
                    "annotation_id": f"ambiguity-{index}",
                    **source,
                    "category": "ambiguity_anchor",
                    "severity": severity_from_score(risk["score"]),
                    "linked_artifact_paths": [f"risk_items[{index - 1}]"],
                    "short_inline_label": "answer gap",
                    "suggested_repair_note": risk["mitigation_path"],
                    "drilldown_id": drilldown_id,
                }
            )
        drilldowns.append(
            _drilldown_entry(
                drilldown_id=drilldown_id,
                title=risk["category"].replace("_", " "),
                summary=risk["rationale"],
                evidence=risk.get("evidence_anchors", []),
                linked_risk_items=[risk["risk_id"]],
                linked_question_items=[],
                mitigation_notes=[risk["mitigation_path"]],
            )
        )

    for index, question in enumerate(question_record.get("questions", []), start=1):
        anchor = (question.get("evidence_anchors") or [None])[0]
        source = _annotation_source(anchor)
        drilldown_id = f"question-{index}"
        annotations.append(
            {
                "annotation_id": f"question-{index}",
                **source,
                "category": "question_anchor",
                "severity": question["risk_if_asked"]["severity"],
                "linked_artifact_paths": [f"questions[{index - 1}]"],
                "short_inline_label": question["category"].replace("_", " "),
                "suggested_repair_note": question["mitigation_or_prep_action"],
                "drilldown_id": drilldown_id,
            }
        )
        drilldowns.append(
            _drilldown_entry(
                drilldown_id=drilldown_id,
                title=question["question_text"],
                summary=question["why_this_manuscript_will_be_asked"],
                evidence=question.get("evidence_anchors", []),
                linked_risk_items=question.get("linked_risk_ids", []),
                linked_question_items=[question["challenge_id"]],
                mitigation_notes=[question["mitigation_or_prep_action"]],
            )
        )

    for priority in defense_record.get("recommended_mitigation_priorities", []):
        risk_id = (priority.get("linked_risk_ids") or [None])[0]
        risk = risk_by_id.get(risk_id)
        anchor = (risk.get("evidence_anchors") or [None])[0] if risk else None
        source = _annotation_source(anchor)
        drilldown_id = f"repair-{priority['priority_rank']}"
        annotations.append(
            {
                "annotation_id": f"repair-{priority['priority_rank']}",
                **source,
                "category": "repair_anchor",
                "severity": risk["severity"] if risk else "moderate",
                "linked_artifact_paths": [f"recommended_mitigation_priorities[{priority['priority_rank'] - 1}]"],
                "short_inline_label": f"repair {priority['priority_rank']}",
                "suggested_repair_note": priority["action"],
                "drilldown_id": drilldown_id,
            }
        )
        drilldowns.append(
            _drilldown_entry(
                drilldown_id=drilldown_id,
                title=priority["title"],
                summary=priority["reason"],
                evidence=collect_evidence_anchors(risk.get("evidence_anchors") if risk else []),
                linked_risk_items=priority.get("linked_risk_ids", []),
                linked_question_items=[],
                mitigation_notes=[priority["action"]],
            )
        )

    record = {
        "artifact_type": "PdfAnnotationManifest",
        "schema_version": "1.0.0",
        "viewer_mode": "text_facsimile_with_source_pdf" if source_pdf_path else "text_facsimile",
        "source": {
            "manuscript_id": canonical_record.get("metadata", {}).get("manuscript_id"),
            "title": canonical_record.get("metadata", {}).get("title"),
            "canonical_record_sha256": stable_json_sha256(canonical_record),
            "defense_record_sha256": stable_json_sha256(defense_record),
            "question_record_sha256": stable_json_sha256(question_record),
            "source_pdf_path": source_pdf_path,
        },
        "annotations": annotations,
        "drilldowns": drilldowns,
        "provenance": artifact_provenance(canonical_record),
    }
    validate(instance=record, schema=load_pdf_annotation_manifest_schema())
    return record
