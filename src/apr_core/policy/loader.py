from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from apr_core.utils import repo_root


def _contracts_root() -> Path:
    return repo_root() / "contracts" / "active"


@lru_cache(maxsize=1)
def load_contract_manifest() -> dict[str, Any]:
    return yaml.safe_load((_contracts_root() / "manifest.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_policy_layer() -> dict[str, Any]:
    return yaml.safe_load((_contracts_root() / "policy_layer.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_audit_input_schema() -> dict[str, Any]:
    return json.loads((_contracts_root() / "audit_input.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_canonical_record_schema() -> dict[str, Any]:
    return json.loads((_contracts_root() / "canonical_audit_record.schema.json").read_text(encoding="utf-8"))


def contract_version() -> str:
    return str(load_contract_manifest()["contract"]["version"])
