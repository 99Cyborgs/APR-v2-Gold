from __future__ import annotations

"""Load and constrain external advisory packs before their output enters APR.

Packs are outside the locked APR contract surface. They are admitted only after
manifest, API-version, domain, and output-shape normalization so provider-like
extensions cannot create false confidence or silently broaden the canonical
record.
"""

import importlib
import sys
from pathlib import Path
from typing import Any

import yaml

from apr_core.anchors import dedupe_anchors
from apr_core.packs.protocol import PackSpec
from apr_core.utils import repo_root, sha256_file

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
    inserted = False
    if import_root_str not in sys.path:
        sys.path.insert(0, import_root_str)
        inserted = True
    try:
        module = importlib.import_module(python_module)
        if not hasattr(module, builder_name):
            raise ValueError(f"builder '{builder_name}' not found in module '{python_module}'")
        return getattr(module, builder_name)
    finally:
        if inserted:
            try:
                sys.path.remove(import_root_str)
            except ValueError:
                pass


def _canonical_pack_request(path: str | Path) -> tuple[Path, Path]:
    raw_path = Path(path).expanduser()
    manifest_path = (raw_path if raw_path.name == "pack.yaml" else raw_path / "pack.yaml").resolve()
    if not manifest_path.exists():
        raise ValueError(f"pack manifest not found: {manifest_path}")
    return manifest_path.parent, manifest_path


def _canonical_requested_paths(pack_paths: list[str | Path] | None) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for path in pack_paths or []:
        repo_path, _ = _canonical_pack_request(path)
        canonical_path = str(repo_path)
        if canonical_path in seen:
            continue
        seen.add(canonical_path)
        canonical.append(canonical_path)
    return canonical


def load_pack_from_path(path: str | Path) -> PackSpec:
    repo_path, manifest_path = _canonical_pack_request(path)
    manifest = _load_manifest(manifest_path)
    builder = _import_builder(repo_path, manifest["python_module"], manifest["builder"])
    built = builder()
    if isinstance(built, PackSpec):
        spec = built
    elif isinstance(built, dict):
        spec = PackSpec(**built)
    else:
        raise ValueError("pack builder must return PackSpec or a compatible dict")
    # Manifest metadata overwrites builder-supplied identity fields so APR's
    # external trust boundary is pinned to the declared pack contract, not to
    # arbitrary runtime objects returned by pack code.
    spec.pack_id = str(manifest["pack_id"])
    spec.version = str(manifest["version"])
    spec.api_version = int(manifest["api_version"])
    spec.display_name = str(manifest["display_name"])
    spec.advisory_only = bool(manifest["advisory_only"])
    spec.supported_domains = list(manifest["supported_domains"])
    spec.repo_root = str(repo_path)
    spec.resolved_repo_root = str(repo_path)
    spec.manifest_path = str(manifest_path)
    spec.manifest_sha256 = sha256_file(manifest_path)
    spec.python_module = str(manifest["python_module"])
    return spec


def discover_fixture_packs() -> list[str]:
    fixture_root = repo_root() / "fixtures" / "external_packs"
    if not fixture_root.exists():
        return []
    return _canonical_requested_paths([path.parent for path in fixture_root.glob("*/pack.yaml")])


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
                "scope": str(item.get("scope") or "advisory_pack_request"),
                "evidence_anchors": dedupe_anchors(item.get("evidence_anchors") or []),
            }
        )
    return output


def _normalize_result(spec: PackSpec, result: dict[str, Any]) -> dict[str, Any]:
    applicability = "not_applicable" if result.get("status") == "not_applicable" else "applicable"
    # APR never trusts raw pack output as canonical. Normalization constrains
    # extension results to additive advisory fields and explicit gate semantics.
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
    paths = _canonical_requested_paths(pack_paths or discover_fixture_packs())
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
    requested = _canonical_requested_paths(pack_paths or [])
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
            # Pack failures are recorded, not masked. APR keeps the core audit
            # assessable instead of trusting partial extension output.
            failures.append(_failed_pack(path, exc))

    return {
        "requested_pack_paths": requested,
        "loaded_packs": loaded,
        "pack_load_failures": failures,
        "any_pack_requested_human_escalation": any_pack_requested_human_escalation,
    }, results
