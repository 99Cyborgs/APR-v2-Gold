from __future__ import annotations

import re
from typing import Any

from apr_core.packs.protocol import PackSpec

COHORT = ["cohort", "patient", "participants", "prospective", "retrospective", "ward"]
ENDPOINT = ["primary endpoint", "endpoint", "sensitivity", "specificity", "auc", "mortality", "escalation"]
SAFETY = ["adverse event", "safety", "harm", "complication", "toxicity"]
ETHICS = ["irb", "institutional review board", "ethics approval", "consent waiver"]
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
    for index, table in enumerate(payload.get("tables") or [], start=1):
        segments.append({"location": f"Table:{index}", "quote": table})
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
    text = _text(payload)
    cohort_visible = any(token in text for token in COHORT)
    endpoint_visible = any(token in text for token in ENDPOINT)
    safety_visible = any(token in text for token in SAFETY)
    ethics_visible = any(token in text for token in ETHICS)

    anchors = _dedupe(
        _search(payload, COHORT, 2)
        + _search(payload, ENDPOINT, 2)
        + _search(payload, SAFETY + ETHICS, 2)
    )

    signals: list[str] = []
    warnings: list[str] = []
    if cohort_visible:
        signals.append("clinical_cohort_surface_visible")
    if endpoint_visible:
        signals.append("clinical_endpoint_surface_visible")
    if safety_visible:
        signals.append("adverse_event_surface_visible")
    if ethics_visible:
        signals.append("ethics_or_irb_surface_visible")

    if not endpoint_visible:
        warnings.append("no explicit endpoint surface is visible for the clinical manuscript")
    if not safety_visible:
        warnings.append("no explicit adverse-event or safety surface is visible")
    if not ethics_visible:
        warnings.append("no explicit ethics or irb surface is visible in the clinical manuscript")

    status = "pass" if cohort_visible and endpoint_visible and ethics_visible else "borderline"

    return {
        "status": status,
        "warnings": warnings,
        "signals": signals,
        "human_escalation_required": False,
        "fatal_gates": [],
        "evidence_anchors": anchors,
        "advisory_fields": {
            "clinical_readiness": {
                "cohort_surface_visible": cohort_visible,
                "endpoint_surface_visible": endpoint_visible,
                "adverse_event_surface_visible": safety_visible,
                "ethics_surface_visible": ethics_visible,
            }
        },
    }


def build_pack() -> PackSpec:
    return PackSpec(
        pack_id="clinical_pack",
        version="0.1.0",
        api_version=1,
        display_name="APR Clinical Pack",
        advisory_only=True,
        supported_domains=["clinical_or_human_subjects"],
        run=run_pack,
    )
