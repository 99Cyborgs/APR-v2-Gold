from __future__ import annotations

from collections import Counter
from typing import Any

from . import attribution_identifiability
from . import invariance_trace
from . import leakage_guard
from . import surface_contract

GOVERNANCE_FIELD_NAMES = ("leakage_guard", "counterfactual_extended", "invariance_trace", "surface_contract")
REPRODUCIBILITY_TIERS = {
    "leakage_guard": "bounded_nondeterministic",
    "attribution_identifiability": "deterministic",
    "invariance_trace": "deterministic",
    "surface_contract": "deterministic",
}
STRICT_LAYER_MODE = "strict"
DISABLED_LAYER_MODE = "disabled"


def resolve_enabled_governance_layers(governance: dict[str, Any]) -> dict[str, bool]:
    return {
        "leakage_guard": bool(governance.get("leakage_guard", {}).get("enabled")),
        "attribution_identifiability": bool(governance.get("attribution_identifiability", {}).get("enabled")),
        "invariance_trace": bool(governance.get("invariance_trace", {}).get("enabled")),
        "surface_contract": bool(governance.get("surface_contract", {}).get("enabled")),
    }


def normalize_reason_codes(reason_codes: list[str] | None) -> list[str]:
    return sorted(dict.fromkeys(reason_code for reason_code in (reason_codes or []) if reason_code))


def resolve_layer_mode(governance: dict[str, Any], layer_name: str) -> str:
    return STRICT_LAYER_MODE if resolve_enabled_governance_layers(governance).get(layer_name, False) else DISABLED_LAYER_MODE


def reproducibility_tier(layer_name: str) -> str:
    return REPRODUCIBILITY_TIERS[layer_name]


def validate_input_surface_contract(payload_input: dict[str, Any], governance: dict[str, Any]) -> None:
    enabled_layers = resolve_enabled_governance_layers(governance)
    if not enabled_layers["surface_contract"]:
        return
    surface_contract.enforce_surface_exclusivity({"ingestion": payload_input}, strict_surface_contract=True)


def validate_scoring_surface_contract(
    legacy_scientific_score_vector: dict[str, Any],
    scientific_score_vector: dict[str, Any],
    governance: dict[str, Any],
    payload_input: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    enabled_layers = resolve_enabled_governance_layers(governance)
    if not enabled_layers["surface_contract"]:
        return None
    export_surfaces = surface_contract.build_scientific_surface_bundle(
        legacy_surface=legacy_scientific_score_vector,
        native_surface=scientific_score_vector,
        alias_key="scientific_vector",
        legacy_key="scientific_vector_legacy",
        native_key="scientific_vector_native",
    )
    payload = {
        "input": payload_input or {},
        "scoring": {
            "scientific_score": legacy_scientific_score_vector,
        },
        "aggregation": {
            "scientific_score_vector": scientific_score_vector,
        },
        "export": {
            "scientific_score": legacy_scientific_score_vector,
            **export_surfaces,
        },
    }
    status = surface_contract.enforce_surface_exclusivity(payload, strict_surface_contract=True)
    return {
        "legacy_present": status["legacy_present"],
        "native_present": status["native_present"],
        "mixed_usage_violation": status["mixed_usage_violation"],
        "reason_codes": status["reason_codes"],
        "status": status["status"],
        "enforcement_mode": status["enforcement_mode"],
        "warning_mode_active": status["warning_mode_active"],
    }


def _build_leakage_guard(case: dict[str, Any], governance: dict[str, Any], case_history: list[dict[str, Any]]) -> dict[str, Any]:
    envelope = leakage_guard.enforce_leakage_envelope(
        case["case_id"],
        {
            "ranks": [item["feature"] for item in case.get("drift_counterfactuals") or []],
            "loss": float(case.get("scientific_loss") or 0.0),
            "epsilon": governance["leakage_guard"]["epsilon"],
            "budget_cap": governance["leakage_guard"]["budget_cap"],
            "run_id": len(case_history) + 1,
            "governance_version": leakage_guard.GOVERNANCE_VERSION,
        },
        case_history,
    )
    return {
        "rank_jitter_applied": envelope["rank_jitter_applied"],
        "noise_scale": envelope["noise_scale"],
        "query_budget": envelope["query_budget"],
        "epsilon_budget": envelope["epsilon_budget"],
        "budget_used": envelope["budget_used"],
        "governance_version": envelope["governance_version"],
    }


def _build_counterfactual_extended(case: dict[str, Any]) -> dict[str, Any]:
    return attribution_identifiability.build_counterfactual_summary(
        list(case.get("drift_counterfactuals") or []),
        case.get("drift_counterfactual_stability"),
    )


def _build_invariance_trace(
    case: dict[str, Any],
    observed: dict[str, Any],
    governance: dict[str, Any],
    case_history: list[dict[str, Any]],
) -> dict[str, Any]:
    return invariance_trace.build_invariance_trace(
        case,
        observed,
        governance["severity_weights"],
        case_history,
    )


def _build_surface_contract(
    case: dict[str, Any],
    governance: dict[str, Any],
) -> dict[str, Any] | None:
    existing = case.get("surface_contract")
    if existing is not None:
        return existing
    return validate_scoring_surface_contract(
        case["scientific_score_vector_legacy"],
        case["scientific_score_vector_native"],
        governance,
    )


def apply_case_governance(
    case: dict[str, Any],
    *,
    observed: dict[str, Any],
    governance: dict[str, Any],
    case_history: list[dict[str, Any]],
) -> dict[str, Any]:
    enabled_layers = resolve_enabled_governance_layers(governance)
    updates: dict[str, Any] = {}
    if enabled_layers["attribution_identifiability"]:
        updates["counterfactual_extended"] = _build_counterfactual_extended(case)
    if enabled_layers["surface_contract"]:
        updates["surface_contract"] = _build_surface_contract(case, governance)
    if enabled_layers["leakage_guard"]:
        updates["leakage_guard"] = _build_leakage_guard(case, governance, case_history)
    if enabled_layers["invariance_trace"]:
        updates["invariance_trace"] = _build_invariance_trace(case, observed, governance, case_history)
    return {**case, **updates}


def export_governance_fields(case: dict[str, Any]) -> dict[str, Any]:
    return {
        field_name: case[field_name]
        for field_name in GOVERNANCE_FIELD_NAMES
        if case.get(field_name) is not None
    }


def _active_cases(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [case for case in case_results if case.get("case_state") == "active"]


def _layer_status(*, enabled: bool, hard_fail_reason_codes: list[str], soft_warning_reason_codes: list[str]) -> str:
    if not enabled:
        return "disabled"
    if hard_fail_reason_codes:
        return "hard_fail"
    if soft_warning_reason_codes:
        return "warning"
    return "pass"


def _build_leakage_report(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> dict[str, Any]:
    enabled = resolve_enabled_governance_layers(governance)["leakage_guard"]
    active_cases = _active_cases(case_results)
    leakage_states = [
        (case["case_id"], case.get("leakage_guard") or {})
        for case in active_cases
        if case.get("leakage_guard") is not None
    ]
    exhausted_case_ids = sorted(case_id for case_id, state in leakage_states if int(state.get("query_budget", 0) or 0) <= 0)
    jittered_case_ids = sorted(case_id for case_id, state in leakage_states if bool(state.get("rank_jitter_applied")))
    soft_warning_reason_codes = normalize_reason_codes(
        [
            "leakage_budget_exhausted" if exhausted_case_ids else "",
            "leakage_rank_jitter_applied" if jittered_case_ids else "",
        ]
    )
    budgets = [int(state.get("query_budget", 0) or 0) for _, state in leakage_states]
    budget_used = [int(state.get("budget_used", 0) or 0) for _, state in leakage_states]
    epsilon_budgets = [float(state.get("epsilon_budget", 0.0) or 0.0) for _, state in leakage_states]
    report = {
        "enabled": enabled,
        "enforcement_mode": resolve_layer_mode(governance, "leakage_guard"),
        "reproducibility_tier": reproducibility_tier("leakage_guard"),
        "warning_mode_active": False,
        "hard_fail_reason_codes": [],
        "soft_warning_reason_codes": soft_warning_reason_codes,
        "budget_cap": int(governance.get("leakage_guard", {}).get("budget_cap", 0) or 0) if enabled else None,
        "observed_case_count": len(leakage_states),
        "query_budget_remaining_min": min(budgets) if budgets else None,
        "query_budget_remaining_max": max(budgets) if budgets else None,
        "budget_used_max": max(budget_used) if budget_used else None,
        "epsilon_budget_max": round(max(epsilon_budgets), 6) if epsilon_budgets else None,
        "exhausted_case_count": len(exhausted_case_ids),
        "exhausted_case_ids": exhausted_case_ids,
        "rank_jitter_case_ids": jittered_case_ids,
    }
    report["status"] = _layer_status(
        enabled=enabled,
        hard_fail_reason_codes=report["hard_fail_reason_codes"],
        soft_warning_reason_codes=report["soft_warning_reason_codes"],
    )
    return report


def _build_attribution_report(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> dict[str, Any]:
    enabled = resolve_enabled_governance_layers(governance)["attribution_identifiability"]
    active_cases = _active_cases(case_results)
    counterfactual_states = [
        (case["case_id"], case.get("counterfactual_extended") or {})
        for case in active_cases
        if case.get("counterfactual_extended") is not None
    ]
    status_counts = Counter(
        str(state.get("identifiability_status") or "unreported")
        for _, state in counterfactual_states
    )
    non_unique_case_ids = sorted(
        case_id
        for case_id, state in counterfactual_states
        if state.get("identifiability_status") not in {None, "unique"}
    )
    soft_warning_reason_codes = normalize_reason_codes(
        ["non_identifiable_attribution" if non_unique_case_ids else ""]
    )
    report = {
        "enabled": enabled,
        "enforcement_mode": resolve_layer_mode(governance, "attribution_identifiability"),
        "reproducibility_tier": reproducibility_tier("attribution_identifiability"),
        "warning_mode_active": False,
        "hard_fail_reason_codes": [],
        "soft_warning_reason_codes": soft_warning_reason_codes,
        "observed_case_count": len(counterfactual_states),
        "identifiability_status_counts": dict(sorted(status_counts.items())),
        "non_unique_case_ids": non_unique_case_ids,
    }
    report["status"] = _layer_status(
        enabled=enabled,
        hard_fail_reason_codes=report["hard_fail_reason_codes"],
        soft_warning_reason_codes=report["soft_warning_reason_codes"],
    )
    return report


def _build_invariance_report(
    case_results: list[dict[str, Any]],
    governance: dict[str, Any],
    *,
    invariance_precision: float,
    invariance_recall: float,
) -> dict[str, Any]:
    enabled = resolve_enabled_governance_layers(governance)["invariance_trace"]
    active_cases = _active_cases(case_results)
    trace_states = [
        (case["case_id"], case.get("invariance_trace") or {})
        for case in active_cases
        if case.get("invariance_trace") is not None
    ]
    drift_case_ids = sorted(case_id for case_id, state in trace_states if bool(state.get("drift_detected")))
    soft_warning_reason_codes = normalize_reason_codes(
        ["silent_drift_detected" if drift_case_ids else ""]
    )
    drift_scores = [float(state.get("drift_score", 0.0) or 0.0) for _, state in trace_states]
    report = {
        "enabled": enabled,
        "enforcement_mode": resolve_layer_mode(governance, "invariance_trace"),
        "reproducibility_tier": reproducibility_tier("invariance_trace"),
        "warning_mode_active": False,
        "hard_fail_reason_codes": [],
        "soft_warning_reason_codes": soft_warning_reason_codes,
        "observed_case_count": len(trace_states),
        "drift_case_ids": drift_case_ids,
        "drift_case_count": len(drift_case_ids),
        "drift_score_max": round(max(drift_scores), 6) if drift_scores else None,
        "precision": invariance_precision,
        "recall": invariance_recall,
    }
    report["status"] = _layer_status(
        enabled=enabled,
        hard_fail_reason_codes=report["hard_fail_reason_codes"],
        soft_warning_reason_codes=report["soft_warning_reason_codes"],
    )
    return report


def _build_surface_contract_report(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> dict[str, Any]:
    enabled = resolve_enabled_governance_layers(governance)["surface_contract"]
    active_cases = _active_cases(case_results)
    contract_states = [
        (case["case_id"], case.get("surface_contract") or {})
        for case in active_cases
        if case.get("surface_contract") is not None
    ]
    violating_case_ids = sorted(
        case_id
        for case_id, state in contract_states
        if bool(state.get("mixed_usage_violation"))
    )
    legacy_present_count = sum(1 for _, state in contract_states if bool(state.get("legacy_present")))
    native_present_count = sum(1 for _, state in contract_states if bool(state.get("native_present")))
    hard_fail_reason_codes = normalize_reason_codes(
        [surface_contract.SURFACE_CONTRACT_MIXED_REASON if violating_case_ids else ""]
    )
    report = {
        "enabled": enabled,
        "enforcement_mode": resolve_layer_mode(governance, "surface_contract"),
        "reproducibility_tier": reproducibility_tier("surface_contract"),
        "warning_mode_active": False,
        "hard_fail_reason_codes": hard_fail_reason_codes,
        "soft_warning_reason_codes": [],
        "observed_case_count": len(contract_states),
        "legacy_present_case_count": legacy_present_count,
        "native_present_case_count": native_present_count,
        "violation_case_count": len(violating_case_ids),
        "violation_case_ids": violating_case_ids,
    }
    report["status"] = _layer_status(
        enabled=enabled,
        hard_fail_reason_codes=report["hard_fail_reason_codes"],
        soft_warning_reason_codes=report["soft_warning_reason_codes"],
    )
    return report


def build_governance_report(
    case_results: list[dict[str, Any]],
    governance: dict[str, Any],
    *,
    leakage_resilience_score: float,
    attribution_stability_score: float,
    invariance_precision: float,
    invariance_recall: float,
    surface_contract_violations: int,
) -> dict[str, Any]:
    enabled_layers = resolve_enabled_governance_layers(governance)
    layers = {
        "leakage_guard": _build_leakage_report(case_results, governance),
        "attribution_identifiability": _build_attribution_report(case_results, governance),
        "invariance_trace": _build_invariance_report(
            case_results,
            governance,
            invariance_precision=invariance_precision,
            invariance_recall=invariance_recall,
        ),
        "surface_contract": _build_surface_contract_report(case_results, governance),
    }
    hard_fail_reason_codes = normalize_reason_codes(
        [
            reason_code
            for layer in layers.values()
            for reason_code in layer["hard_fail_reason_codes"]
        ]
    )
    soft_warning_reason_codes = normalize_reason_codes(
        [
            reason_code
            for layer in layers.values()
            for reason_code in layer["soft_warning_reason_codes"]
        ]
    )
    warning_layers = sorted(layer_name for layer_name, report in layers.items() if report["warning_mode_active"])
    return {
        "leakage_resilience_score": leakage_resilience_score,
        "attribution_stability_score": attribution_stability_score,
        "invariance_precision": invariance_precision,
        "invariance_recall": invariance_recall,
        "surface_contract_violations": surface_contract_violations,
        "enabled_layers": sorted(layer_name for layer_name, enabled in enabled_layers.items() if enabled),
        "layer_modes": {
            layer_name: report["enforcement_mode"]
            for layer_name, report in layers.items()
        },
        "contract_status": {
            "status": "hard_fail" if hard_fail_reason_codes else "pass",
            "hard_fail_reason_codes": hard_fail_reason_codes,
            "soft_warning_reason_codes": soft_warning_reason_codes,
        },
        "warning_mode": {
            "active": bool(warning_layers),
            "layers": warning_layers,
            "reason_codes": normalize_reason_codes(
                [
                    reason_code
                    for layer_name, report in layers.items()
                    if report["warning_mode_active"]
                    for reason_code in report["soft_warning_reason_codes"]
                ]
            ),
        },
        "reproducibility_tiers": {
            layer_name: report["reproducibility_tier"]
            for layer_name, report in layers.items()
        },
        "layers": layers,
    }
