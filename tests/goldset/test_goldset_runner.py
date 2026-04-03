from pathlib import Path
import copy
import json
import sys

from jsonschema import validate
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))
existing = sys.modules.get("apr_core")
if existing and not str(getattr(existing, "__file__", "")).startswith(str(SRC)):
    for name in list(sys.modules):
        if name == "apr_core" or name.startswith("apr_core."):
            sys.modules.pop(name, None)

from apr_core.goldset import (  # noqa: E402
    default_goldset_governance_config,
    load_goldset_ledger_entry_schema,
    load_goldset_manifest,
    load_goldset_manifest_schema,
    load_goldset_summary_schema,
    run_goldset_manifest,
)
import apr_core.goldset.runner as goldset_runner  # noqa: E402


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest_path


def test_goldset_manifest_passes_schema_validation():
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    validate(instance=manifest, schema=load_goldset_manifest_schema())
    assert {stratum["name"] for stratum in manifest["strata"]} == {"core_gold", "stress_gold", "holdout"}
    assert len(manifest["cases"]) == 8
    assert all(case["central_claim"] for case in manifest["cases"])
    assert all(case["claim_type"] for case in manifest["cases"])
    assert all("recommendation_band" in case["expected_decision"] for case in manifest["cases"])


def test_goldset_runner_passes_fixture_manifest_and_emits_governance_fields():
    summary = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    validate(instance=summary, schema=load_goldset_summary_schema())

    assert summary["failed"] == 0
    assert summary["gates"]["status"] == "pass"
    assert summary["evaluation_mode"] == "development"
    assert summary["decision_algebra"]["total_score"] == 0
    assert summary["decision_algebra"]["recommendation_loss_model"] == "asymmetric_matrix"
    assert summary["decision_consistency"]["exact_match_cases"] == 8
    assert summary["governance"]["baseline_window"] == default_goldset_governance_config()["baseline_window"]
    assert summary["editorial_first_pass_score"]["case_count"] == summary["total_cases"]
    assert summary["calibration_export"]["case_count"] == summary["total_cases"]
    assert summary["system_diagnostics"]["baseline"]["available"] is False
    assert summary["strata"]["core_gold"]["total"] == 5
    assert summary["strata"]["stress_gold"]["total"] == 3
    assert summary["strata"]["holdout"]["total"] == 0
    assert summary["case_deltas"]["available"] is False


def test_goldset_runner_writes_valid_calibration_ledger(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"

    first = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", ledger_path=ledger_path, notes="baseline")
    second = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", ledger_path=ledger_path, notes="repeat")

    assert first["calibration_ledger"]["entry_appended"] is True
    assert second["case_deltas"]["available"] is True
    assert second["case_deltas"]["changed_case_count"] == 0
    assert second["recommendation_changes_vs_prior"]["total_changed_cases"] == 0

    schema = load_goldset_ledger_entry_schema()
    ledger_lines = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(ledger_lines) == 2
    for entry in ledger_lines:
        validate(instance=entry, schema=schema)


def test_goldset_runner_classifies_missed_fatal_gate_for_forced_core_regression(tmp_path: Path):
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        case["pack_paths"] = [str((ROOT / "benchmarks" / "goldset" / path).resolve()) for path in case.get("pack_paths", [])]
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["scientific_record.status"] = "fatal_fail"
            case["expected"]["exact"]["decision.recommendation"] = "DO_NOT_SUBMIT"
            break
    else:
        raise AssertionError("reviewable_sound_paper case not found")

    mutated_manifest = tmp_path / "mutated_manifest.yaml"
    mutated_manifest.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    summary = run_goldset_manifest(mutated_manifest)
    case = next(item for item in summary["cases"] if item["case_id"] == "reviewable_sound_paper")

    assert case["status"] == "fail"
    assert "missed_fatal_gate" in case["error_classes"]
    assert "false_accept_on_fatal_case" in case["error_classes"]
    assert summary["gates"]["status"] == "fail"


def test_goldset_runner_excludes_holdout_in_development_and_redacts_holdout_eval(tmp_path: Path):
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["stratum"] = "holdout"
            case["gate_behavior"] = "exclude"
            break
    else:
        raise AssertionError("reviewable_sound_paper case not found")

    manifest_path = _write_manifest(tmp_path, manifest)

    development = run_goldset_manifest(manifest_path)
    assert development["total_cases"] == 7
    assert "reviewable_sound_paper" in development["holdout"]["excluded_case_ids"]
    assert all(case["case_id"] != "reviewable_sound_paper" for case in development["cases"])

    holdout = run_goldset_manifest(manifest_path, holdout_eval=True)
    assert holdout["evaluation_mode"] == "holdout_blind"
    assert holdout["total_cases"] == 1
    case = holdout["cases"][0]
    assert case["case_id"] == "reviewable_sound_paper"
    assert case["expected_redacted"] is True
    assert case["expected"]["exact"] == {}
    assert case["expected_decision"]["recommendation"] is None
    assert case["decision_recommendation"] is None
    assert all(error_class == "masked_holdout_error" for error_class in case["error_classes"])
    assert holdout["holdout"]["noise_injected"] is True
    assert holdout["recommendation_changes_vs_prior"]["available"] is False
    assert holdout["holdout"]["evaluated_case_ids"] == ["reviewable_sound_paper"]


def test_goldset_runner_blocks_on_new_core_gold_failure_class_in_rolling_baseline(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    baseline_manifest = ROOT / "benchmarks" / "goldset" / "manifest.yaml"
    run_goldset_manifest(baseline_manifest, ledger_path=ledger_path, notes="baseline")

    manifest = load_goldset_manifest(baseline_manifest)
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        case["pack_paths"] = [str((ROOT / "benchmarks" / "goldset" / path).resolve()) for path in case.get("pack_paths", [])]
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["classification.article_type"] = "editorial_or_opinion"
            break
    mutated_manifest = _write_manifest(tmp_path, manifest)

    summary = run_goldset_manifest(mutated_manifest, ledger_path=ledger_path, notes="mutated")

    assert summary["gates"]["status"] == "fail"
    assert any(failure["gate_id"] == "new_core_gold_failure_class" for failure in summary["gates"]["rolling_failures"])


def test_goldset_runner_scores_recommendation_loss_for_recommendation_drift(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    baseline_manifest = ROOT / "benchmarks" / "goldset" / "manifest.yaml"
    run_goldset_manifest(baseline_manifest, ledger_path=ledger_path, notes="baseline")

    manifest = load_goldset_manifest(baseline_manifest)
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["decision.recommendation"] = "PREPRINT_READY_NOT_JOURNAL_READY"
            break
    mutated_manifest = _write_manifest(tmp_path, manifest)

    summary = run_goldset_manifest(mutated_manifest, ledger_path=ledger_path, notes="recommendation-drift")
    case = next(item for item in summary["cases"] if item["case_id"] == "reviewable_sound_paper")

    assert case["recommendation_loss"] == 2
    assert case["total_score"] >= case["decision_score"]
    assert summary["gates"]["status"] == "fail"
    assert any(failure["gate_id"] == "new_core_gold_failure_class" for failure in summary["gates"]["rolling_failures"])


def test_goldset_runner_blocks_when_fatal_error_count_exceeds_rolling_baseline(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    baseline_manifest = ROOT / "benchmarks" / "goldset" / "manifest.yaml"
    run_goldset_manifest(baseline_manifest, ledger_path=ledger_path, notes="baseline")

    manifest = load_goldset_manifest(baseline_manifest)
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["scientific_record.status"] = "fatal_fail"
            case["expected"]["exact"]["decision.recommendation"] = "DO_NOT_SUBMIT"
            break
    mutated_manifest = _write_manifest(tmp_path, manifest)

    summary = run_goldset_manifest(mutated_manifest, ledger_path=ledger_path, notes="fatal-drift")

    assert summary["gates"]["status"] == "fail"
    assert any(failure["gate_id"] == "fatal_error_count_above_baseline" for failure in summary["gates"]["rolling_failures"])


def test_goldset_runner_allows_governance_tuning(tmp_path: Path):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    summary = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        ledger_path=ledger_path,
        ledger_baseline_window=3,
        regression_threshold=0.2,
        fatal_weight_scale=1.5,
    )

    assert summary["governance"]["baseline_window"] == 3
    assert summary["governance"]["regression_threshold"] == 0.2
    assert summary["governance"]["drift_thresholds"]["recommendation_bias"] == 1.5
    assert summary["decision_algebra"]["severity_weights"]["missed_fatal_gate"] == 15.0


def test_goldset_runner_emits_drift_attribution_with_recent_code_changes(tmp_path: Path, monkeypatch):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    baseline_manifest = ROOT / "benchmarks" / "goldset" / "manifest.yaml"

    monkeypatch.setattr(goldset_runner, "_current_git_metadata", lambda: {"commit_sha": "oldsha", "git_dirty": False})
    monkeypatch.setattr(goldset_runner, "git_output", lambda args, cwd=None: (0, ""))
    run_goldset_manifest(baseline_manifest, ledger_path=ledger_path, notes="baseline")

    manifest = load_goldset_manifest(baseline_manifest)
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        case["pack_paths"] = [str((ROOT / "benchmarks" / "goldset" / path).resolve()) for path in case.get("pack_paths", [])]
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["classification.article_type"] = "editorial_or_opinion"
            break
    mutated_manifest = _write_manifest(tmp_path, manifest)

    monkeypatch.setattr(goldset_runner, "_current_git_metadata", lambda: {"commit_sha": "newsha", "git_dirty": False})

    def _fake_git_output(args: list[str], cwd=None):
        if args[:2] == ["diff", "--name-only"]:
            return 0, "src/apr_core/goldset/runner.py"
        return 0, ""

    monkeypatch.setattr(goldset_runner, "git_output", _fake_git_output)
    summary = run_goldset_manifest(mutated_manifest, ledger_path=ledger_path, notes="mutated")

    attribution = summary["system_diagnostics"]["drift_attribution"]
    assert attribution["available"] is True
    assert attribution["likely_source"]["category"] == "reviewable_baseline"
    assert attribution["likely_source"]["error_class"] == "wrong_article_type"
    assert attribution["likely_source"]["code_change_surface"] == "goldset_governor"


def test_goldset_runner_emits_separate_scientific_and_editorial_planes():
    summary = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml", separate_planes=True)
    case = next(item for item in summary["cases"] if item["case_id"] == "reviewable_sound_paper")

    assert summary["governance"]["gating"]["use_editorial_for_decision"] is False
    assert summary["decision_algebra"]["plane_mode"] == "separate"
    assert case["scientific_score"]["total"] == 1.0
    assert case["editorial_score"]["total"] is not None
    assert case["scientific_loss"] == 0
    assert case["total_loss"] == case["total_score"] == 0


def test_goldset_runner_editorial_score_does_not_change_decision():
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    case = next(item for item in manifest["cases"] if item["case_id"] == "reviewable_sound_paper")
    payload = json.loads((ROOT / "fixtures" / "inputs" / case["input"]).read_text(encoding="utf-8"))
    record = goldset_runner.run_audit(payload)
    observed = goldset_runner._summarize_observed_surface(record)
    governance = goldset_runner._resolve_goldset_governance_config()
    base_editorial_first_pass = goldset_runner._build_editorial_first_pass(payload)
    base_metrics = goldset_runner._build_case_decision_metrics(
        case,
        record,
        payload,
        observed,
        [],
        governance,
        base_editorial_first_pass,
    )

    editorial_variant = copy.deepcopy(payload)
    editorial_variant["title"] = "Transformative note"
    editorial_variant["abstract"] = "A revolutionary breakthrough changes everything."
    editorial_variant["manuscript_text"] = "We propose a transformative paradigm. Revolutionary claims dominate the note."
    editorial_variant["figures_and_captions"] = []
    editorial_variant["tables"] = []
    editorial_variant["references"] = []
    shifted_editorial_first_pass = goldset_runner._build_editorial_first_pass(editorial_variant)
    shifted_metrics = goldset_runner._build_case_decision_metrics(
        case,
        record,
        editorial_variant,
        observed,
        [],
        governance,
        shifted_editorial_first_pass,
    )

    assert shifted_metrics["scientific_recommendation"] == base_metrics["scientific_recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert shifted_metrics["scientific_score"] == base_metrics["scientific_score"]
    assert shifted_metrics["editorial_score"] != base_metrics["editorial_score"]
    assert shifted_metrics["decision_confidence"] == base_metrics["decision_confidence"]


def test_goldset_runner_scientific_vector_is_independent_from_scientific_record_criteria():
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    case = next(item for item in manifest["cases"] if item["case_id"] == "reviewable_sound_paper")
    payload = json.loads((ROOT / "fixtures" / "inputs" / case["input"]).read_text(encoding="utf-8"))
    record = goldset_runner.run_audit(payload)

    native_before = goldset_runner._scientific_score_vector(record, payload).as_dict()
    legacy_before = goldset_runner._scientific_score(record).as_dict()

    mutated_record = copy.deepcopy(record)
    for detail in mutated_record["scientific_record"]["criteria"].values():
        detail["status"] = "fail"
        detail["severity"] = "fatal"

    native_after = goldset_runner._scientific_score_vector(mutated_record, payload).as_dict()
    legacy_after = goldset_runner._scientific_score(mutated_record).as_dict()

    assert native_after == native_before
    assert legacy_after != legacy_before


def test_goldset_runner_editorial_penalty_remains_non_gating():
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    case = next(item for item in manifest["cases"] if item["case_id"] == "reviewable_sound_paper")
    payload = json.loads((ROOT / "fixtures" / "inputs" / case["input"]).read_text(encoding="utf-8"))
    record = goldset_runner.run_audit(payload)
    observed = goldset_runner._summarize_observed_surface(record)
    governance = goldset_runner._resolve_goldset_governance_config(enable_editorial_weight=True)
    base_editorial_first_pass = goldset_runner._build_editorial_first_pass(payload)
    base_metrics = goldset_runner._build_case_decision_metrics(
        case,
        record,
        payload,
        observed,
        [],
        governance,
        base_editorial_first_pass,
    )

    editorial_variant = copy.deepcopy(payload)
    editorial_variant["title"] = "Transformative note"
    editorial_variant["abstract"] = "A revolutionary breakthrough changes everything."
    editorial_variant["manuscript_text"] = "We propose a transformative paradigm. Revolutionary claims dominate the note."
    editorial_variant["figures_and_captions"] = []
    editorial_variant["tables"] = []
    editorial_variant["references"] = []
    shifted_editorial_first_pass = goldset_runner._build_editorial_first_pass(editorial_variant)
    shifted_metrics = goldset_runner._build_case_decision_metrics(
        case,
        record,
        editorial_variant,
        observed,
        [],
        governance,
        shifted_editorial_first_pass,
    )

    assert base_metrics["scientific_recommendation"] == shifted_metrics["scientific_recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert shifted_metrics["editorial_penalty"] > base_metrics["editorial_penalty"]
    assert shifted_metrics["total_score"] > base_metrics["total_score"]
    assert shifted_metrics["editorial_penalty"] < shifted_metrics["boundary_margin"]


def test_goldset_runner_exports_extended_calibration_records():
    summary = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset" / "manifest.yaml",
        export_calibration_extended=True,
        drift_counterfactuals=True,
    )
    summary_case = summary["cases"][0]
    case = summary["calibration_export"]["cases"][0]

    assert summary["calibration_export"]["case_count"] == summary["total_cases"]
    assert summary_case["scientific_score_vector_legacy"]["total"] is not None
    assert summary_case["scientific_score_vector_native"]["claim_clarity"] is not None
    assert summary_case["drift_counterfactual_stability"] is not None
    assert case["scientific_score_vector"]["evidence_alignment"] is not None
    assert case["scientific_score_vector_legacy"]["total"] is not None
    assert case["scientific_score_vector_native"]["claim_clarity"] is not None
    assert case["editorial_score_vector"]["clarity"] is not None
    assert case["decision"] is not None
    assert case["confidence"] in {"low", "medium", "high"}
    assert case["loss"] >= 0
    assert case["boundary_margin"] >= 0
    assert case["calibration_extended"]["scientific_vector"]["claim_clarity"] is not None
    assert case["calibration_extended"]["scientific_vector_legacy"]["total"] is not None
    assert case["calibration_extended"]["scientific_vector_native"]["claim_clarity"] is not None
    assert case["calibration_extended"]["editorial_vector"]["clarity"] is not None
    assert case["calibration_extended"]["loss_band"] in {"low", "medium", "high"}
    assert case["calibration_extended"]["drift_counterfactual"] == case["calibration_extended"]["counterfactuals"]
    assert 0.0 <= case["calibration_extended"]["drift_counterfactual_stability"] <= 1.0


def test_goldset_runner_quantizes_losses_when_enabled():
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    case = next(item for item in manifest["cases"] if item["case_id"] == "reviewable_sound_paper")
    payload = json.loads((ROOT / "fixtures" / "inputs" / case["input"]).read_text(encoding="utf-8"))
    record = goldset_runner.run_audit(payload)
    observed = goldset_runner._summarize_observed_surface(record)
    governance = goldset_runner._resolve_goldset_governance_config(
        enable_editorial_weight=True,
        loss_quantization=True,
    )
    payload["title"] = "Transformative note"
    payload["abstract"] = "A revolutionary breakthrough changes everything."
    payload["manuscript_text"] = "We propose a transformative paradigm. Revolutionary claims dominate the note."
    payload["figures_and_captions"] = []
    payload["tables"] = []
    payload["references"] = []
    editorial_first_pass = goldset_runner._build_editorial_first_pass(payload)
    metrics = goldset_runner._build_case_decision_metrics(
        case,
        record,
        payload,
        observed,
        [],
        governance,
        editorial_first_pass,
    )

    assert metrics["editorial_penalty"] > 0
    assert metrics["editorial_penalty"] == round(metrics["editorial_penalty"], 2)
    assert metrics["total_score"] == round(metrics["total_score"], 2)
    assert metrics["loss_band"] in {"low", "medium", "high"}


def test_goldset_runner_applies_strict_holdout_blindness_bins_and_masking(tmp_path: Path):
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    manifest["cases"] = [case for case in manifest["cases"] if case["case_id"] == "reviewable_sound_paper"]
    manifest["cases"][0]["stratum"] = "holdout"
    manifest["cases"][0]["gate_behavior"] = "exclude"
    manifest["cases"][0]["expected"]["exact"]["scientific_record.status"] = "fatal_fail"
    manifest["cases"][0]["expected"]["exact"]["decision.recommendation"] = "DO_NOT_SUBMIT"
    manifest_path = _write_manifest(tmp_path, manifest)

    summary = run_goldset_manifest(
        manifest_path,
        holdout_eval=True,
        holdout_blindness_level="strict",
    )
    case = summary["cases"][0]

    assert summary["holdout"]["blindness_level"] == "strict"
    assert case["decision_recommendation"] is None
    assert case["decision_consistency_status"] == "masked_holdout"
    assert case["recommendation_bin"] == "accepted_band"
    assert case["error_class_bins"]["fatal_or_integrity"] >= 1
    assert case["scientific_score"]["total"] is None
    assert case["scientific_score_vector"]["claim_clarity"] is None
    assert case["loss_band"] in {"low", "medium", "high"}
    assert all(error_class == "masked_holdout_error" for error_class in case["error_classes"])


def test_goldset_runner_reports_drift_intervention_delta(tmp_path: Path, monkeypatch):
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    baseline_manifest = ROOT / "benchmarks" / "goldset" / "manifest.yaml"

    monkeypatch.setattr(goldset_runner, "_current_git_metadata", lambda: {"commit_sha": "oldsha", "git_dirty": False})
    monkeypatch.setattr(goldset_runner, "git_output", lambda args, cwd=None: (0, ""))
    run_goldset_manifest(baseline_manifest, ledger_path=ledger_path, notes="baseline")

    manifest = load_goldset_manifest(baseline_manifest)
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["classification.article_type"] = "editorial_or_opinion"
            break
    mutated_manifest = _write_manifest(tmp_path, manifest)

    monkeypatch.setattr(goldset_runner, "_current_git_metadata", lambda: {"commit_sha": "newsha", "git_dirty": False})
    monkeypatch.setattr(
        goldset_runner,
        "git_output",
        lambda args, cwd=None: (0, "src/apr_core/goldset/runner.py") if args[:2] == ["diff", "--name-only"] else (0, ""),
    )

    summary = run_goldset_manifest(mutated_manifest, ledger_path=ledger_path, notes="mutated", drift_intervention=True)
    intervention = summary["system_diagnostics"]["drift_attribution"]["intervention_delta"]
    likely_source = summary["system_diagnostics"]["drift_attribution"]["likely_source"]

    assert intervention["available"] is True
    assert intervention["surface"] == likely_source["category"]
    assert intervention["delta"] > 0


def test_goldset_runner_emits_case_level_drift_counterfactual(tmp_path: Path):
    manifest = load_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        case["pack_paths"] = [str((ROOT / "benchmarks" / "goldset" / path).resolve()) for path in case.get("pack_paths", [])]
    for case in manifest["cases"]:
        if case["case_id"] == "reviewable_sound_paper":
            case["expected"]["exact"]["classification.article_type"] = "editorial_or_opinion"
            break
    else:
        raise AssertionError("reviewable_sound_paper case not found")

    mutated_manifest = _write_manifest(tmp_path, manifest)
    summary = run_goldset_manifest(
        mutated_manifest,
        drift_counterfactuals=True,
        export_calibration_extended=True,
    )
    case = next(item for item in summary["cases"] if item["case_id"] == "reviewable_sound_paper")
    calibration_case = next(item for item in summary["calibration_export"]["cases"] if item["case_id"] == "reviewable_sound_paper")

    assert case["drift_counterfactual"]["feature"] == "error_class:wrong_article_type"
    assert case["drift_counterfactual"]["delta_loss"] > 0
    assert "error_class:wrong_article_type" in calibration_case["calibration_extended"]["drift_features"]
    assert any(
        counterfactual["feature"] == "error_class:wrong_article_type"
        for counterfactual in calibration_case["calibration_extended"]["counterfactuals"]
    )
