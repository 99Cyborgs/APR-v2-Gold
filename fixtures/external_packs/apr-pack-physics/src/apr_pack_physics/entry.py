from __future__ import annotations

import re
from typing import Any

from apr_core.packs.protocol import PackSpec

BROAD_SCOPE = ["universal", "unification", "fundamental", "all orbital phenomena"]
OBSERVABLE = ["observable", "measurable", "spectroscopy", "signal", "signature", "benchmark"]
DISTINGUISH = ["distinguish", "signature", "different from", "compared with", "baseline"]
LIMITING = ["limit", "reduces to", "recovers", "known result", "weak-drive", "weak drive"]
FORMAL = ["hamiltonian", "lagrangian", "equation", "theorem", "derive", "proof"]
EOM = ["equations of motion", "variational", "euler-lagrange", "time evolution", "lindblad"]
_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _text(payload: dict[str, Any]) -> str:
    return " ".join(filter(None, [payload.get("title"), payload.get("abstract"), payload.get("manuscript_text")])).lower()


def _segments(payload: dict[str, Any]) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    if payload.get("title"):
        segments.append({"location": "Title", "quote": payload["title"]})
    for index, sentence in enumerate(_SPLIT.split((payload.get("abstract") or "").strip()), start=1):
        if sentence.strip():
            segments.append({"location": f"Abstract:s{index}", "quote": sentence.strip()})
    for index, sentence in enumerate(_SPLIT.split((payload.get("manuscript_text") or "").strip()), start=1):
        if sentence.strip():
            segments.append({"location": f"Body:s{index}", "quote": sentence.strip()})
    for index, figure in enumerate(payload.get("figures_and_captions") or [], start=1):
        segments.append({"location": f"Figure:{index}", "quote": figure})
    return segments


def _dedupe(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, str]] = []
    for item in items:
        key = (item["location"], item["quote"])
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _search(payload: dict[str, Any], phrases: list[str], max_hits: int = 3) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for segment in _segments(payload):
        quote = segment["quote"].lower()
        if any(phrase in quote for phrase in phrases):
            hits.append(segment)
            if len(hits) >= max_hits:
                break
    return _dedupe(hits)


def run_pack(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    domain = record["classification"]["domain_module"]
    if domain not in {"theory_physics_or_applied_math", "computational_or_simulation"}:
        return {
            "status": "not_applicable",
            "warnings": [f"physics pack not applicable to domain_module={domain}"],
            "signals": [],
            "human_escalation_required": False,
            "fatal_gates": [],
            "evidence_anchors": [],
            "advisory_fields": {}
        }

    text = _text(payload)
    broad_scope = any(phrase in text for phrase in BROAD_SCOPE)
    observable_visible = any(phrase in text for phrase in OBSERVABLE)
    discriminating_visible = any(phrase in text for phrase in DISTINGUISH)
    limit_visible = any(phrase in text for phrase in LIMITING)
    formal_visible = any(phrase in text for phrase in FORMAL) or bool(record["parsing"].get("first_hard_object"))
    eom_visible = any(phrase in text for phrase in EOM)

    anchors = _dedupe(_search(payload, BROAD_SCOPE, 2) + _search(payload, OBSERVABLE, 2) + _search(payload, LIMITING, 2) + _search(payload, FORMAL + DISTINGUISH, 3))
    signals: list[str] = []
    warnings: list[str] = []
    fatal_gates: list[dict[str, Any]] = []

    if broad_scope:
        signals.append("broad_scope_language_detected")
        warnings.append("broad or revisionary scope language is visible")
    if formal_visible:
        signals.append("formal_object_visible")
    if observable_visible:
        signals.append("observable_anchor_visible")
    if discriminating_visible:
        signals.append("discriminating_consequence_language_visible")
    if limit_visible:
        signals.append("limiting_case_language_visible")
    if "hamiltonian" in text or "lagrangian" in text:
        signals.append("hamiltonian_or_lagrangian_claim_visible")
        if not eom_visible:
            warnings.append("formal dynamics language is visible without an obvious equations-of-motion surface")

    if record["classification"]["article_type"] == "theory_or_model" and not observable_visible and not discriminating_visible:
        fatal_gates.append(
            {
                "code": "missing_observable_or_discriminating_consequence",
                "reason": "theory/model manuscript lacks a visible observable anchor or discriminating consequence",
                "scope": "physics_pack_advisory",
                "evidence_anchors": anchors
            }
        )

    if fatal_gates:
        status = "fail"
    elif broad_scope or not limit_visible or not discriminating_visible:
        status = "borderline"
    else:
        status = "pass"

    return {
        "status": status,
        "warnings": warnings,
        "signals": signals,
        "human_escalation_required": bool(fatal_gates or (broad_scope and not observable_visible)),
        "fatal_gates": fatal_gates,
        "evidence_anchors": anchors,
        "advisory_fields": {
            "physics_credibility": {
                "observable_anchor_visible": observable_visible,
                "discriminating_consequence_visible": discriminating_visible,
                "limiting_case_language_visible": limit_visible,
                "formal_object_visible": formal_visible,
                "equations_of_motion_or_variational_surface_visible": eom_visible,
                "broad_scope_language_visible": broad_scope
            }
        }
    }


def build_pack() -> PackSpec:
    return PackSpec(
        pack_id="physics_pack",
        version="0.1.0",
        api_version=1,
        display_name="APR Physics Pack",
        advisory_only=True,
        supported_domains=["theory_physics_or_applied_math", "computational_or_simulation"],
        run=run_pack,
    )
