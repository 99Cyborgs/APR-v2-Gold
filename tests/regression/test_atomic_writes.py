from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

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

import apr_core.utils as utils  # noqa: E402
import apr_core.cli as cli  # noqa: E402


def test_write_json_preserves_existing_file_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "record.json"
    target.write_text('{"status":"old"}\n', encoding="utf-8")
    original_replace = utils.os.replace

    def _fail_replace(src: str | bytes, dst: str | bytes) -> None:
        if Path(dst) == target:
            raise OSError("replace failed")
        original_replace(src, dst)

    monkeypatch.setattr(utils.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        utils.write_json(target, {"status": "new"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"status": "old"}
    assert {path.name for path in tmp_path.iterdir()} == {"record.json"}


def test_write_text_preserves_existing_markdown_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "report.md"
    target.write_text("# old report\n", encoding="utf-8")
    original_replace = utils.os.replace

    def _fail_replace(src: str | bytes, dst: str | bytes) -> None:
        if Path(dst) == target:
            raise OSError("replace failed")
        original_replace(src, dst)

    monkeypatch.setattr(utils.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        utils.write_text(target, "# new report\n")

    assert target.read_text(encoding="utf-8") == "# old report\n"
    assert {path.name for path in tmp_path.iterdir()} == {"report.md"}


def test_write_text_bundle_rolls_back_all_targets_on_mid_install_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    summary_path = tmp_path / "summary.json"
    report_path = tmp_path / "report.md"
    summary_path.write_text('{"status":"old"}\n', encoding="utf-8")
    report_path.write_text("# old report\n", encoding="utf-8")
    original_replace = utils.os.replace
    failed = {"value": False}

    def _flaky_replace(src: str | bytes, dst: str | bytes) -> None:
        if Path(dst) == report_path and not failed["value"]:
            failed["value"] = True
            raise OSError("bundle install failed")
        original_replace(src, dst)

    monkeypatch.setattr(utils.os, "replace", _flaky_replace)

    with pytest.raises(OSError, match="bundle install failed"):
        utils.write_text_bundle(
            {
                summary_path: '{"status":"new"}\n',
                report_path: "# new report\n",
            }
        )

    assert json.loads(summary_path.read_text(encoding="utf-8")) == {"status": "old"}
    assert report_path.read_text(encoding="utf-8") == "# old report\n"
    assert {path.name for path in tmp_path.iterdir()} == {"report.md", "summary.json"}


def test_cmd_goldset_restores_previous_outputs_when_ledger_append_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    summary_path = tmp_path / "goldset_summary.json"
    governance_path = tmp_path / "governance_report.json"
    ledger_path = tmp_path / "calibration_ledger.jsonl"
    summary_path.write_text('{"status":"old"}\n', encoding="utf-8")
    governance_path.write_text('{"status":"old-governance"}\n', encoding="utf-8")
    ledger_path.write_text('{"status":"old-ledger"}\n', encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "run_goldset_manifest",
        lambda *args, **kwargs: {
            "governance_report": {"status": "new-governance"},
            "calibration_ledger": {"path": None, "entry_appended": False, "baseline_window": 5},
            "gates": {"status": "pass"},
        },
    )
    monkeypatch.setattr(cli, "build_goldset_ledger_entry", lambda *args, **kwargs: {"status": "new-ledger"})

    def _failing_append(path: str | Path, entry: dict[str, object]) -> None:
        Path(path).write_text(json.dumps(entry) + "\n", encoding="utf-8")
        raise OSError("ledger append failed")

    monkeypatch.setattr(cli, "append_goldset_ledger_entry", _failing_append)

    args = SimpleNamespace(
        holdout=False,
        holdout_eval=False,
        manifest=None,
        no_ledger=False,
        ledger_path=str(ledger_path),
        output=str(summary_path),
        pack_path=None,
        notes="baseline",
        operator="tester",
        baseline_window=5,
        regression_threshold=0.1,
        fatal_weight_scale=1.0,
        loss_quantization=False,
        enable_editorial_weight=False,
        separate_planes=False,
        export_calibration_extended=False,
        holdout_blindness_level=None,
        drift_intervention="off",
        drift_counterfactuals=False,
        leakage_guard=False,
        attribution_identifiability=False,
        invariance_trace=False,
        strict_surface_contract=False,
    )

    with pytest.raises(OSError, match="ledger append failed"):
        cli.cmd_goldset(args)

    assert json.loads(summary_path.read_text(encoding="utf-8")) == {"status": "old"}
    assert json.loads(governance_path.read_text(encoding="utf-8")) == {"status": "old-governance"}
    assert json.loads(ledger_path.read_text(encoding="utf-8")) == {"status": "old-ledger"}
    assert {path.name for path in tmp_path.iterdir()} == {
        "calibration_ledger.jsonl",
        "goldset_summary.json",
        "governance_report.json",
    }
