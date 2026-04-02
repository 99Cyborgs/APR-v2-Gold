from __future__ import annotations

from typing import Any

KNOWN_ARTICLE_TYPES = {
    "original_research",
    "methods_or_tools",
    "theory_or_model",
    "constraint_or_null_result",
    "replication_or_validation",
    "review",
    "systematic_review",
    "commentary_or_perspective",
    "protocol_or_registered_report",
    "case_report",
    "editorial_or_opinion",
}


def _text(payload: dict[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                payload.get("target_venue"),
                payload.get("outlet_profile_hint"),
                payload.get("declared_article_type"),
            ],
        )
    ).lower()


def _article_type(payload: dict[str, Any], text: str) -> str:
    declared = (payload.get("declared_article_type") or "").strip().lower()
    if declared in KNOWN_ARTICLE_TYPES:
        return declared
    if "systematic review" in text or "meta-analysis" in text:
        return "systematic_review"
    if "review" in text or "survey" in text:
        return "review"
    if "protocol" in text or "registered report" in text:
        return "protocol_or_registered_report"
    if "replication" in text or "reanalyze" in text or "validation" in text:
        return "replication_or_validation"
    if "null result" in text or "did not recover" in text or "constraint" in text:
        return "constraint_or_null_result"
    if any(token in text for token in ["hamiltonian", "lagrangian", "theorem", "derive", "model"]):
        return "theory_or_model"
    if any(token in text for token in ["benchmark", "pipeline", "calibration routine", "method", "tool"]):
        return "methods_or_tools"
    if any(token in text for token in ["perspective", "commentary", "opinion", "note"]):
        return "commentary_or_perspective"
    return "original_research"


def _claim_type(article_type: str, text: str) -> str:
    if article_type in {"commentary_or_perspective", "editorial_or_opinion"}:
        return "opinion_claim"
    if article_type in {"systematic_review", "review"}:
        return "synthesis_claim"
    if article_type == "protocol_or_registered_report":
        return "protocol_claim"
    if article_type == "replication_or_validation":
        return "replication_claim"
    if article_type == "constraint_or_null_result":
        return "null_result_claim"
    if article_type == "theory_or_model":
        return "model_claim"
    if article_type == "methods_or_tools" or any(token in text for token in ["benchmark", "baseline", "compares", "reduces drift"]):
        return "benchmark_claim"
    return "empirical_claim"


def _outlet_profile(payload: dict[str, Any], text: str) -> str:
    hint = (payload.get("outlet_profile_hint") or "").lower()
    venue = (payload.get("target_venue") or "").lower()
    combined = f"{hint} {venue}"
    if "preprint" in combined or "arxiv" in combined:
        return "preprint_screen"
    if "scientific reports" in combined or "plos one" in combined:
        return "soundness_first_journal"
    if venue.startswith("nature"):
        return "nature_selective"
    if "physical review letters" in combined or venue == "prl":
        return "aps_selective"
    if "review" in venue and "journal" in venue:
        return "review_only_venue"
    return "specialist_research_journal"


def _domain_module(article_type: str, claim_type: str, text: str) -> str:
    if any(token in text for token in ["patient", "cohort", "clinical", "irb", "ethics approval", "retrospective"]):
        return "clinical_or_human_subjects"
    if article_type in {"review", "systematic_review"}:
        return "review_synthesis"
    if any(token in text for token in ["hamiltonian", "lagrangian", "theorem", "qubit", "cavity", "convergence", "orbital", "mechanics"]):
        return "theory_physics_or_applied_math"
    if any(token in text for token in ["simulation", "numerical", "solver", "compute", "workflow"]) and claim_type == "model_claim":
        return "computational_or_simulation"
    if article_type == "methods_or_tools" or claim_type == "benchmark_claim":
        return "methods_or_tools"
    if claim_type in {"empirical_claim", "replication_claim", "null_result_claim"}:
        return "observational_or_empirical"
    return "general_scientific_manuscript"


def _article_claim_mismatch(article_type: str, claim_type: str, text: str) -> tuple[bool, str | None]:
    if article_type == "commentary_or_perspective" and claim_type != "opinion_claim":
        return True, "commentary form does not match a primary research claim burden"
    if article_type == "protocol_or_registered_report" and any(token in text for token in ["results", "we report", "we observed"]):
        return True, "protocol form is mixed with completed-results language"
    if article_type in {"review", "systematic_review"} and claim_type != "synthesis_claim":
        return True, "review form is mismatched to a non-synthesis primary claim"
    return False, None


def classify_package(payload: dict[str, Any], parsing: dict[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    article_type = _article_type(payload, text)
    claim_type = _claim_type(article_type, text)
    outlet_profile = _outlet_profile(payload, text)
    domain_module = _domain_module(article_type, claim_type, text)
    mismatch, reason = _article_claim_mismatch(article_type, claim_type, text)
    if not parsing.get("central_claim"):
        mismatch = True
        reason = reason or "no recoverable central claim is available for article/claim coherence"
    return {
        "article_type": article_type,
        "claim_type": claim_type,
        "outlet_profile": outlet_profile,
        "domain_module": domain_module,
        "article_claim_mismatch": mismatch,
        "article_claim_mismatch_reason": reason,
    }
