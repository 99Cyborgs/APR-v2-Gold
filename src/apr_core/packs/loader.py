from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import yaml

from apr_core.anchors import dedupe_anchors
from apr_core.packs.protocol import PackSpec
from apr_core.utils import repo_root

PACK_API_VERSION = 1


def _load_manifest(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data = loaded.get("pack") or {}
    required = ["pack_id", "version", "api_version", "advisory_only", "supported_domains", "python_module", "builder"]
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError(f"pack manifest missing required fields: {', '.join(missing)}")
    if int(data["api_version"]) != PACK_API_VERSION:
        raise ValueError(f"unsupported pack api version: {data['api_version']}")
    data.setdefault("display_name", data["pack_id"])
    return data


def _import_builder(repo_path: Path, python_module: str, builder_name: str):
    import_root = repo_path / "src" if (repo_path / "src").exists() else repo_path
    import_root_str = str(import_root)
    if import_root_str not in sys.path:
        sys.path.insert(0, import_root_str)
    module = importlib.import_module(python_module)
    if not hasattr(module, builder_name):
        raise ValueError(f"builder '{builder_name}' not found in module '{python_module}'")
    return getattr(module, builder_name)


def load_pack_from_path(path: str | Path) -> PackSpec:
    raw_path = Path(path)
    manifest_path = raw_path if raw_path.name == "pack.yaml" else raw_path / "pack.yaml"
    repo_path = manifest_path.parent
    manifest = _load_manifest(manifest_path)
    builder = _import_builder(repo_path, manifest["python_module"], manifest["builder"])
    built = builder()
    if isinstance(built, PackSpec):
        spec = built
    elif isinstance(built, dict):
        spec = PackSpec(**built)
    else:
        raise ValueError("pack builder must return PackSpec or a compatible dict")
    spec.pack_id = str(manifest["pack_id"])
    spec.version = str(manifest["version"])
    spec.api_version = int(manifest["api_version"])
    spec.display_name = str(manifest["display_name"])
    spec.advisory_only = bool(manifest["advisory_only"])
    spec.supported_domains = list(manifest["supported_domains"])
    spec.repo_root = str(repo_path)
    spec.python_module = str(manifest["python_module"])
    return spec


def discover_fixture_packs() -> list[str]:
    fixture_root = repo_root() / "fixtures" / "external_packs"
    if not fixture_root.exists():
        return []
    return [str(path.parent) for path in fixture_root.glob("*/pack.yaml")]


def _failed_pack(path: str | Path, error: Exception) -> dict[str, str]:
    return {"path": str(path), "error": str(error)}


def _not_applicable_result(spec: PackSpec, domain_module: str) -> dict[str, Any]:
    return {
        "pack_id": spec.pack_id,
        "display_name": spec.display_name,
        "version": spec.version,
        "api_version": spec.api_version,
        "advisory_only": spec.advisory_only,
        "supported_domains": list(spec.supported_domains),
        "applicability": "not_applicable",
        "status": "not_applicable",
        "human_escalation_required": False,
        "signals": [],
        "warnings": [f"domain_module '{domain_module}' is outside the supported domains for this pack"],
        "fatal_gates": [],
        "evidence_anchors": [],
        "advisory_fields": {},
    }


def _normalize_fatal_gates(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items or []:
        output.append(
            {
                "code": str(item.get("code") or "unspecified_pack_gate"),
                "reason": str(item.get("reason") or "unspecified_pack_reason"),
                "scope": str(item.get("scope") or "pack_specific_advisory"),
                "evidence_anchors": dedupe_anchors(item.get("evidence_anchors") or []),
            }
        )
    return output


def _normalize_result(spec: PackSpec, result: dict[str, Any]) -> dict[str, Any]:
    applicability = "not_applicable" if result.get("status") == "not_applicable" else "applicable"
    return {
        "pack_id": spec.pack_id,
        "display_name": spec.display_name,
        "version": spec.version,
        "api_version": spec.api_version,
        "advisory_only": spec.advisory_only,
        "supported_domains": list(spec.supported_domains),
        "applicability": applicability,
        "status": str(result.get("status") or "pass"),
        "human_escalation_required": bool(result.get("human_escalation_required", False)),
        "signals": [str(item) for item in (result.get("signals") or [])],
        "warnings": [str(item) for item in (result.get("warnings") or [])],
        "fatal_gates": _normalize_fatal_gates(result.get("fatal_gates") or []),
        "evidence_anchors": dedupe_anchors(result.get("evidence_anchors") or []),
        "advisory_fields": result.get("advisory_fields") or {},
    }


def inspect_packs(pack_paths: list[str | Path] | None = None) -> dict[str, Any]:
    paths = [str(path) for path in (pack_paths or discover_fixture_packs())]
    loaded: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in paths:
        try:
            loaded.append(load_pack_from_path(path).manifest_view())
        except Exception as exc:
            failures.append(_failed_pack(path, exc))
    return {"requested_pack_paths": paths, "loaded_packs": loaded, "pack_load_failures": failures}


def execute_packs(
    payload: dict[str, Any],
    record: dict[str, Any],
    pack_paths: list[str | Path] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    requested = [str(Path(path)) for path in (pack_paths or [])]
    if not requested:
        return {
            "requested_pack_paths": [],
            "loaded_packs": [],
            "pack_load_failures": [],
            "any_pack_requested_human_escalation": False,
        }, []

    domain_module = record["classification"]["domain_module"]
    loaded: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    any_pack_requested_human_escalation = False

    for path in requested:
        try:
            spec = load_pack_from_path(path)
            loaded.append(spec.manifest_view())
            if spec.supported_domains and "*" not in spec.supported_domains and domain_module not in spec.supported_domains:
                results.append(_not_applicable_result(spec, domain_module))
                continue
            raw_result = spec.run(payload, record)
            if not isinstance(raw_result, dict):
                raise ValueError("pack run() must return a dictionary")
            normalized = _normalize_result(spec, raw_result)
            any_pack_requested_human_escalation = any_pack_requested_human_escalation or normalized["human_escalation_required"]
            results.append(normalized)
        except Exception as exc:
            failures.append(_failed_pack(path, exc))

    return {
        "requested_pack_paths": requested,
        "loaded_packs": loaded,
        "pack_load_failures": failures,
        "any_pack_requested_human_escalation": any_pack_requested_human_escalation,
    }, results
