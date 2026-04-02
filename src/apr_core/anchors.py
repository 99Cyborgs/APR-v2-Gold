from __future__ import annotations

import re
from typing import Any, Iterable

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def make_anchor(location: str, quote: str | None) -> dict[str, str]:
    text = (quote or "").strip().replace("\n", " ")
    if len(text) > 280:
        text = text[:277].rstrip() + "..."
    return {"location": location, "quote": text}


def _sentences(text: str | None, limit: int | None = None) -> list[str]:
    if not text:
        return []
    sentences = [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]
    return sentences[:limit] if limit is not None else sentences


def segment_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    units: list[dict[str, str]] = []
    if payload.get("title"):
        units.append(make_anchor("Title", payload["title"]))
    for index, sentence in enumerate(_sentences(payload.get("abstract"), limit=8), start=1):
        units.append(make_anchor(f"Abstract:s{index}", sentence))
    for index, sentence in enumerate(_sentences(payload.get("manuscript_text"), limit=18), start=1):
        units.append(make_anchor(f"Body:s{index}", sentence))
    for index, item in enumerate(payload.get("figures_and_captions") or [], start=1):
        units.append(make_anchor(f"Figure:{index}", item))
    for index, item in enumerate(payload.get("tables") or [], start=1):
        units.append(make_anchor(f"Table:{index}", item))
    for index, item in enumerate(payload.get("references") or [], start=1):
        units.append(make_anchor(f"Ref:{index}", item))
    for index, sentence in enumerate(_sentences(payload.get("supplement_or_appendix"), limit=6), start=1):
        units.append(make_anchor(f"Supplement:s{index}", sentence))
    if payload.get("ethics_and_disclosures"):
        units.append(make_anchor("Disclosures", payload["ethics_and_disclosures"]))
    if payload.get("reviewer_notes"):
        units.append(make_anchor("ReviewerNotes", payload["reviewer_notes"]))
    return units


def dedupe_anchors(anchors: Iterable[dict[str, str] | None]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, str]] = []
    for anchor in anchors:
        if not anchor:
            continue
        cleaned = make_anchor(anchor.get("location", ""), anchor.get("quote", ""))
        key = (cleaned["location"], cleaned["quote"])
        if key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def search_anchors(
    payload: dict[str, Any],
    patterns: Iterable[str],
    *,
    prefixes: Iterable[str] | None = None,
    max_hits: int = 3,
) -> list[dict[str, str]]:
    wanted = [pattern.lower() for pattern in patterns if pattern]
    allowed = set(prefixes or [])
    hits: list[dict[str, str]] = []
    for unit in segment_payload(payload):
        prefix = unit["location"].split(":", 1)[0]
        if allowed and prefix not in allowed:
            continue
        quote = unit["quote"].lower()
        if any(pattern in quote for pattern in wanted):
            hits.append(unit)
            if len(hits) >= max_hits:
                break
    return dedupe_anchors(hits)


def first_anchor_from_fields(payload: dict[str, Any], fields: Iterable[str]) -> dict[str, str] | None:
    for field in fields:
        if field == "title" and payload.get("title"):
            return make_anchor("Title", payload["title"])
        if field == "abstract":
            abstract = _sentences(payload.get("abstract"), limit=1)
            if abstract:
                return make_anchor("Abstract:s1", abstract[0])
        if field == "manuscript_text":
            body = _sentences(payload.get("manuscript_text"), limit=1)
            if body:
                return make_anchor("Body:s1", body[0])
        if field == "figures_and_captions" and payload.get("figures_and_captions"):
            return make_anchor("Figure:1", payload["figures_and_captions"][0])
        if field == "tables" and payload.get("tables"):
            return make_anchor("Table:1", payload["tables"][0])
        if field == "references" and payload.get("references"):
            return make_anchor("Ref:1", payload["references"][0])
        if field == "supplement_or_appendix" and payload.get("supplement_or_appendix"):
            supplement = _sentences(payload.get("supplement_or_appendix"), limit=1)
            if supplement:
                return make_anchor("Supplement:s1", supplement[0])
        if field == "ethics_and_disclosures" and payload.get("ethics_and_disclosures"):
            return make_anchor("Disclosures", payload["ethics_and_disclosures"])
        if field == "reviewer_notes" and payload.get("reviewer_notes"):
            return make_anchor("ReviewerNotes", payload["reviewer_notes"])
    return None


def detect_first_hard_object(payload: dict[str, Any]) -> dict[str, str] | None:
    combined = " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                payload.get("supplement_or_appendix"),
            ],
        )
    ).lower()
    if any(token in combined for token in ["theorem", "lemma", "proposition", "corollary"]):
        hit = search_anchors(payload, ["theorem", "lemma", "proposition", "corollary"], max_hits=1)
        if hit:
            return {"kind": "theorem", **hit[0]}
    if any(token in combined for token in ["equation", "hamiltonian", "lagrangian", "derivation", "derive"]):
        hit = search_anchors(payload, ["equation", "hamiltonian", "lagrangian", "derive"], max_hits=1)
        if hit:
            return {"kind": "equation_or_formal_object", **hit[0]}
    if payload.get("tables"):
        return {"kind": "table", **make_anchor("Table:1", payload["tables"][0])}
    if payload.get("figures_and_captions"):
        return {"kind": "figure", **make_anchor("Figure:1", payload["figures_and_captions"][0])}
    if any(token in combined for token in ["protocol", "workflow", "pipeline", "procedure", "calibration routine"]):
        hit = search_anchors(payload, ["protocol", "workflow", "pipeline", "procedure", "calibration routine"], max_hits=1)
        if hit:
            return {"kind": "protocol", **hit[0]}
    return None


def detect_decisive_support_object(payload: dict[str, Any], claim_type: str | None = None) -> dict[str, str] | None:
    if claim_type in {"benchmark_claim", "empirical_claim", "replication_claim", "null_result_claim"}:
        if payload.get("tables"):
            return {"kind": "table", **make_anchor("Table:1", payload["tables"][0])}
        if payload.get("figures_and_captions"):
            return {"kind": "figure", **make_anchor("Figure:1", payload["figures_and_captions"][0])}
    if payload.get("figures_and_captions"):
        return {"kind": "figure", **make_anchor("Figure:1", payload["figures_and_captions"][0])}
    if payload.get("tables"):
        return {"kind": "table", **make_anchor("Table:1", payload["tables"][0])}
    return detect_first_hard_object(payload)
