from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from apr_core.pipeline import run_audit
from apr_core.utils import get_by_path, is_nonempty, read_json, repo_root, utc_now_iso


def _default_manifest() -> Path:
    return repo_root() / "benchmarks" / "goldset" / "manifest.yaml"


def run_goldset_manifest(manifest_path: str | Path | None = None, *, extra_pack_paths: list[str] | None = None) -> dict[str, Any]:
    manifest_file = Path(manifest_path) if manifest_path else _default_manifest()
    manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    case_root = (manifest_file.parent / manifest["case_root"]).resolve()

    results: list[dict[str, Any]] = []
    partition_summary: dict[str, dict[str, int]] = {}
    passed = 0
    failed = 0

    for partition in manifest["partitions"]:
        partition_name = partition["name"]
        partition_summary.setdefault(partition_name, {"total": 0, "passed": 0, "failed": 0})
        for case in partition["cases"]:
            payload = read_json(case_root / case["input"])
            case_pack_paths = [str((manifest_file.parent / path).resolve()) for path in case.get("pack_paths", [])]
            merged_pack_paths = [*case_pack_paths, *(extra_pack_paths or [])]
            record = run_audit(payload, pack_paths=merged_pack_paths)

            mismatches: list[dict[str, Any]] = []
            for dotted_path, expected_value in (case.get("expected") or {}).items():
                actual_value = get_by_path(record, dotted_path)
                if actual_value != expected_value:
                    mismatches.append({"path": dotted_path, "expected": expected_value, "actual": actual_value})

            missing_required_paths: list[str] = []
            for dotted_path in case.get("required_nonempty_paths", []):
                actual_value = get_by_path(record, dotted_path)
                if not is_nonempty(actual_value):
                    missing_required_paths.append(dotted_path)

            ok = not mismatches and not missing_required_paths
            partition_summary[partition_name]["total"] += 1
            if ok:
                passed += 1
                partition_summary[partition_name]["passed"] += 1
            else:
                failed += 1
                partition_summary[partition_name]["failed"] += 1

            results.append(
                {
                    "partition": partition_name,
                    "case_id": case["case_id"],
                    "status": "pass" if ok else "fail",
                    "mismatches": mismatches,
                    "missing_required_paths": missing_required_paths,
                    "decision_recommendation": record["decision"]["recommendation"],
                }
            )

    return {
        "manifest_version": manifest["manifest_version"],
        "contract_version": manifest["contract_version"],
        "generated_at_utc": utc_now_iso(),
        "total_cases": passed + failed,
        "passed": passed,
        "failed": failed,
        "partitions": partition_summary,
        "cases": results,
    }
