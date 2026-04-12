from __future__ import annotations

from typing import Any

from jsonschema import validate

from apr_core.derived_utils import (
    artifact_provenance,
    artifact_source,
    collect_evidence_anchors,
    count_answerability,
    evidence_anchors_from_paths,
    severity_from_score,
)
from apr_core.policy import load_defense_readiness_record_schema

DEFAULT_DEFENSE_CONTEXT = "phd_defense_committee"

_STATUS_SCORE = {
    "pass": 0,
    "clear": 0,
    "declared": 0,
    "aligned": 0,
    "watch": 15,
    "borderline": 20,
    "incomplete": 30,
    "flagged": 35,
    "downgraded": 40,
    "fail": 50,
    "rebuild_required": 55,
    "missing": 55,
    "repairable_fail": 65,
    "blocked": 70,
    "fatal": 80,
    "fatal_fail": 85,
    "escalate": 90,
    "non_reviewable": 95,
}

_QUESTION_PRESSURE_CONTEXT_BONUS = {
    "phd_defense_committee": 20,
    "dissertation_proposal_committee": 12,
    "departmental_research_review": 10,
    "journal_referee": 8,
    "ethics_or_compliance_board": 10,
}

_RISK_BLUEPRINTS = {
    "central_claim_clarity_risk": {
        "paths": [
            "parsing.central_claim_anchor",
            "scientific_record.criteria.problem_definition_and_claim_clarity",
            "reviewability.evidence_anchors",
        ],
        "attack": "The board asks for one defendable sentence and exposes ambiguity in the actual claim boundary.",
        "needed": [
            "One sentence stating the central claim",
            "Evidence anchor that directly supports that claim",
            "Clear bound on what is not being claimed",
        ],
        "mitigation": "Tighten the central claim sentence, align it with the decisive support object, and explicitly state the claim boundary.",
    },
    "novelty_positioning_risk": {
        "paths": [
            "parsing.novelty_delta_anchor",
            "editorial_first_pass.evidence_anchors",
            "scientific_record.criteria.literature_positioning",
        ],
        "attack": "A reviewer asks whether the manuscript's novelty is distinct from baseline engineering, framing, or venue aspiration.",
        "needed": [
            "Nearest prior work or baseline",
            "Explicit novelty delta",
            "Bound on what remains incremental rather than novel",
        ],
        "mitigation": "Name the nearest prior work, state the novelty delta in one sentence, and separate genuine contribution from baseline execution.",
    },
    "literature_gap_risk": {
        "paths": [
            "scientific_record.criteria.literature_positioning",
            "venue.evidence_anchors",
            "editorial_first_pass.evidence_anchors",
        ],
        "attack": "The committee asks whether the manuscript has actually defined the literature gap or just gestured toward it.",
        "needed": [
            "Explicit literature gap statement",
            "Named comparator literature or baseline",
            "Why the current manuscript closes or constrains that gap",
        ],
        "mitigation": "Expand the literature-positioning paragraph to name the exact gap, comparator literature, and why this manuscript changes the record.",
    },
    "method_legibility_risk": {
        "paths": [
            "parsing.first_hard_object",
            "reviewability.evidence_anchors",
            "scientific_record.criteria.methodological_legibility",
        ],
        "attack": "A board member asks how another specialist could reconstruct the method without guessing.",
        "needed": [
            "Method or protocol statement",
            "First hard object or formal object",
            "Explanation of why this method fits the claim",
        ],
        "mitigation": "Expose the method spine earlier, surface the first hard object, and add one paragraph on why alternative methods were not chosen.",
    },
    "evidence_alignment_risk": {
        "paths": [
            "parsing.decisive_support_object",
            "scientific_record.criteria.evidence_to_claim_alignment",
            "claim_evidence_calibration.evidence_anchors",
        ],
        "attack": "The defense challenge is whether the cited evidence actually decides the claim being made.",
        "needed": [
            "Decisive support object",
            "Claim-to-evidence link",
            "Why weaker evidence would not support the same claim",
        ],
        "mitigation": "Make the decisive support object explicit and narrow the claim so it matches the visible evidence envelope.",
    },
    "overclaim_risk": {
        "paths": [
            "claim_evidence_calibration.evidence_anchors",
            "adversarial_resilience.evidence_anchors",
            "scientific_record.criteria.claim_evidence_calibration",
        ],
        "attack": "The manuscript is pressed on whether language outruns support, robustness, or stated limitations.",
        "needed": [
            "Measured evidence envelope",
            "Bounded claim language",
            "Why broader interpretations are not warranted",
        ],
        "mitigation": "Reduce rhetorical scope, add explicit limits, and tie the strongest claim sentence to the actual evidence level.",
    },
    "comparator_or_control_risk": {
        "paths": [
            "structural_integrity.evidence_anchors",
            "scientific_record.criteria.literature_positioning",
            "venue.evidence_anchors",
        ],
        "attack": "The board asks whether the chosen baseline or control is fair, sufficient, and nearest to the claimed contribution.",
        "needed": [
            "Named control or baseline",
            "Reason that comparator is fair",
            "What stronger comparator would change the interpretation",
        ],
        "mitigation": "Add the missing comparator or justify the current one explicitly, including what a stronger control would likely reveal.",
    },
    "reproducibility_risk": {
        "paths": [
            "transparency.evidence_anchors",
            "scientific_record.criteria.transparency_and_reporting_readiness",
            "reviewability.evidence_anchors",
        ],
        "attack": "A referee asks whether another specialist could reproduce the result from the manuscript as written.",
        "needed": [
            "Data, code, or materials pathway",
            "Method detail needed for replication",
            "Named missing items if replication is incomplete",
        ],
        "mitigation": "Close the transparency gap by stating the exact release pathway and the minimum materials needed for reproduction.",
    },
    "statistics_or_uncertainty_risk": {
        "paths": [
            "structural_integrity.evidence_anchors",
            "claim_evidence_calibration.evidence_anchors",
            "scientific_record.criteria.evidence_to_claim_alignment",
        ],
        "attack": "The challenge is whether uncertainty, sensitivity, or robustness is visible enough to support the conclusion.",
        "needed": [
            "Uncertainty statement or interval",
            "Robustness or sensitivity check",
            "Failure condition or threshold that would change the conclusion",
        ],
        "mitigation": "Add explicit uncertainty and robustness language, including the threshold at which the current claim would weaken.",
    },
    "scope_inflation_risk": {
        "paths": [
            "scientific_record.criteria.problem_definition_and_claim_clarity",
            "venue.evidence_anchors",
            "adversarial_resilience.evidence_anchors",
        ],
        "attack": "The committee challenges whether the manuscript is claiming more scope than the evidence and stated boundary justify.",
        "needed": [
            "Bounded scope statement",
            "Explicit limit or excluded regime",
            "Why broader claims are not being made",
        ],
        "mitigation": "Replace broad framing with the strongest bounded claim and explicitly list excluded regimes or unsupported extrapolations.",
    },
    "limitations_acknowledgment_risk": {
        "paths": [
            "structural_integrity.evidence_anchors",
            "scientific_record.criteria.problem_definition_and_claim_clarity",
            "scientific_record.criteria.methodological_legibility",
        ],
        "attack": "The board tests whether limitations are real working bounds or merely a perfunctory sentence at the end.",
        "needed": [
            "Concrete limitation statement",
            "Failure condition",
            "Repair path or next discriminating analysis",
        ],
        "mitigation": "Move limitations into the main argument, state the highest-impact failure condition, and pair it with a concrete repair path.",
    },
    "ethics_or_provenance_risk": {
        "paths": [
            "integrity.evidence_anchors",
            "scientific_record.criteria.integrity_and_policy_readiness",
            "transparency.evidence_anchors",
        ],
        "attack": "The manuscript is challenged on disclosure, approvals, provenance, or integrity assumptions that could invalidate the record.",
        "needed": [
            "Ethics or disclosure statement",
            "Provenance or approval chain",
            "Escalation trigger if those assumptions fail",
        ],
        "mitigation": "Make provenance and disclosure explicit, state any approvals or data-origin constraints, and surface any remaining escalation triggers.",
    },
    "defense_question_pressure_risk": {
        "paths": [
            "parsing.central_claim_anchor",
            "claim_evidence_calibration.evidence_anchors",
            "scientific_record.major_concerns",
        ],
        "attack": "High-pressure questioning concentrates where multiple weaknesses intersect and the manuscript cannot answer cleanly from its own record.",
        "needed": [
            "Concise defense script for the central claim",
            "Evidence anchors for the top attack surfaces",
            "Prioritized mitigation sequence",
        ],
        "mitigation": "Prepare short defense answers for the top risk intersections and order mitigation by the highest-scoring unanswered attack surfaces.",
    },
}


def _status_score(status: str | None) -> int:
    if not status:
        return 0
    return _STATUS_SCORE.get(status, 0)


def _criterion_detail(record: dict[str, Any], criterion: str) -> dict[str, Any]:
    return record.get("scientific_record", {}).get("criteria", {}).get(criterion, {})


def _component_score(record: dict[str, Any], component: str) -> int:
    return int(record.get("editorial_first_pass", {}).get("component_scores", {}).get(component, 0) or 0)


def _payload_text(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    parts = [
        payload.get("title") or "",
        payload.get("abstract") or "",
        payload.get("manuscript_text") or "",
        payload.get("supplement_or_appendix") or "",
        payload.get("ethics_and_disclosures") or "",
    ]
    return " ".join(str(part) for part in parts).lower()


def _score_central_claim(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = 0
    parsing = record.get("parsing", {})
    checks = record.get("reviewability", {}).get("checks", {})
    score += 25 if not parsing.get("central_claim") else 0
    score += 30 if checks.get("recoverable_central_claim") == "fail" else 0
    confidence = float(parsing.get("claim_extraction_confidence") or 0.0)
    score += 25 if confidence < 0.6 else 12 if confidence < 0.75 else 0
    score += _status_score(_criterion_detail(record, "problem_definition_and_claim_clarity").get("status"))
    if payload and "we " not in _payload_text(payload):
        score += 5
    return min(100, score)


def _score_novelty_positioning(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = 25 if not record.get("parsing", {}).get("novelty_delta_candidate") else 0
    score += _status_score(_criterion_detail(record, "literature_positioning").get("status"))
    references_coverage = _component_score(record, "references_coverage")
    score += 25 if references_coverage <= 1 else 12 if references_coverage <= 3 else 0
    if payload and "novel" not in _payload_text(payload) and "new" not in _payload_text(payload):
        score += 8
    return min(100, score)


def _score_literature_gap(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = _status_score(_criterion_detail(record, "literature_positioning").get("status"))
    references_coverage = _component_score(record, "references_coverage")
    score += 30 if references_coverage <= 1 else 15 if references_coverage <= 3 else 0
    if payload and len(payload.get("references") or []) < 3:
        score += 10
    return min(100, score)


def _score_method_legibility(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = 0
    checks = record.get("reviewability", {}).get("checks", {})
    score += 30 if checks.get("assessable_method_model_or_protocol") == "fail" else 0
    score += 20 if not record.get("parsing", {}).get("first_hard_object") else 0
    score += _status_score(_criterion_detail(record, "methodological_legibility").get("status"))
    if payload and not any(payload.get(name) for name in ("tables", "figures_and_captions", "supplement_or_appendix")):
        score += 10
    return min(100, score)


def _score_evidence_alignment(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = _status_score(_criterion_detail(record, "evidence_to_claim_alignment").get("status"))
    score += _status_score(record.get("claim_evidence_calibration", {}).get("status"))
    score += 15 if not record.get("parsing", {}).get("decisive_support_object") else 0
    if payload and not (payload.get("tables") or payload.get("figures_and_captions")):
        score += 8
    return min(100, score)


def _score_overclaim(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    calibration = record.get("claim_evidence_calibration", {})
    mismatch = int(calibration.get("mismatch") or 0)
    score = max(0, mismatch) * 18
    score += _status_score(calibration.get("status"))
    score += min(20, int(record.get("adversarial_resilience", {}).get("flag_count") or 0) * 4)
    if any(term in _payload_text(payload) for term in ("breakthrough", "transformative", "universal", "all ")):
        score += 15
    return min(100, score)


def _score_comparator_control(record: dict[str, Any], payload: dict[str, Any] | None) -> tuple[int, bool]:
    article_type = record.get("classification", {}).get("article_type")
    applicable = article_type not in {"commentary_or_perspective", "editorial_or_opinion"}
    if not applicable:
        return 0, False
    structural = record.get("structural_integrity", {}).get("research_spine_signals", {})
    score = 35 if structural and not structural.get("comparator", False) else 0
    score += 20 if record.get("venue", {}).get("routing_state") in {"retarget_specialist", "retarget_soundness_first"} else 0
    text = _payload_text(payload)
    if payload and "baseline" not in text and "compare" not in text:
        score += 20
    return min(100, score), True


def _score_reproducibility(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    transparency = record.get("transparency", {})
    score = _status_score(transparency.get("status"))
    score += min(25, len(transparency.get("missing_items") or []) * 8)
    score += _status_score(_criterion_detail(record, "transparency_and_reporting_readiness").get("status"))
    if payload and not any(payload.get(name) for name in ("data_availability", "code_availability", "materials_availability")):
        score += 15
    return min(100, score)


def _score_statistics_uncertainty(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    structural = record.get("structural_integrity", {}).get("research_spine_signals", {})
    score = 25 if structural and not structural.get("uncertainty", False) else 0
    score += 15 if record.get("claim_evidence_calibration", {}).get("status") in {"watch", "fail", "fatal"} else 0
    text = _payload_text(payload)
    if payload and not any(term in text for term in ("uncertainty", "confidence interval", "error bar", "sensitivity", "robust")):
        score += 20
    return min(100, score)


def _score_scope_inflation(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    score = 0
    if record.get("venue", {}).get("routing_state") in {"retarget_specialist", "retarget_soundness_first"}:
        score += 20
    if record.get("adversarial_resilience", {}).get("status") in {"watch", "downgraded", "blocked"}:
        score += 20
    text = _payload_text(payload)
    if any(term in text for term in ("universal", "all", "transformative", "field-defining", "paradigm")):
        score += 30
    score += _status_score(_criterion_detail(record, "problem_definition_and_claim_clarity").get("status"))
    return min(100, score)


def _score_limitations_acknowledgment(record: dict[str, Any], payload: dict[str, Any] | None) -> int:
    structural = record.get("structural_integrity", {}).get("research_spine_signals", {})
    score = 25 if structural and not structural.get("failure_condition", False) else 0
    score += 20 if record.get("rehabilitation", {}).get("next_actions_ranked") else 0
    text = _payload_text(payload)
    if payload and not any(term in text for term in ("limit", "failure", "should not be used", "does not", "cannot")):
        score += 20
    return min(100, score)


def _score_ethics_provenance(record: dict[str, Any], payload: dict[str, Any] | None) -> tuple[int, bool]:
    text = _payload_text(payload)
    domain = record.get("classification", {}).get("domain_module")
    applicable = domain == "clinical_or_human_subjects" or bool(text.strip()) or bool(record.get("integrity", {}).get("flags"))
    score = _status_score(record.get("integrity", {}).get("status"))
    score += _status_score(_criterion_detail(record, "integrity_and_policy_readiness").get("status"))
    if domain == "clinical_or_human_subjects" and "ethics" not in text and "irb" not in text and "consent" not in text:
        score += 25
    if payload and "declare" not in text and "competing" not in text and "disclosure" not in text:
        score += 10
    return min(100, score), applicable


def _score_defense_pressure(risk_items: list[dict[str, Any]], context_type: str) -> int:
    active_scores = sorted(
        [
            item["score"]
            for item in risk_items
            if item["category"] != "defense_question_pressure_risk" and item["current_answerability"] != "not_applicable"
        ],
        reverse=True,
    )
    pressure = sum(active_scores[:3]) // max(1, min(3, len(active_scores[:3])))
    pressure += _QUESTION_PRESSURE_CONTEXT_BONUS.get(context_type, 0)
    weak_or_missing = sum(1 for item in risk_items if item["current_answerability"] in {"weak", "missing"})
    pressure += weak_or_missing * 4
    return min(100, pressure)


def _answerability_from_score(score: int, applicable: bool, anchors: list[dict[str, str]]) -> str:
    if not applicable:
        return "not_applicable"
    if score >= 75 and not anchors:
        return "missing"
    if score >= 65:
        return "missing"
    if score >= 35:
        return "weak"
    return "answered"


def _build_rationale(category: str, record: dict[str, Any], applicable: bool) -> str:
    if not applicable:
        return "This risk family is not a primary attack surface for the current manuscript type."
    if category == "central_claim_clarity_risk":
        confidence = float(record.get("parsing", {}).get("claim_extraction_confidence") or 0.0)
        return f"Central-claim recovery confidence is {confidence:.2f}, and claim clarity will be tested against the visible claim boundary."
    if category == "novelty_positioning_risk":
        novelty = record.get("parsing", {}).get("novelty_delta_candidate") or "no explicit novelty delta"
        return f"Novelty positioning depends on {novelty!r} and the literature-positioning criterion."
    if category == "literature_gap_risk":
        return "Literature positioning remains a likely attack surface because gap definition and comparator coverage are part of the scientific-record threshold."
    if category == "method_legibility_risk":
        return "Method legibility depends on whether the method spine and first hard object are visible enough for another specialist to reconstruct."
    if category == "evidence_alignment_risk":
        return "Evidence alignment is driven by the decisive support object and the claim-evidence calibration status."
    if category == "overclaim_risk":
        return "Overclaim pressure rises when rhetoric, adversarial flags, or claim magnitude outrun the actual support envelope."
    if category == "comparator_or_control_risk":
        return "Comparator sufficiency is a likely pressure point when the baseline, control, or nearest fair comparison is missing or thin."
    if category == "reproducibility_risk":
        return "Reproducibility risk is governed by the transparency pathway and any missing release or materials signals."
    if category == "statistics_or_uncertainty_risk":
        return "Uncertainty and robustness remain exposed when the record does not show explicit sensitivity or bounded error treatment."
    if category == "scope_inflation_risk":
        return "Scope inflation appears when the manuscript's framing exceeds what the evidence and routing decision can support."
    if category == "limitations_acknowledgment_risk":
        return "Boards will test whether limitations and failure conditions are explicit operating bounds rather than perfunctory caveats."
    if category == "ethics_or_provenance_risk":
        return "Ethics and provenance pressure tracks integrity, disclosures, and any domain-specific approval assumptions."
    return "Defense pressure accumulates where several unresolved risks intersect and the manuscript cannot answer quickly from its own record."


def _risk_item(category: str, *, score: int, applicable: bool, record: dict[str, Any]) -> dict[str, Any]:
    blueprint = _RISK_BLUEPRINTS[category]
    anchors = evidence_anchors_from_paths(record, blueprint["paths"])
    answerability = _answerability_from_score(score, applicable, anchors)
    return {
        "risk_id": category.replace("_risk", ""),
        "category": category,
        "score": score,
        "severity": severity_from_score(score),
        "rationale": _build_rationale(category, record, applicable),
        "likely_attack_vector": blueprint["attack"],
        "expected_evidence_needed": blueprint["needed"],
        "current_answerability": answerability,
        "mitigation_path": blueprint["mitigation"],
        "linked_canonical_field_paths": blueprint["paths"],
        "evidence_anchors": anchors,
    }


def _build_strength_anchors(record: dict[str, Any], payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    parsing = record.get("parsing", {})
    if parsing.get("central_claim") and float(parsing.get("claim_extraction_confidence") or 0.0) >= 0.7:
        candidates.append(
            {
                "anchor_id": "strength-central-claim",
                "label": "Central claim is recoverable",
                "summary": "The manuscript exposes a bounded central claim that can be quoted and defended directly.",
                "linked_canonical_field_paths": ["parsing.central_claim", "parsing.central_claim_anchor"],
                "evidence_anchors": collect_evidence_anchors(parsing.get("central_claim_anchor")),
            }
        )
    if parsing.get("decisive_support_object"):
        candidates.append(
            {
                "anchor_id": "strength-decisive-support",
                "label": "Decisive support object is visible",
                "summary": "The record exposes a concrete support object that can anchor defense answers to evidence rather than rhetoric.",
                "linked_canonical_field_paths": ["parsing.decisive_support_object", "reviewability.evidence_anchors"],
                "evidence_anchors": collect_evidence_anchors(
                    parsing.get("decisive_support_object"),
                    record.get("reviewability", {}).get("evidence_anchors"),
                ),
            }
        )
    if record.get("transparency", {}).get("status") == "declared":
        candidates.append(
            {
                "anchor_id": "strength-transparency",
                "label": "Transparency pathway is declared",
                "summary": "The manuscript already exposes a concrete transparency pathway for audit or replication follow-up.",
                "linked_canonical_field_paths": ["transparency", "scientific_record.criteria.transparency_and_reporting_readiness"],
                "evidence_anchors": collect_evidence_anchors(
                    record.get("transparency", {}).get("evidence_anchors"),
                    _criterion_detail(record, "transparency_and_reporting_readiness"),
                ),
            }
        )
    if record.get("integrity", {}).get("status") == "clear":
        candidates.append(
            {
                "anchor_id": "strength-integrity-clear",
                "label": "No integrity escalation is visible",
                "summary": "The canonical record does not expose an integrity block, which lowers committee attack pressure on provenance and policy grounds.",
                "linked_canonical_field_paths": ["integrity", "scientific_record.criteria.integrity_and_policy_readiness"],
                "evidence_anchors": collect_evidence_anchors(
                    record.get("integrity", {}).get("evidence_anchors"),
                    _criterion_detail(record, "integrity_and_policy_readiness"),
                ),
            }
        )
    if payload and any(term in _payload_text(payload) for term in ("limit", "failure", "should not be used")):
        candidates.append(
            {
                "anchor_id": "strength-limitations-visible",
                "label": "Limitations are at least partially surfaced",
                "summary": "The manuscript already contains language that acknowledges limits or failure conditions, which improves defense credibility.",
                "linked_canonical_field_paths": ["structural_integrity", "parsing.anchor_index"],
                "evidence_anchors": collect_evidence_anchors(
                    record.get("structural_integrity", {}).get("evidence_anchors"),
                    record.get("parsing", {}).get("anchor_index"),
                ),
            }
        )
    return [candidate for candidate in candidates if candidate["evidence_anchors"]]


def _build_weakness_anchors(record: dict[str, Any]) -> list[dict[str, Any]]:
    weaknesses: list[dict[str, Any]] = []
    criteria = record.get("scientific_record", {}).get("criteria", {})
    for criterion_name, detail in criteria.items():
        if detail.get("status") in {"fail", "borderline"}:
            weaknesses.append(
                {
                    "anchor_id": f"weakness-{criterion_name}",
                    "label": criterion_name.replace("_", " "),
                    "summary": detail.get("why") or "This criterion remains vulnerable under review.",
                    "linked_canonical_field_paths": [f"scientific_record.criteria.{criterion_name}"],
                    "evidence_anchors": collect_evidence_anchors(detail),
                }
            )
    transparency = record.get("transparency", {})
    if transparency.get("status") in {"incomplete", "missing"}:
        weaknesses.append(
            {
                "anchor_id": "weakness-transparency-gap",
                "label": "Transparency gap",
                "summary": "Transparency and reporting remain incomplete enough to invite replication and documentation attacks.",
                "linked_canonical_field_paths": ["transparency"],
                "evidence_anchors": collect_evidence_anchors(transparency.get("evidence_anchors")),
            }
        )
    calibration = record.get("claim_evidence_calibration", {})
    if calibration.get("status") in {"watch", "fail", "fatal"}:
        weaknesses.append(
            {
                "anchor_id": "weakness-claim-evidence-calibration",
                "label": "Claim and evidence are not tightly aligned",
                "summary": "The claim-evidence calibration surface already exposes a mismatch that a board will likely press.",
                "linked_canonical_field_paths": ["claim_evidence_calibration"],
                "evidence_anchors": collect_evidence_anchors(calibration.get("evidence_anchors")),
            }
        )
    return [item for item in weaknesses if item["evidence_anchors"]]


def build_defense_readiness_record(
    canonical_record: dict[str, Any],
    *,
    payload: dict[str, Any] | None = None,
    context_type: str = DEFAULT_DEFENSE_CONTEXT,
) -> dict[str, Any]:
    risk_items: list[dict[str, Any]] = []

    comparator_score, comparator_applicable = _score_comparator_control(canonical_record, payload)
    ethics_score, ethics_applicable = _score_ethics_provenance(canonical_record, payload)

    risk_items.append(_risk_item("central_claim_clarity_risk", score=_score_central_claim(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("novelty_positioning_risk", score=_score_novelty_positioning(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("literature_gap_risk", score=_score_literature_gap(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("method_legibility_risk", score=_score_method_legibility(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("evidence_alignment_risk", score=_score_evidence_alignment(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("overclaim_risk", score=_score_overclaim(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("comparator_or_control_risk", score=comparator_score, applicable=comparator_applicable, record=canonical_record))
    risk_items.append(_risk_item("reproducibility_risk", score=_score_reproducibility(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("statistics_or_uncertainty_risk", score=_score_statistics_uncertainty(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("scope_inflation_risk", score=_score_scope_inflation(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("limitations_acknowledgment_risk", score=_score_limitations_acknowledgment(canonical_record, payload), applicable=True, record=canonical_record))
    risk_items.append(_risk_item("ethics_or_provenance_risk", score=ethics_score, applicable=ethics_applicable, record=canonical_record))
    risk_items.append(
        _risk_item(
            "defense_question_pressure_risk",
            score=_score_defense_pressure(risk_items, context_type),
            applicable=True,
            record=canonical_record,
        )
    )

    answerability_counts = count_answerability(item["current_answerability"] for item in risk_items)
    high_pressure_question_count = sum(
        1 for item in risk_items if item["score"] >= 60 and item["current_answerability"] in {"weak", "missing"}
    )
    summary = (
        f"{sum(1 for item in risk_items if item['severity'] == 'critical')} critical and "
        f"{sum(1 for item in risk_items if item['severity'] == 'high')} high-risk attack surfaces; "
        f"{answerability_counts['weak'] + answerability_counts['missing']} surfaces are not yet answerable cleanly."
    )

    ranked_risks = sorted(
        [item for item in risk_items if item["current_answerability"] != "not_applicable"],
        key=lambda item: (-item["score"], item["category"]),
    )
    priorities = [
        {
            "priority_rank": index,
            "title": item["category"].replace("_", " "),
            "reason": item["rationale"],
            "linked_risk_ids": [item["risk_id"]],
            "action": item["mitigation_path"],
        }
        for index, item in enumerate(ranked_risks[:5], start=1)
    ]

    max_score = max(item["score"] for item in risk_items)
    blocking_recommendation = canonical_record.get("decision", {}).get("recommendation") in {
        "DO_NOT_SUBMIT",
        "NON_REVIEWABLE",
        "REBUILD_BEFORE_SUBMISSION",
    }
    if blocking_recommendation or max_score >= 80 or answerability_counts["missing"] >= 3:
        overall_status = "not_ready"
    elif max_score >= 60 or answerability_counts["missing"] >= 1 or answerability_counts["weak"] >= 4:
        overall_status = "vulnerable"
    elif max_score >= 35 or answerability_counts["weak"] >= 2:
        overall_status = "ready_with_mitigation"
    else:
        overall_status = "ready"

    record = {
        "artifact_type": "DefenseReadinessRecord",
        "schema_version": "1.0.0",
        "context_type": context_type,
        "overall_status": overall_status,
        "source": artifact_source(canonical_record, payload),
        "strength_anchors": _build_strength_anchors(canonical_record, payload),
        "weakness_anchors": _build_weakness_anchors(canonical_record),
        "risk_items": risk_items,
        "answerability_summary": {
            "counts": answerability_counts,
            "high_pressure_question_count": high_pressure_question_count,
            "summary": summary,
        },
        "recommended_mitigation_priorities": priorities,
        "provenance": artifact_provenance(canonical_record),
    }
    validate(instance=record, schema=load_defense_readiness_record_schema())
    return record
