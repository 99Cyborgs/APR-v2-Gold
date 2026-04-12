from __future__ import annotations

from typing import Any

from jsonschema import validate

from apr_core.defense_readiness import DEFAULT_DEFENSE_CONTEXT, build_defense_readiness_record
from apr_core.derived_utils import artifact_provenance, collect_evidence_anchors, count_answerability, severity_from_score
from apr_core.policy import load_question_challenge_record_schema
from apr_core.question_registry import load_validated_question_registry, question_registry_sha256
from apr_core.utils import stable_json_sha256


def _registry_entries_for_context(registry: dict[str, Any], context_type: str) -> list[dict[str, Any]]:
    return [entry for entry in registry.get("entries", []) if context_type in entry.get("contexts", [])]


def _linked_risks(entry: dict[str, Any], defense_record: dict[str, Any]) -> list[dict[str, Any]]:
    families = set(entry.get("linked_risk_families", []))
    return [risk for risk in defense_record.get("risk_items", []) if risk.get("category") in families]


def _entry_is_applicable(entry: dict[str, Any], canonical_record: dict[str, Any], defense_record: dict[str, Any]) -> bool:
    trigger = entry.get("trigger_conditions", {})
    article_types = trigger.get("article_types", [])
    current_article_type = canonical_record.get("classification", {}).get("article_type")
    if article_types and current_article_type not in article_types:
        return False

    linked_risks = _linked_risks(entry, defense_record)
    applicable_risks = [risk for risk in linked_risks if risk.get("current_answerability") != "not_applicable"]
    if trigger.get("always_include"):
        return True
    if applicable_risks and max(int(risk.get("score") or 0) for risk in applicable_risks) >= int(trigger.get("minimum_risk_score") or 0):
        return True
    return not trigger.get("only_when_applicable", False) and bool(applicable_risks)


def _question_target(entry: dict[str, Any], canonical_record: dict[str, Any], linked_risks: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    anchors = collect_evidence_anchors([risk.get("evidence_anchors") for risk in linked_risks])
    if anchors:
        return anchors[0]["quote"], anchors

    parsing = canonical_record.get("parsing", {})
    if entry.get("category") == "novelty_relative_to_nearest_prior_work" and parsing.get("novelty_delta_anchor"):
        anchors = collect_evidence_anchors(parsing.get("novelty_delta_anchor"))
        return anchors[0]["quote"], anchors
    if parsing.get("central_claim_anchor"):
        anchors = collect_evidence_anchors(parsing.get("central_claim_anchor"))
        return anchors[0]["quote"], anchors
    if parsing.get("decisive_support_object"):
        anchors = collect_evidence_anchors(parsing.get("decisive_support_object"))
        return anchors[0]["quote"], anchors
    return "No anchored span available.", []


def _question_reason(entry: dict[str, Any], canonical_record: dict[str, Any], linked_risks: list[dict[str, Any]], target: str) -> str:
    if linked_risks:
        dominant = max(linked_risks, key=lambda risk: int(risk.get("score") or 0))
        return (
            f"This manuscript is likely to be asked this because {dominant['category']} is active at "
            f"{dominant['severity']} severity and the challenge can be grounded in: {target}"
        )
    claim = canonical_record.get("parsing", {}).get("central_claim") or "the manuscript's central contribution"
    return f"This is a standard board question for the claimed contribution: {claim}"


def _answer_ingredients(entry: dict[str, Any], linked_risks: list[dict[str, Any]]) -> list[str]:
    ingredients = list(entry.get("expected_answer_ingredients", []))
    for risk in linked_risks:
        ingredients.extend(risk.get("expected_evidence_needed", []))
    seen: set[str] = set()
    ordered: list[str] = []
    for ingredient in ingredients:
        if ingredient in seen:
            continue
        seen.add(ingredient)
        ordered.append(ingredient)
    return ordered


def build_question_challenge_record(
    canonical_record: dict[str, Any],
    *,
    defense_record: dict[str, Any] | None = None,
    context_type: str = DEFAULT_DEFENSE_CONTEXT,
    limit: int | None = None,
) -> dict[str, Any]:
    defense_record = defense_record or build_defense_readiness_record(canonical_record, context_type=context_type)
    registry = load_validated_question_registry()

    questions: list[dict[str, Any]] = []
    for entry in _registry_entries_for_context(registry, context_type):
        if not _entry_is_applicable(entry, canonical_record, defense_record):
            continue

        linked_risks = _linked_risks(entry, defense_record)
        target, anchors = _question_target(entry, canonical_record, linked_risks)
        answerability = "answered"
        if linked_risks:
            order = {"answered": 0, "weak": 1, "missing": 2, "not_applicable": -1}
            answerability = max(
                (risk.get("current_answerability", "answered") for risk in linked_risks),
                key=lambda state: order.get(state, 0),
            )
        risk_score = max((int(risk.get("score") or 0) for risk in linked_risks), default=25 if entry["trigger_conditions"]["always_include"] else 10)
        questions.append(
            {
                "challenge_id": f"{context_type}:{entry['question_id']}",
                "registry_question_id": entry["question_id"],
                "question_text": entry["canonical_question_text"],
                "category": entry["category"],
                "why_this_manuscript_will_be_asked": _question_reason(entry, canonical_record, linked_risks, target),
                "targeted_claim_or_span": target,
                "current_answerability": answerability,
                "risk_if_asked": {
                    "score": risk_score,
                    "severity": severity_from_score(risk_score),
                },
                "suggested_answer_ingredients": _answer_ingredients(entry, linked_risks),
                "mitigation_or_prep_action": (
                    linked_risks[0]["mitigation_path"]
                    if linked_risks
                    else "Prepare one concise answer anchored to the central claim and a concrete evidence quote."
                ),
                "evidence_anchors": anchors,
                "linked_risk_ids": [risk["risk_id"] for risk in linked_risks],
            }
        )

    questions.sort(
        key=lambda item: (
            -int(item["risk_if_asked"]["score"]),
            item["category"],
            item["registry_question_id"],
        )
    )
    if limit is not None:
        questions = questions[:limit]

    answerability_counts = count_answerability(question["current_answerability"] for question in questions)
    summary = {
        "question_count": len(questions),
        "high_risk_question_count": sum(1 for question in questions if question["risk_if_asked"]["score"] >= 60),
        "answerability_counts": answerability_counts,
        "summary": (
            f"{sum(1 for question in questions if question['risk_if_asked']['score'] >= 60)} questions are high-pressure; "
            f"{answerability_counts['weak'] + answerability_counts['missing']} are not yet answerable cleanly."
        ),
    }

    record = {
        "artifact_type": "QuestionChallengeRecord",
        "schema_version": "1.0.0",
        "context_type": context_type,
        "source": {
            "manuscript_id": canonical_record.get("metadata", {}).get("manuscript_id"),
            "title": canonical_record.get("metadata", {}).get("title"),
            "canonical_record_sha256": stable_json_sha256(canonical_record),
            "defense_record_sha256": stable_json_sha256(defense_record),
            "registry_sha256": question_registry_sha256(),
        },
        "questions": questions,
        "summary": summary,
        "provenance": artifact_provenance(canonical_record),
    }
    validate(instance=record, schema=load_question_challenge_record_schema())
    return record
