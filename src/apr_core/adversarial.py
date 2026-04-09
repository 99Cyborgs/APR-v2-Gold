from __future__ import annotations

import re
from collections import Counter
from typing import Any

from apr_core.anchors import dedupe_anchors, first_anchor_from_fields, search_anchors
from apr_core.policy import load_policy_layer

BASELINE_MARKERS = ("baseline", "compare", "compares", "relative to", "versus", "replication")
NOVELTY_MARKERS = ("novel", "new", "first", "transformative", "paradigm", "breakthrough")
PARAMETER_MARKERS = ("parameter", "hyperparameter", "tuning", "sweep", "grid search", "learning rate", "epoch", "layers")
SIMULATION_MARKERS = ("simulation", "simulated", "numerical", "toy simulation", "synthetic", "solver")
RHETORICAL_MARKERS = ("universal", "all orbital phenomena", "field-defining", "transformative", "revolutionary", "paradigm")


def _affirmed_marker(text: str, marker: str) -> bool:
    lowered = text.lower()
    pattern = re.compile(rf"\b{re.escape(marker)}\b")
    for match in pattern.finditer(lowered):
        window = lowered[max(0, match.start() - 80) : match.end()]
        if not any(negation in window for negation in ("no ", "without ", "does not ", "never ", "missing ")):
            return True
    return False


def _text(payload: dict[str, Any], parsing: dict[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                payload.get("title"),
                payload.get("abstract"),
                payload.get("manuscript_text"),
                parsing.get("central_claim"),
                parsing.get("novelty_delta_candidate"),
            ],
        )
    ).lower()


def assess_adversarial_resilience(
    payload: dict[str, Any],
    parsing: dict[str, Any],
    classification: dict[str, Any],
    claim_evidence_calibration: dict[str, Any],
) -> dict[str, Any]:
    policy = load_policy_layer()["policy_layer"]["adversarial_resilience"]
    text = _text(payload, parsing)
    flags: list[str] = []

    comparator_present = any(_affirmed_marker(text, marker) for marker in BASELINE_MARKERS) or len(payload.get("references") or []) >= 2
    if classification.get("claim_type") in {"benchmark_claim", "empirical_claim", "replication_claim", "model_claim"} and not comparator_present:
        flags.append("baseline_evasion:no_visible_comparator")
    if classification.get("claim_type") in {"benchmark_claim", "empirical_claim"} and not payload.get("tables") and not payload.get("figures_and_captions"):
        flags.append("baseline_evasion:no_decisive_bearing_object")

    novelty_hits = sum(text.count(marker) for marker in NOVELTY_MARKERS)
    if novelty_hits >= 2 and not parsing.get("novelty_delta_candidate"):
        flags.append("proxy_novelty:novelty_without_delta")
    if novelty_hits >= 2 and not comparator_present:
        flags.append("proxy_novelty:novelty_without_comparator")

    parameter_hits = sum(text.count(marker) for marker in PARAMETER_MARKERS)
    numeric_tokens = sum(token.isdigit() for token in text.replace("%", " ").split())
    if parameter_hits >= 2 and not parsing.get("decisive_support_object"):
        flags.append("parameter_stuffing:parameter_density_without_support")
    if parameter_hits >= 2 and numeric_tokens >= 4 and not payload.get("tables"):
        flags.append("parameter_stuffing:numeric_density_without_table")

    simulation_present = any(marker in text for marker in SIMULATION_MARKERS)
    if simulation_present and classification.get("claim_type") in {"benchmark_claim", "empirical_claim"} and not comparator_present:
        flags.append("simulation_as_proof:simulation_claim_without_comparator")
    if simulation_present and not payload.get("figures_and_captions") and not payload.get("tables"):
        flags.append("simulation_as_proof:simulation_without_claim_bearing_object")

    rhetorical_hits = sum(text.count(marker) for marker in RHETORICAL_MARKERS)
    if rhetorical_hits >= 1:
        flags.append("rhetorical_scope_expansion:broad_scope_language")
    if rhetorical_hits >= 2 and claim_evidence_calibration.get("mismatch", 0) > 0:
        flags.append("rhetorical_scope_expansion:rhetoric_exceeds_support")

    triggered_checks = sorted({flag.split(":", 1)[0] for flag in flags})
    flag_count = len(flags)
    if flag_count >= int(policy["block_submit_threshold"]):
        status = "blocked"
    elif flag_count >= int(policy["downgrade_confidence_threshold"]):
        status = "downgraded"
    elif flag_count > 0:
        status = "watch"
    else:
        status = "clear"

    family_counts = Counter(flag.split(":", 1)[0] for flag in flags)
    anchors = dedupe_anchors(
        [
            parsing.get("central_claim_anchor"),
            parsing.get("decisive_support_object"),
            first_anchor_from_fields(payload, ["abstract", "manuscript_text", "tables", "figures_and_captions"]),
            *search_anchors(payload, BASELINE_MARKERS, max_hits=1),
            *search_anchors(payload, NOVELTY_MARKERS, max_hits=1),
            *search_anchors(payload, PARAMETER_MARKERS, max_hits=1),
            *search_anchors(payload, SIMULATION_MARKERS, max_hits=1),
            *search_anchors(payload, RHETORICAL_MARKERS, max_hits=1),
        ]
    )

    return {
        "flags": flags,
        "flag_count": flag_count,
        "triggered_checks": triggered_checks,
        "status": status,
        "family_counts": dict(sorted(family_counts.items())),
        "evidence_anchors": anchors,
    }
