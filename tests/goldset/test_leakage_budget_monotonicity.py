from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset.governance.leakage_guard import GOVERNANCE_VERSION, enforce_leakage_envelope  # noqa: E402


def test_leakage_budget_never_increases_and_noise_stays_bounded():
    history: list[dict[str, object]] = []
    budgets: list[int] = []
    epsilon_budgets: list[float] = []
    noise_scales: list[float] = []

    for run_id in range(1, 6):
        envelope = enforce_leakage_envelope(
            "case-a",
            {
                "loss": 3.0,
                "epsilon": 1.0,
                "budget_cap": 8,
                "run_id": run_id,
                "governance_version": GOVERNANCE_VERSION,
            },
            history,
        )
        budgets.append(envelope["query_budget"])
        epsilon_budgets.append(envelope["epsilon_budget"])
        noise_scales.append(envelope["noise_scale"])
        history.append({"case_id": "case-a"})

    assert budgets == sorted(budgets, reverse=True)
    assert epsilon_budgets == sorted(epsilon_budgets, reverse=True)
    assert all(noise_scale <= epsilon_budget <= 1.0 for noise_scale, epsilon_budget in zip(noise_scales, epsilon_budgets, strict=False))
