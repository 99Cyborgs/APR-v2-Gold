from __future__ import annotations

from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors


def _pathway(statement: str | None) -> str:
    if not statement:
        return "missing"
    text = statement.lower()
    if "not applicable" in text or "no additional materials" in text:
        return "not_applicable"
    if any(token in text for token in ["public", "github", "zenodo", "repository", "archived"]):
        return "public_repository"
    if any(token in text for token in ["on request", "upon request", "available on request"]):
        return "available_on_request"
    if any(token in text for token in ["appendix", "supplement"]):
        return "supplement_or_appendix"
    if any(token in text for token in ["cannot be shared", "restricted", "sensitive"]):
        return "restricted_non_public"
    return "declared_unspecified"


def _expected_surfaces(classification: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, bool, bool]:
    article_type = classification["article_type"]
    domain_module = classification["domain_module"]
    if article_type in {"commentary_or_perspective", "editorial_or_opinion", "review", "systematic_review"}:
        return (False, False, False)
    if article_type == "theory_or_model":
        code_expected = domain_module == "computational_or_simulation" or "simulation" in (payload.get("manuscript_text") or "").lower()
        return (False, code_expected, False)
    data_expected = True
    code_expected = article_type in {"methods_or_tools", "replication_or_validation", "original_research", "constraint_or_null_result"}
    materials_expected = article_type in {"methods_or_tools", "protocol_or_registered_report"}
    return (data_expected, code_expected, materials_expected)


def assess_transparency(payload: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    data_expected, code_expected, materials_expected = _expected_surfaces(classification, payload)
    data_pathway = _pathway(payload.get("data_availability"))
    code_pathway = _pathway(payload.get("code_availability"))
    materials_pathway = _pathway(payload.get("materials_availability"))

    missing_items: list[str] = []
    if data_expected and data_pathway == "missing":
        missing_items.append("data_availability")
    if code_expected and code_pathway == "missing":
        missing_items.append("code_availability")
    if materials_expected and materials_pathway == "missing":
        missing_items.append("materials_availability")

    expected_any = data_expected or code_expected or materials_expected
    present_any = any(pathway != "missing" for pathway in [data_pathway, code_pathway, materials_pathway])
    if not expected_any:
        status = "not_applicable"
    elif not present_any:
        status = "missing"
    elif missing_items:
        status = "incomplete"
    else:
        status = "declared"

    anchors = dedupe_anchors(
        [
            *search_anchors(
                payload,
                ["data", "code", "repository", "zenodo", "available on request", "supplement", "materials"],
                max_hits=4,
            ),
            first_anchor_from_fields(payload, ["ethics_and_disclosures", "supplement_or_appendix", "manuscript_text"]),
        ]
    )

    return {
        "status": status,
        "data_pathway": data_pathway if data_expected or data_pathway != "missing" else "not_applicable",
        "code_pathway": code_pathway if code_expected or code_pathway != "missing" else "not_applicable",
        "materials_pathway": materials_pathway if materials_expected or materials_pathway != "missing" else "not_applicable",
        "missing_items": missing_items,
        "evidence_anchors": anchors,
    }
