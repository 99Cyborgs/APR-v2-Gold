from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path

import yaml

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


def test_doctor_cli_smoke():
    result = _run("doctor")
    payload = json.loads(result.stdout)
    if result.returncode == 0:
        assert payload["status"] == "ok"
    else:
        assert payload == {"status": "error", "git_status": "dirty"}


def test_audit_render_goldset_and_packs_cli_smoke(tmp_path: Path):
    record_path = tmp_path / "record.json"
    review_path = tmp_path / "review_record.json"
    report_path = tmp_path / "report.md"
    goldset_path = tmp_path / "goldset.json"
    ledger_path = tmp_path / "goldset_ledger.jsonl"

    audit = _run("audit", "fixtures/inputs/reviewable_sound_paper.json", "--output", str(record_path))
    assert audit.returncode == 0, audit.stderr or audit.stdout
    assert record_path.exists()

    review = _run(
        "review",
        "fixtures/inputs/reviewable_sound_paper.json",
        "--profile",
        "nature_selective",
        "--output",
        str(review_path),
    )
    assert review.returncode == 0, review.stderr or review.stdout
    reviewed_record = json.loads(review_path.read_text(encoding="utf-8"))
    assert reviewed_record["classification"]["outlet_profile"] == "nature_selective"

    render = _run("render", str(record_path), "--output", str(report_path))
    assert render.returncode == 0, render.stderr or render.stdout
    assert report_path.exists()

    goldset = _run(
        "goldset",
        "--output",
        str(goldset_path),
        "--ledger-path",
        str(ledger_path),
        "--baseline-window",
        "3",
        "--regression-threshold",
        "0.2",
        "--fatal-weight-scale",
        "1.5",
    )
    assert goldset.returncode == 0, goldset.stderr or goldset.stdout
    assert goldset_path.exists()
    assert ledger_path.exists()
    goldset_summary = json.loads(goldset_path.read_text(encoding="utf-8"))
    governance_report = json.loads((tmp_path / "governance_report.json").read_text(encoding="utf-8"))
    ledger_entry = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[-1])
    assert goldset_summary["governance"]["baseline_window"] == 3
    assert goldset_summary["governance"]["fatal_weight_scale"] == 1.5
    assert governance_report == goldset_summary["governance_report"]
    assert ledger_entry["governance_report"] == goldset_summary["governance_report"]
    assert ledger_entry["case_outcomes"][0]["decision_recommendation"] == goldset_summary["cases"][0]["decision_recommendation"]

    packs = _run(
        "packs",
        "--pack-path",
        "fixtures/external_packs/apr-pack-physics",
        "--pack-path",
        "fixtures/external_packs/apr-pack-clinical",
    )
    assert packs.returncode == 0, packs.stderr or packs.stdout
    pack_report = json.loads(packs.stdout)
    assert [item["pack_id"] for item in pack_report["loaded_packs"]] == ["physics_pack", "clinical_pack"]
    assert pack_report["pack_load_failures"] == []


def test_goldset_holdout_eval_cli_smoke(tmp_path: Path):
    manifest = yaml.safe_load((ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["split"] = "holdout"
            case["gate_behavior"] = "exclude"
            break

    manifest_path = tmp_path / "holdout_manifest.yaml"
    output_path = tmp_path / "holdout_summary.json"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    result = _run("goldset", "--manifest", str(manifest_path), "--holdout", "--no-ledger", "--output", str(output_path))
    assert result.returncode == 0, result.stderr or result.stdout

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["evaluation_mode"] == "holdout_blind"
    assert summary["total_cases"] == 1
    assert summary["cases"][0]["expected_redacted"] is True
    assert summary["cases"][0]["decision_recommendation"] is None
    assert all(error_class == "masked_holdout_error" for error_class in summary["cases"][0]["error_classes"])


def test_goldset_extended_plane_flags_cli_smoke(tmp_path: Path):
    output_path = tmp_path / "goldset_extended_summary.json"

    result = _run(
        "goldset",
        "--output",
        str(output_path),
        "--no-ledger",
        "--loss-quantization",
        "--enable-editorial-weight",
        "--separate-planes",
        "--drift-counterfactuals",
        "--export-calibration-extended",
        "--leakage-guard",
        "--attribution-identifiability",
        "--invariance-trace",
        "--strict-surface-contract",
        "--holdout-blindness-level",
        "moderate",
        "--drift-intervention",
        "on",
    )
    assert result.returncode == 0, result.stderr or result.stdout

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    first_case = summary["cases"][0]
    first_calibration_case = summary["calibration_export"]["cases"][0]

    assert summary["governance"]["planes"]["explicit_cli_flag"] is True
    assert summary["governance"]["loss_quantization"]["enabled"] is True
    assert summary["governance"]["editorial_penalty_weight"] == 0.05
    assert summary["governance"]["drift_counterfactuals"]["enabled"] is True
    assert summary["governance"]["holdout_blindness"]["level"] == "moderate"
    assert summary["governance"]["drift_intervention"]["enabled"] is True
    assert summary["governance"]["leakage_guard"]["enabled"] is True
    assert summary["governance"]["attribution_identifiability"]["enabled"] is True
    assert summary["governance"]["invariance_trace"]["enabled"] is True
    assert summary["governance"]["surface_contract"]["enabled"] is True
    assert first_case["scientific_score"]["total"] is not None
    assert first_case["scientific_score_vector"]["claim_clarity"] is not None
    assert first_case["editorial_score"]["total"] is not None
    assert first_case["loss_band"] in {"low", "medium", "high"}
    assert first_case["leakage_guard"]["query_budget"] >= 1
    assert first_case["counterfactual_extended"]["identifiability"] in {"unique", "degenerate", "correlated"}
    assert first_case["invariance_trace"]["trace_hash"] is not None
    assert first_case["surface_contract"]["mixed_usage_violation"] is False
    assert first_calibration_case["scientific_score_vector"]["total"] is not None
    assert first_calibration_case["editorial_score_vector"]["total"] is not None
    assert first_calibration_case["calibration_extended"]["scientific_vector"]["claim_clarity"] is not None
    assert first_calibration_case["calibration_extended"]["surface_contract"]["mixed_usage_violation"] is False
