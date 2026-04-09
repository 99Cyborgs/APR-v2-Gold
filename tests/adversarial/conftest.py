from __future__ import annotations

import copy
import itertools
import json
import sys
from pathlib import Path

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

from apr_core.goldset import load_goldset_manifest, run_goldset_manifest  # noqa: E402

FLAG_NAMES = (
    "leakage_guard",
    "attribution_identifiability",
    "invariance_trace",
    "strict_surface_contract",
)
FLAG_MATRIX = [dict(zip(FLAG_NAMES, values, strict=False)) for values in itertools.product((False, True), repeat=4)]


def flag_id(flags: dict[str, bool]) -> str:
    return ",".join(f"{name}={'on' if flags[name] else 'off'}" for name in FLAG_NAMES)


def load_manifest() -> dict[str, object]:
    manifest = copy.deepcopy(load_goldset_manifest(ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml"))
    manifest["case_root"] = str((ROOT / "fixtures" / "inputs").resolve())
    for case in manifest["cases"]:
        case["pack_paths"] = [str((ROOT / "benchmarks" / "goldset_dev" / path).resolve()) for path in case.get("pack_paths", [])]
    return manifest


def load_case_payload(case_id: str = "reviewable_sound_paper") -> dict[str, object]:
    manifest = load_manifest()
    case = next(case for case in manifest["cases"] if case["case_id"] == case_id)
    return json.loads((ROOT / "fixtures" / "inputs" / case["input"]).read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, manifest: dict[str, object], name: str = "manifest.yaml") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / name
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest_path


def active_case(summary: dict[str, object], case_id: str = "reviewable_sound_paper") -> dict[str, object]:
    return next(case for case in summary["cases"] if case["case_id"] == case_id)


def run_single_case_summary(
    tmp_path: Path,
    payload: dict[str, object],
    flags: dict[str, bool],
    *,
    case_id: str = "reviewable_sound_paper",
    ledger_path: Path | None = None,
    input_name: str = "attack.json",
    extra_kwargs: dict[str, object] | None = None,
) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    manifest["cases"] = [case for case in manifest["cases"] if case["case_id"] == case_id]
    manifest["cases"][0]["input"] = input_name
    (tmp_path / input_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    manifest["case_root"] = str(tmp_path.resolve())
    manifest_path = write_manifest(tmp_path, manifest)
    return run_goldset_manifest(
        manifest_path,
        ledger_path=ledger_path,
        export_calibration_extended=True,
        drift_counterfactuals=True,
        **flags,
        **(extra_kwargs or {}),
    )


def run_full_manifest_summary(
    tmp_path: Path,
    flags: dict[str, bool],
    *,
    ledger_path: Path | None = None,
    extra_kwargs: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest_path = write_manifest(tmp_path, load_manifest())
    return run_goldset_manifest(
        manifest_path,
        ledger_path=ledger_path,
        export_calibration_extended=True,
        drift_counterfactuals=True,
        **flags,
        **(extra_kwargs or {}),
    )
