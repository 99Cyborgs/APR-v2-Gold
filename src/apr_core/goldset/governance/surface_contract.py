from __future__ import annotations

from typing import Any
import warnings

LEGACY_SCORE_FIELDS = {"scientific_score"}
NATIVE_SCORE_FIELDS = {"scientific_vector", "scientific_score_vector"}
ENFORCED_SECTIONS = {"root", "input", "ingestion", "scoring", "aggregation"}
SURFACE_CONTRACT_MIXED_REASON = "surface_contract_mixed_namespace"
MODE_DISABLED = "disabled"
MODE_STRICT = "strict"
MODE_WARN_ONLY = "warn_only"


class SurfaceContractViolation(ValueError):
    """Raised when legacy and native scientific score surfaces are consumed together."""

    def __init__(
        self,
        message: str,
        *,
        reason_codes: list[str] | None = None,
        mixed_sections: list[str] | None = None,
        enforcement_mode: str = MODE_STRICT,
        warning_mode_active: bool = False,
    ) -> None:
        super().__init__(message)
        self.reason_codes = list(reason_codes or [])
        self.mixed_sections = list(mixed_sections or [])
        self.enforcement_mode = enforcement_mode
        self.warning_mode_active = warning_mode_active


def _normalize_reason_codes(reason_codes: list[str] | None) -> list[str]:
    return sorted(dict.fromkeys(reason_code for reason_code in (reason_codes or []) if reason_code))


def classify_surface_contract_mode(*, enabled: bool, strict_surface_contract: bool = True) -> str:
    if not enabled:
        return MODE_DISABLED
    return MODE_STRICT if strict_surface_contract else MODE_WARN_ONLY


def build_scientific_surface_bundle(
    *,
    legacy_surface: dict[str, Any],
    native_surface: dict[str, Any],
    alias_surface: dict[str, Any] | None = None,
    alias_key: str = "scientific_score_vector",
    legacy_key: str = "scientific_score_vector_legacy",
    native_key: str = "scientific_score_vector_native",
) -> dict[str, dict[str, Any]]:
    resolved_alias = native_surface if alias_surface is None else alias_surface
    return {
        alias_key: resolved_alias,
        legacy_key: legacy_surface,
        native_key: native_surface,
    }


def _section_payloads(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    root_payload = {key: value for key, value in payload.items() if key in LEGACY_SCORE_FIELDS | NATIVE_SCORE_FIELDS}
    if root_payload:
        sections["root"] = root_payload
    for section in ("input", "ingestion", "scoring", "aggregation", "export"):
        section_payload = payload.get(section)
        if isinstance(section_payload, dict):
            sections[section] = section_payload
    return sections


def _section_status(section_payload: dict[str, Any]) -> dict[str, bool]:
    legacy_surface_used = any(field in section_payload for field in LEGACY_SCORE_FIELDS)
    native_surface_used = any(field in section_payload for field in NATIVE_SCORE_FIELDS)
    return {
        "legacy_surface_used": legacy_surface_used,
        "native_surface_used": native_surface_used,
        "legacy_present": legacy_surface_used,
        "native_present": native_surface_used,
        "mixed_usage_violation": bool(legacy_surface_used and native_surface_used),
    }


def validate_score_namespace(payload):
    sections = _section_payloads(dict(payload or {}))
    per_section = {section: _section_status(section_payload) for section, section_payload in sections.items()}
    legacy_surface_used = any(
        status["legacy_surface_used"] for section, status in per_section.items() if section in ENFORCED_SECTIONS
    )
    native_surface_used = any(
        status["native_surface_used"] for section, status in per_section.items() if section in ENFORCED_SECTIONS
    )
    legacy_present = any(status["legacy_present"] for status in per_section.values())
    native_present = any(status["native_present"] for status in per_section.values())
    mixed_sections = sorted(
        section
        for section, status in per_section.items()
        if section in ENFORCED_SECTIONS and status["mixed_usage_violation"]
    )
    reason_codes = [SURFACE_CONTRACT_MIXED_REASON] if mixed_sections else []
    return {
        "legacy_present": legacy_present,
        "native_present": native_present,
        "legacy_surface_used": legacy_surface_used,
        "native_surface_used": native_surface_used,
        "mixed_usage_violation": bool(mixed_sections),
        "mixed_sections": mixed_sections,
        "reason_codes": reason_codes,
        "status": "mixed_usage_violation" if mixed_sections else "ok",
    }


def enforce_surface_exclusivity(payload, *, strict_surface_contract: bool = True):
    status = validate_score_namespace(payload)
    status["enforcement_mode"] = classify_surface_contract_mode(enabled=True, strict_surface_contract=strict_surface_contract)
    status["warning_mode_active"] = status["enforcement_mode"] == MODE_WARN_ONLY
    status["reason_codes"] = _normalize_reason_codes(status.get("reason_codes"))
    if status["mixed_usage_violation"]:
        sections = ", ".join(status["mixed_sections"]) or "unknown"
        message = f"scientific_score and scientific_score_vector may not be consumed together in {sections}"
        if strict_surface_contract:
            raise SurfaceContractViolation(
                message,
                reason_codes=status["reason_codes"],
                mixed_sections=status["mixed_sections"],
                enforcement_mode=status["enforcement_mode"],
                warning_mode_active=status["warning_mode_active"],
            )
        warnings.warn(message, RuntimeWarning, stacklevel=2)
    return status


def _require_property(schema: dict[str, Any], container_path: list[str], property_name: str) -> None:
    cursor = schema
    for segment in container_path:
        cursor = cursor[segment]
    properties = cursor.get("properties", {})
    if property_name not in properties:
        raise ValueError(f"schema is missing declared property: {'.'.join(container_path + [property_name])}")


def validate_governance_schema_contract(summary_schema: dict[str, Any], ledger_schema: dict[str, Any]) -> None:
    for property_name in ("leakage_guard", "counterfactual_extended", "invariance_trace", "surface_contract"):
        _require_property(summary_schema, ["$defs", "caseResult"], property_name)
        _require_property(summary_schema, ["$defs", "calibrationExtended"], property_name)
        _require_property(ledger_schema, ["properties", "case_outcomes", "items"], property_name)
    for property_name in ("conditional_importance", "interaction_matrix", "identifiability_status"):
        _require_property(summary_schema, ["$defs", "counterfactualExtended"], property_name)
        _require_property(ledger_schema, ["$defs", "counterfactualExtended"], property_name)
