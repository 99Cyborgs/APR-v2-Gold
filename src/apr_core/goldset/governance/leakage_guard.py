from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

GOVERNANCE_VERSION = "1"
_LEAKAGE_GUARD_SECRET = secrets.token_bytes(16)


def bind_governance_seed(
    case_id: str,
    run_id: int | str,
    governance_version: str = GOVERNANCE_VERSION,
) -> int:
    digest = hashlib.sha256(f"{case_id}:{run_id}:{governance_version}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _count_previous_queries(case_id: str, history: list[dict[str, Any]]) -> int:
    return sum(1 for item in history if item.get("case_id") == case_id)


def _epsilon_budget(epsilon: float, query_budget: int, budget_cap: int) -> float:
    if budget_cap <= 0 or query_budget <= 0 or epsilon <= 0:
        return 0.0
    return round(float(epsilon) * (query_budget / float(budget_cap)), 6)


def _secret_unit_interval(*parts: Any) -> float:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(_LEAKAGE_GUARD_SECRET + payload).digest()
    return int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)


def _centered_unit_interval(*parts: Any) -> float:
    return (_secret_unit_interval(*parts) * 2.0) - 1.0


def _history_fingerprint(case_id: str, history: list[dict[str, Any]]) -> str:
    relevant: list[dict[str, Any]] = []
    for item in history:
        if item.get("case_id") != case_id:
            continue
        leakage_state = item.get("leakage_guard") or {}
        relevant.append(
            {
                "budget_used": leakage_state.get("budget_used"),
                "governance_version": leakage_state.get("governance_version"),
                "query_budget": leakage_state.get("query_budget"),
                "status": item.get("status"),
            }
        )
    encoded = json.dumps(relevant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{case_id}:{len(relevant)}:{encoded}".encode("utf-8")).hexdigest()


def _jitter_rankings(ranks: list[Any], *, seed: int, history_fingerprint: str, apply_jitter: bool) -> tuple[list[Any], bool]:
    ordered = list(ranks)
    if not apply_jitter or len(ordered) < 2:
        return ordered, False
    decorated = [
        (
            hashlib.sha256(f"{seed}:{history_fingerprint}:{index}:{value}".encode("utf-8")).hexdigest(),
            value,
        )
        for index, value in enumerate(ordered)
    ]
    jittered = [value for _, value in sorted(decorated)]
    return jittered, jittered != ordered


def bounded_noise(seed: int, epsilon_budget: float, history_fingerprint: str = "") -> float:
    if epsilon_budget <= 0:
        return 0.0
    hidden_bias = _centered_unit_interval("bias", seed, history_fingerprint)
    hidden_magnitude = 0.25 + (abs(hidden_bias) * 0.4)
    hidden_component = hidden_magnitude if hidden_bias >= 0 else -hidden_magnitude
    correlated_component = _centered_unit_interval("correlated", seed, history_fingerprint) * 0.35
    combined = hidden_component + correlated_component
    if abs(combined) < 0.2:
        combined = 0.2 if hidden_component >= 0 else -0.2
    combined = max(-1.0, min(1.0, combined))
    return round(combined * float(epsilon_budget), 6)


def enforce_leakage_envelope(case_id: str, outputs: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    budget_cap = max(1, int(outputs.get("budget_cap", 8)))
    previous_queries = _count_previous_queries(case_id, history)
    query_budget = max(budget_cap - previous_queries, 0)
    epsilon = float(outputs.get("epsilon", 0.0) or 0.0)
    epsilon_budget = _epsilon_budget(epsilon, query_budget, budget_cap)
    run_id = outputs.get("run_id", previous_queries + 1)
    governance_version = str(outputs.get("governance_version", GOVERNANCE_VERSION))
    seed = int(outputs.get("seed", bind_governance_seed(case_id, run_id, governance_version)))
    history_fingerprint = _history_fingerprint(case_id, history)
    noise = bounded_noise(seed, epsilon_budget, history_fingerprint)
    loss = float(outputs.get("loss", 0.0) or 0.0)
    jittered_ranks, rank_jitter_applied = _jitter_rankings(
        list(outputs.get("ranks", [])),
        seed=seed,
        history_fingerprint=history_fingerprint,
        apply_jitter=previous_queries > 0 and query_budget > 0,
    )

    return {
        "case_id": case_id,
        "rank_jitter_applied": rank_jitter_applied,
        "noise_scale": abs(noise),
        "query_budget": query_budget,
        "noisy_loss": None if query_budget <= 0 else round(loss + noise, 6),
        "jittered_ranks": jittered_ranks,
        "seed": seed,
        "run_id": str(run_id),
        "governance_version": governance_version,
        "budget_cap": budget_cap,
        "budget_used": min(previous_queries, budget_cap),
        "epsilon_budget": epsilon_budget,
    }
