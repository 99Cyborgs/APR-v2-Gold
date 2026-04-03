from __future__ import annotations

"""Dataclasses for APR's canonical in-memory contract shapes.

These types improve structural discipline, but most governance-bearing surfaces
remain intentionally open dictionaries because the authoritative semantics live
in the active schemas and policy layer. Treat these classes as transport shells,
not as a substitute for schema and semantic validation.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class EvidenceAnchor:
    location: str
    quote: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class HardObject:
    kind: str
    location: str
    quote: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class CriterionAssessment:
    status: str
    severity: str
    why: str
    required_repair: str | None
    evidence_anchors: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NormalizedManuscriptPackage:
    audit_mode: str
    manuscript_id: str | None
    title: str | None
    abstract: str | None
    manuscript_text: str | None
    figures_and_captions: list[str] | None
    tables: list[str] | None
    references: list[str] | None
    supplement_or_appendix: str | None
    target_venue: str | None
    target_audience: str | None
    outlet_profile_hint: str | None
    declared_article_type: str | None
    data_availability: str | None
    code_availability: str | None
    materials_availability: str | None
    ethics_and_disclosures: str | None
    reporting_checklist: str | None
    prior_reviews: list[str] | None
    author_response_to_reviews: str | None
    reviewer_notes: str | None
    external_constraints: list[str] | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CanonicalAuditRecord:
    # These nested mappings carry contract-governed semantics that exceed Python
    # typing. They must stay aligned with the canonical record schema and the
    # pipeline's semantic gates, not merely with this dataclass field list.
    contract_version: str
    policy_layer_version: str
    audit_mode: str
    metadata: dict[str, Any]
    input_sufficiency: dict[str, Any]
    parsing: dict[str, Any]
    classification: dict[str, Any]
    reviewability: dict[str, Any]
    transparency: dict[str, Any]
    integrity: dict[str, Any]
    scientific_record: dict[str, Any]
    venue: dict[str, Any]
    rehabilitation: dict[str, Any]
    pack_execution: dict[str, Any]
    pack_results: list[dict[str, Any]]
    decision: dict[str, Any]
    provenance: dict[str, Any]
    rendering: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
