from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset import run_goldset_manifest  # noqa: E402
from apr_core.goldset.leakage_guard import GOVERNANCE_VERSION, bind_governance_seed, enforce_leakage_envelope  # noqa: E402


def test_leakage_guard_preserves_decision_and_loss_band_across_repeated_runs(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"

    first = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", ledger_path=ledger_path, leakage_guard=True)
    second = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", ledger_path=ledger_path, leakage_guard=True)

    first_case = next(case for case in first["cases"] if case["case_id"] == "reviewable_sound_paper")
    second_case = next(case for case in second["cases"] if case["case_id"] == "reviewable_sound_paper")

    assert first_case["decision_recommendation"] == second_case["decision_recommendation"]
    assert first_case["loss_band"] == second_case["loss_band"]
    assert first_case["leakage_guard"]["query_budget"] == 8
    assert second_case["leakage_guard"]["query_budget"] == 7
    assert first_case["leakage_guard"]["noise_scale"] >= 0
    assert second_case["leakage_guard"]["noise_scale"] >= 0


def test_leakage_envelope_is_seed_bound_and_budget_bounded():
    true_loss = 3.0
    history: list[dict[str, object]] = []

    noisy_losses: list[float] = []
    seen_seeds: list[int] = []
    for run_id in range(1, 6):
        envelope = enforce_leakage_envelope(
            "case-a",
            {
                "loss": true_loss,
                "budget_cap": 8,
                "epsilon": 1.0,
                "ranks": ["a", "b"],
                "run_id": run_id,
                "governance_version": GOVERNANCE_VERSION,
            },
            history,
        )
        noisy_losses.append(envelope["noisy_loss"])
        seen_seeds.append(envelope["seed"])
        assert envelope["seed"] == bind_governance_seed("case-a", run_id, GOVERNANCE_VERSION)
        assert envelope["noise_scale"] <= envelope["epsilon_budget"] <= 1.0
        history.append({"case_id": "case-a"})

    assert len(set(seen_seeds)) == len(seen_seeds)
    assert len(set(noisy_losses)) == len(noisy_losses)
