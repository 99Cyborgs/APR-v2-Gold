from __future__ import annotations

from typing import Any

from apr_core.models import NormalizedManuscriptPackage

STRING_FIELDS = [
    "manuscript_id",
    "title",
    "abstract",
    "manuscript_text",
    "supplement_or_appendix",
    "target_venue",
    "target_audience",
    "outlet_profile_hint",
    "declared_article_type",
    "data_availability",
    "code_availability",
    "materials_availability",
    "ethics_and_disclosures",
    "reporting_checklist",
    "author_response_to_reviews",
    "reviewer_notes",
]

LIST_FIELDS = [
    "figures_and_captions",
    "tables",
    "references",
    "prior_reviews",
    "external_constraints",
]


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or None
    text = str(value).strip()
    return [text] if text else None


def normalize_input(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {"audit_mode": payload["audit_mode"]}
    for field in STRING_FIELDS:
        cleaned[field] = _clean_string(payload.get(field))
    for field in LIST_FIELDS:
        cleaned[field] = _clean_list(payload.get(field))
    package = NormalizedManuscriptPackage(**cleaned)
    return package.as_dict()


def grade_input_sufficiency(payload: dict[str, Any]) -> dict[str, Any]:
    missing_inputs: list[str] = []
    if not payload.get("title"):
        missing_inputs.append("title")
    if not payload.get("abstract"):
        missing_inputs.append("abstract")
    if not payload.get("manuscript_text"):
        missing_inputs.append("manuscript_text")
    if not payload.get("references"):
        missing_inputs.append("references")
    if not payload.get("figures_and_captions") and not payload.get("tables"):
        missing_inputs.append("support_objects")

    if payload.get("abstract") and not payload.get("manuscript_text") and not payload.get("figures_and_captions") and not payload.get("tables"):
        document_state = "abstract_only"
    elif payload.get("manuscript_text") and payload.get("references") and (payload.get("figures_and_captions") or payload.get("tables")):
        document_state = "complete_manuscript"
    else:
        document_state = "partial_manuscript"

    coverage = sum(
        1
        for present in [
            payload.get("title"),
            payload.get("abstract"),
            payload.get("manuscript_text"),
            payload.get("references"),
            payload.get("figures_and_captions") or payload.get("tables"),
        ]
        if present
    )

    if coverage >= 5:
        grade = "high"
    elif coverage >= 3:
        grade = "medium"
    else:
        grade = "low"

    provisional_limitations: list[str] = []
    if not payload.get("target_venue"):
        provisional_limitations.append("target_venue_unspecified")
    if not payload.get("references"):
        provisional_limitations.append("literature_context_thin")
    if not payload.get("data_availability") and not payload.get("code_availability"):
        provisional_limitations.append("transparency_pathways_thin")
    if not payload.get("manuscript_text"):
        provisional_limitations.append("full_body_missing")

    return {
        "grade": grade,
        "document_state": document_state,
        "missing_inputs": missing_inputs,
        "provisional_limitations": provisional_limitations,
    }


def build_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "manuscript_id": payload.get("manuscript_id"),
        "title": payload.get("title"),
        "target_venue": payload.get("target_venue"),
        "target_audience": payload.get("target_audience"),
        "outlet_profile_hint": payload.get("outlet_profile_hint"),
        "declared_article_type": payload.get("declared_article_type"),
    }
