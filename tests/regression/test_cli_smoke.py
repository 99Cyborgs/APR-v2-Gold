from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apr_core import cli


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
    assert result.returncode == 0, result.stderr or result.stdout
    assert payload["status"] == "ok"
    assert payload["git_status"] in {"clean", "dirty", "unavailable"}


def test_readiness_cli_smoke():
    result = _run("readiness")
    payload = json.loads(result.stdout)
    if result.returncode == 0:
        assert payload["status"] == "ok"
        assert payload["git_status"] == "clean"
    else:
        assert payload["status"] == "error"
        assert payload["reason"] == "release_readiness_requires_clean_worktree"
        assert payload["git_status"] == "dirty"


def test_doctor_command_reports_dirty_git_without_failing(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_doctor_report",
        lambda: (
            {
                "status": "ok",
                "repo_root": str(ROOT),
                "contract_version": "2.1.0",
                "policy_layer_version": "2.1.0",
                "git_status": "dirty",
                "git_detail": "",
            },
            0,
        ),
    )

    assert cli.cmd_doctor(None) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["git_status"] == "dirty"


def test_readiness_command_rejects_dirty_git(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_doctor_report",
        lambda: (
            {
                "status": "ok",
                "repo_root": str(ROOT),
                "contract_version": "2.1.0",
                "policy_layer_version": "2.1.0",
                "git_status": "dirty",
                "git_detail": "",
            },
            0,
        ),
    )

    assert cli.cmd_readiness(None) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["reason"] == "release_readiness_requires_clean_worktree"
    assert payload["git_status"] == "dirty"


def test_audit_render_goldset_and_packs_cli_smoke(tmp_path: Path):
    record_path = tmp_path / "record.json"
    defense_path = tmp_path / "defense.json"
    questions_path = tmp_path / "questions.json"
    review_path = tmp_path / "review_record.json"
    report_path = tmp_path / "report.md"
    goldset_path = tmp_path / "goldset.json"
    ledger_path = tmp_path / "goldset_ledger.jsonl"
    annotation_dir = tmp_path / "annotation_view"

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

    defense = _run(
        "defense",
        str(record_path),
        "--manuscript-package",
        "fixtures/inputs/reviewable_sound_paper.json",
        "--context",
        "journal_referee",
        "--output",
        str(defense_path),
    )
    assert defense.returncode == 0, defense.stderr or defense.stdout
    defense_record = json.loads(defense_path.read_text(encoding="utf-8"))
    assert defense_record["artifact_type"] == "DefenseReadinessRecord"

    questions = _run(
        "questions",
        str(record_path),
        "--manuscript-package",
        "fixtures/inputs/reviewable_sound_paper.json",
        "--defense",
        str(defense_path),
        "--context",
        "journal_referee",
        "--output",
        str(questions_path),
    )
    assert questions.returncode == 0, questions.stderr or questions.stdout
    question_record = json.loads(questions_path.read_text(encoding="utf-8"))
    assert question_record["artifact_type"] == "QuestionChallengeRecord"

    annotate = _run(
        "annotate-pdf",
        str(record_path),
        "--manuscript-package",
        "fixtures/inputs/reviewable_sound_paper.json",
        "--defense",
        str(defense_path),
        "--questions",
        str(questions_path),
        "--source-pdf",
        "fixtures/inputs/reviewable_sound_paper.pdf",
        "--output-dir",
        str(annotation_dir),
    )
    assert annotate.returncode == 0, annotate.stderr or annotate.stdout
    annotation_payload = json.loads(annotate.stdout)
    assert annotation_payload["status"] == "ok"
    assert Path(annotation_payload["manifest_path"]).exists()
    assert Path(annotation_payload["html_path"]).exists()

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
    assert goldset_summary["calibration_ledger"]["entry_appended"] is True
    assert governance_report == goldset_summary["governance_report"]
    assert ledger_entry["governance_report"] == goldset_summary["governance_report"]
    assert ledger_entry["policy_layer_version"] == goldset_summary["policy_layer_version"]
    assert ledger_entry["runtime_identity"] == goldset_summary["runtime_identity"]
    assert ledger_entry["repo_state"]["git_dirty"] in {True, False, None}
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


def test_external_paper_goldset_cli_smoke(tmp_path: Path):
    output_path = tmp_path / "external_papers_summary.json"

    result = _run(
        "goldset",
        "--manifest",
        "benchmarks/external_papers_dev/manifest.yaml",
        "--no-ledger",
        "--output",
        str(output_path),
    )
    assert result.returncode == 0, result.stderr or result.stdout

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["failed"] == 0
    assert summary["external_dissection_summary"]["available"] is True
    assert summary["external_dissection_summary"]["passed_case_count"] == summary["total_cases"]


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


def test_validate_goldset_script_fails_on_contract_version_drift(tmp_path: Path):
    manifest = yaml.safe_load((ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["contract_version"] = "9.9.9"
    manifest_path = tmp_path / "drifted_manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "scripts/validate_goldset.py", "--manifest", str(manifest_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "contract_version=9.9.9" in (result.stderr or result.stdout)
