from __future__ import annotations

import re
from typing import Any

from apr_core.anchors import dedupe_anchors, detect_decisive_support_object, detect_first_hard_object, segment_payload

CLAIM_MARKERS = [
    "we present",
    "we show",
    "we derive",
    "we report",
    "we develop",
    "we benchmark",
    "we reanalyze",
    "we replicate",
    "we rerun",
    "we propose",
    "we constrain",
]
NOVELTY_MARKERS = ["first", "new", "novel", "improves", "reduces", "differs", "outperforms", "independent"]
BROAD_MARKERS = ["universal", "paradigm", "all orbital phenomena", "framework for all", "overturns"]
RESULT_MARKERS = ["results", "agreement", "reduces", "improves", "constraint", "signature", "benchmark"]
COMPARISON_MARKERS = [
    "relative to",
    "compared with",
    "compared to",
    "baseline",
    "does not persist",
    "did not persist",
    "replicate",
    "replication",
]
WORD_RE = re.compile(r"[A-Za-z]{4,}")


def _score(unit: dict[str, str]) -> int:
    quote = unit["quote"].lower()
    location = unit["location"]
    score = 0
    if location.startswith("Title"):
        score += 2
    if location.startswith("Abstract"):
        score += 4
    if location.startswith("Body"):
        score += 2
    if location.startswith(("Abstract:s1", "Abstract:s2")):
        score += 1
    if any(marker in quote for marker in CLAIM_MARKERS):
        score += 4
    if any(marker in quote for marker in NOVELTY_MARKERS):
        score += 2
    if any(marker in quote for marker in RESULT_MARKERS):
        score += 1
    if 25 <= len(unit["quote"]) <= 280:
        score += 1
    return score


def _novelty_candidate(
    ranked: list[dict[str, str]],
    central_unit: dict[str, str] | None,
) -> tuple[str | None, dict[str, str] | None]:
    for unit in ranked:
        quote = unit["quote"].lower()
        if any(marker in quote for marker in NOVELTY_MARKERS):
            return unit["quote"], unit
    if central_unit:
        central_quote = central_unit["quote"].lower()
        if any(marker in central_quote for marker in CLAIM_MARKERS) and any(
            marker in central_quote for marker in COMPARISON_MARKERS
        ):
            return central_unit["quote"], central_unit
    return (ranked[0]["quote"], ranked[0]) if ranked else (None, None)


def _contradictions(payload: dict[str, Any], central_claim: str | None, support_object: dict[str, str] | None) -> list[str]:
    text = " ".join(filter(None, [payload.get("title"), payload.get("abstract"), payload.get("manuscript_text")])).lower()
    flags: list[str] = []
    if "systematic review" in text and not payload.get("reporting_checklist"):
        flags.append("systematic_review_without_reporting_trace")
    if "protocol" in text and any(term in text for term in ["we show", "we report", "results", "we observed"]):
        flags.append("protocol_language_mixed_with_result_language")
    if "commentary" in text and any(term in text for term in ["we benchmark", "we derive", "we constrain"]):
        flags.append("commentary_language_mixed_with_primary_research_claims")
    if central_claim and any(marker in central_claim.lower() for marker in BROAD_MARKERS) and not support_object:
        flags.append("broad_claim_without_visible_support")
    return flags


def _confidence(payload: dict[str, Any], ranked: list[dict[str, str]], support_object: dict[str, str] | None) -> float:
    confidence = 0.0
    if ranked:
        confidence += 0.3
    if payload.get("abstract"):
        confidence += 0.15
    if payload.get("manuscript_text"):
        confidence += 0.15
    if payload.get("references"):
        confidence += 0.1
    if support_object:
        confidence += 0.15
    if len(ranked) >= 3:
        confidence += 0.1
    if ranked and any(marker in ranked[0]["quote"].lower() for marker in CLAIM_MARKERS):
        confidence += 0.05
    title = payload.get("title") or ""
    abstract = payload.get("abstract") or ""
    if len(set(WORD_RE.findall(title.lower())) & set(WORD_RE.findall(abstract.lower()))) >= 2:
        confidence += 0.05
    return round(min(1.0, confidence), 2)


def _provisional_claim_type(payload: dict[str, Any]) -> str | None:
    text = " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                payload.get("declared_article_type"),
            ],
        )
    ).lower()
    article_type = (payload.get("declared_article_type") or "").strip().lower()
    if article_type in {"commentary_or_perspective", "editorial_or_opinion"}:
        return "opinion_claim"
    if article_type in {"review", "systematic_review"}:
        return "synthesis_claim"
    if article_type == "protocol_or_registered_report":
        return "protocol_claim"
    if article_type == "replication_or_validation":
        return "replication_claim"
    if article_type == "constraint_or_null_result":
        return "null_result_claim"
    if article_type == "theory_or_model":
        return "model_claim"
    if article_type == "methods_or_tools":
        return "benchmark_claim"
    if any(token in text for token in ("replication", "replicate", "rerun", "validation")):
        return "replication_claim"
    if any(token in text for token in ("null result", "does not persist", "did not persist", "constraint")):
        return "null_result_claim"
    if any(token in text for token in ("theorem", "lagrangian", "hamiltonian", "derive")):
        return "model_claim"
    if any(token in text for token in ("benchmark", "baseline", "compare", "compares")):
        return "benchmark_claim"
    if "protocol" in text:
        return "protocol_claim"
    if text:
        return "empirical_claim"
    return None


def extract_claims(payload: dict[str, Any]) -> dict[str, Any]:
    units = [
        unit
        for unit in segment_payload(payload)
        if not unit["location"].startswith(("Ref", "Disclosures", "ReviewerNotes"))
    ]
    ranked = sorted(units, key=_score, reverse=True)
    central_unit = ranked[0] if ranked and _score(ranked[0]) > 0 else (units[0] if units else None)
    first_hard_object = detect_first_hard_object(payload)
    decisive_support_object = detect_decisive_support_object(payload, claim_type=_provisional_claim_type(payload))
    novelty_text, novelty_anchor = _novelty_candidate(ranked[:8], central_unit)
    central_claim = central_unit["quote"] if central_unit else None
    contradiction_flags = _contradictions(payload, central_claim, decisive_support_object)
    anchor_index = dedupe_anchors([central_unit, novelty_anchor, first_hard_object, decisive_support_object, *ranked[:4]])
    return {
        "claim_candidates": [unit["quote"] for unit in ranked[:8]],
        "central_claim": central_claim,
        "central_claim_anchor": central_unit,
        "novelty_delta_candidate": novelty_text,
        "novelty_delta_anchor": novelty_anchor,
        "first_hard_object": first_hard_object,
        "decisive_support_object": decisive_support_object,
        "claim_extraction_confidence": _confidence(payload, ranked[:8], decisive_support_object),
        "contradiction_flags": contradiction_flags,
        "anchor_index": anchor_index,
    }
