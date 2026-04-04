from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "apr_core.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_governance_report_json_is_written_per_run(tmp_path: Path):
    summary_path = tmp_path / "goldset_summary.json"
    governance_report_path = tmp_path / "governance_report.json"

    result = _run(
        "goldset",
        "--output",
        str(summary_path),
        "--no-ledger",
        "--leakage-guard",
        "--attribution-identifiability",
        "--invariance-trace",
        "--strict-surface-contract",
    )
    assert result.returncode == 0, result.stderr or result.stdout

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    governance_report = json.loads(governance_report_path.read_text(encoding="utf-8"))

    assert governance_report == summary["governance_report"]
    assert {
        "leakage_resilience_score",
        "attribution_stability_score",
        "invariance_precision",
        "invariance_recall",
        "surface_contract_violations",
        "enabled_layers",
        "layer_modes",
        "contract_status",
        "warning_mode",
        "reproducibility_tiers",
        "layers",
    }.issubset(governance_report)
    assert governance_report["leakage_resilience_score"] >= 0
    assert governance_report["attribution_stability_score"] >= 0
    assert governance_report["invariance_precision"] >= 0
    assert governance_report["invariance_recall"] >= 0
    assert governance_report["surface_contract_violations"] >= 0
    assert governance_report["warning_mode"]["active"] is False
    assert governance_report["layers"]["surface_contract"]["status"] == "pass"
    assert governance_report["reproducibility_tiers"]["leakage_guard"] == "bounded_nondeterministic"
