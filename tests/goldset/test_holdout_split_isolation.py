from pathlib import Path
import sys

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

from apr_core.goldset import run_goldset_manifest  # noqa: E402
import apr_core.goldset.runner as goldset_runner  # noqa: E402

DEV_MANIFEST = ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml"
HOLDOUT_MANIFEST = ROOT / "benchmarks" / "goldset_holdout" / "manifest.yaml"
AUTHORITATIVE_DOC_EXPECTATIONS = {
    ROOT / "README.md": [
        "benchmarks/goldset_dev/manifest.yaml",
        "benchmarks/goldset_holdout/manifest.yaml",
    ],
    ROOT / "benchmarks" / "goldset" / "README.md": [
        "../goldset_dev/manifest.yaml",
        "../goldset_holdout/manifest.yaml",
        "blind holdout lane",
    ],
    ROOT / "benchmarks" / "goldset" / "holdout" / "README.md": [
        "benchmarks/goldset_holdout/manifest.yaml",
        "compatibility placeholder only",
    ],
    ROOT / "docs" / "SPEC_IMPLEMENTATION_MATRIX.md": [
        "Blind holdout benchmark lane",
        "benchmarks/goldset_holdout/manifest.yaml",
    ],
    ROOT / "docs" / "BENCHMARK_POLICY.md": [
        "benchmarks/goldset_dev/manifest.yaml",
        "benchmarks/goldset_holdout/manifest.yaml",
        "apr goldset --holdout",
        "blind evaluation",
    ],
}
STALE_DOC_SNIPPETS = (
    "benchmarks/goldset/manifest.yaml",
    "benchmarks/goldset/holdout/manifest.yaml",
)


def test_holdout_ledger_entries_do_not_seed_dev_baselines(tmp_path: Path):
    shared_ledger = tmp_path / "shared_calibration_ledger.jsonl"

    holdout = run_goldset_manifest(HOLDOUT_MANIFEST, ledger_path=shared_ledger, holdout_eval=True)
    development = run_goldset_manifest(DEV_MANIFEST, ledger_path=shared_ledger)

    assert holdout["evaluation_mode"] == "holdout_blind"
    assert development["evaluation_mode"] == "development"
    assert development["prior_run"]["available"] is False
    assert development["system_diagnostics"]["baseline"]["available"] is False


def test_holdout_ledger_entries_do_not_enter_dev_case_history(tmp_path: Path, monkeypatch):
    shared_ledger = tmp_path / "shared_calibration_ledger.jsonl"
    run_goldset_manifest(HOLDOUT_MANIFEST, ledger_path=shared_ledger, holdout_eval=True)

    captured_histories: dict[str, int] = {}
    original_evaluate_case = goldset_runner._evaluate_case

    def _wrapped_evaluate_case(*args, **kwargs):
        case = args[0]
        captured_histories[case["case_id"]] = len(kwargs.get("case_history", []))
        return original_evaluate_case(*args, **kwargs)

    monkeypatch.setattr(goldset_runner, "_evaluate_case", _wrapped_evaluate_case)
    run_goldset_manifest(DEV_MANIFEST, ledger_path=shared_ledger)

    assert captured_histories
    assert all(history_size == 0 for history_size in captured_histories.values())


def test_holdout_authoritative_docs_describe_active_blind_lane():
    for doc_path, required_snippets in AUTHORITATIVE_DOC_EXPECTATIONS.items():
        content = doc_path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            assert snippet in content, f"{doc_path.name} is missing authoritative benchmark guidance: {snippet}"
        for stale_snippet in STALE_DOC_SNIPPETS:
            assert stale_snippet not in content, f"{doc_path.name} reintroduced stale benchmark path: {stale_snippet}"
