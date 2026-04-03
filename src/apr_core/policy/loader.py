from __future__ import annotations

"""Load the single active APR contract surface for runtime enforcement.

This module is the code-side authority for which manifest, policy layer, and
JSON Schemas are active. Runtime callers must resolve versions from these files
rather than hard-coding policy assumptions, because APR treats one manifest,
one policy layer, and one schema pair as the only admissible contract set.
"""

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
    # The manifest is the version authority that binds runtime behavior to one
    # active contract lineage.
    return yaml.safe_load((_contracts_root() / "manifest.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_policy_layer() -> dict[str, Any]:
    # Policy is loaded beside the manifest so recommendation and compatibility
    # constraints cannot silently drift from the active contract version.
    return yaml.safe_load((_contracts_root() / "policy_layer.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_audit_input_schema() -> dict[str, Any]:
    return json.loads((_contracts_root() / "audit_input.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_canonical_record_schema() -> dict[str, Any]:
    return json.loads((_contracts_root() / "canonical_audit_record.schema.json").read_text(encoding="utf-8"))


def contract_version() -> str:
    # Package versioning is normalized to the active manifest so distribution
    # metadata cannot advertise a different contract than runtime enforcement.
    return str(load_contract_manifest()["contract"]["version"])
